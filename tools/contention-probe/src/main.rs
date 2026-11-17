//! Contention and batch-size probe (knotrel v0.6.0 qualification, M5/M3.6).
//!
//! Starts one `knotrel-server` process, loads a deterministic graph, then
//! runs a list of configurations against it, printing one JSON line per
//! configuration. It links no knotrel crate: every measurement crosses the
//! real HTTP stack of the binary under test.
//!
//! ```text
//! contention-probe --server-bin PATH --mode standalone|source-managed
//!     --lifecycle true|false --nodes N --seed S --configs FILE [--port P]
//! ```
//!
//! `FILE` holds one JSON object per line:
//! `{"id":..,"mix":"read100|read95|mixed50|lifecycle50","batch":B,"clients":C,
//!   "warmup_ms":W,"measure_ms":D,"open_rate":R|null,"background":"none|import|events"}`.
//!
//! # Measurement boundaries
//!
//! - **Client latency:** from the time a request is due (open loop: its
//!   scheduled time; closed loop: when the client starts writing it) to the
//!   end of its response body, on a dedicated keep-alive connection per
//!   client. Requests that *start* inside the measure window are recorded;
//!   warmup requests are discarded. Open-loop latency therefore includes
//!   client-side queueing when the server falls behind (no coordinated
//!   omission).
//! - **Throughput:** completed requests (and graph operations) per second of
//!   measure window; open loop also reports the offered rate.
//! - **Server phases:** deltas of the server's own histograms between two
//!   `/metrics` scrapes bracketing the measure window: queue wait, lock wait
//!   and execution per job kind, and HTTP duration per route. Means are
//!   exact (`sum / count`); quantiles are bucket upper bounds.
//! - **Outstanding work:** `knotrel_graph_jobs_outstanding`, sampled every
//!   100 ms during the measure window by one extra connection (the scrape
//!   takes no graph lock).
//! - **Fairness:** Jain's index over per-client completed requests, and the
//!   min/max ratio.
//! - **Memory:** server RSS (`ps`) after each configuration.
//!
//! Mixes: `read100` only `connected` (the only direct requests source-managed
//! mode accepts); `read95` and `mixed50` add 5% and 50% `link`/`cut`
//! toggles of client-owned extra edges; `lifecycle50` adds 50%
//! `set_node_active`/`set_edge_enabled` toggles of client-owned nodes and
//! base edges (lifecycle support only).
//!
//! Every response is checked: a status other than 200 is counted by status
//! (503 = admission refusal); a 200 batch must return one result per
//! operation, and per-item `error` results and no-op mutations
//! (`changed: false`) are counted by code.
//!
//! # Revision 2 (v0.6.0 supplementary contention run)
//!
//! Fixes the coverage defects found after the frozen v0.6.0 campaign:
//! - the server is started with `KNOTREL_MAX_NODES = nodes + 100000`, so the
//!   new node IDs registered by `mixed50` toggles and feeder catch-up fit
//!   (the default limit is 100,000);
//! - a background import reads the current `ETag` from `GET /v1/stats` when
//!   its configuration starts, instead of reusing one that an earlier
//!   configuration's events made stale;
//! - a background feeder request refused with 503 is retried unchanged after
//!   10 ms and counted; any other failure stops the background activity, and
//!   every failure is recorded with its status and error code;
//! - a toggle's phase is read before the pass boundary flips it, so the last
//!   owned item of the first pass is no longer cut before it was linked (one
//!   no-op mutation per client in revision 1);
//! - each configuration toggles its own fresh extra-edge IDs (client-owned
//!   and feeder-owned), and a client resends a refused batch body unchanged,
//!   so link/cut toggles stay effective across configurations and 503s.
//!   `lifecycle50` toggles base items and is meant for one configuration per
//!   server process.
//!
//! Correctness of answers is not re-verified here (it is covered by the test
//! suites and the core oracles); the probe measures timing.

use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    io::{BufRead, BufReader, Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    process::{Child, Command, Stdio},
    sync::{
        Arc, Barrier,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::{Duration, Instant},
};

/// Deterministic xorshift generator.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn below(&mut self, bound: u64) -> u64 {
        self.next() % bound
    }
}

/// Lower-cased response header names and values.
type Headers = Vec<(String, String)>;

/// One keep-alive HTTP/1.1 connection.
struct Conn {
    reader: BufReader<TcpStream>,
    writer: TcpStream,
}

impl Conn {
    fn connect(address: SocketAddr) -> std::io::Result<Self> {
        let stream = TcpStream::connect(address)?;
        stream.set_nodelay(true)?;
        stream.set_read_timeout(Some(Duration::from_secs(60)))?;
        Ok(Self {
            reader: BufReader::new(stream.try_clone()?),
            writer: stream,
        })
    }

    /// Sends one request and reads the whole response; returns status,
    /// lower-cased headers and body.
    fn request(
        &mut self,
        method: &str,
        path: &str,
        headers: &[(&str, &str)],
        body: &[u8],
    ) -> std::io::Result<(u16, Headers, Vec<u8>)> {
        let mut head = format!("{method} {path} HTTP/1.1\r\nhost: knotrel\r\n");
        for (name, value) in headers {
            head.push_str(&format!("{name}: {value}\r\n"));
        }
        if !body.is_empty() {
            head.push_str("content-type: application/json\r\n");
        }
        head.push_str(&format!("content-length: {}\r\n\r\n", body.len()));
        self.writer.write_all(head.as_bytes())?;
        self.writer.write_all(body)?;
        let mut line = String::new();
        self.reader.read_line(&mut line)?;
        let status: u16 = line
            .split_whitespace()
            .nth(1)
            .and_then(|code| code.parse().ok())
            .ok_or_else(|| std::io::Error::other(format!("bad status line {line:?}")))?;
        let mut response_headers = Vec::new();
        loop {
            line.clear();
            self.reader.read_line(&mut line)?;
            let trimmed = line.trim_end();
            if trimmed.is_empty() {
                break;
            }
            if let Some((name, value)) = trimmed.split_once(':') {
                response_headers.push((name.trim().to_ascii_lowercase(), value.trim().to_owned()));
            }
        }
        let header = |name: &str| {
            response_headers
                .iter()
                .find(|(key, _)| key == name)
                .map(|(_, value)| value.clone())
        };
        let mut body = Vec::new();
        if let Some(length) = header("content-length") {
            let length: usize = length
                .parse()
                .map_err(|_| std::io::Error::other("bad content-length"))?;
            body.resize(length, 0);
            self.reader.read_exact(&mut body)?;
        } else if header("transfer-encoding").is_some_and(|v| v.contains("chunked")) {
            loop {
                line.clear();
                self.reader.read_line(&mut line)?;
                let size = usize::from_str_radix(line.trim().split(';').next().unwrap_or(""), 16)
                    .map_err(|_| std::io::Error::other("bad chunk size"))?;
                let start = body.len();
                body.resize(start + size, 0);
                self.reader.read_exact(&mut body[start..])?;
                line.clear();
                self.reader.read_line(&mut line)?;
                if size == 0 {
                    break;
                }
            }
        }
        Ok((status, response_headers, body))
    }
}

/// Probe revision recorded in every `start` record (1 = frozen v0.6.0 campaign).
const PROBE_REVISION: u32 = 2;

/// Node-limit headroom above the loaded graph for IDs that toggles and feeder
/// events register (at most 128 per client plus 128 feeder IDs).
const NODE_HEADROOM: u64 = 100_000;

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|listener| listener.local_addr())
        .map(|address| address.port())
        .expect("bind an ephemeral port")
}

/// Starts the server with a cleared environment and waits for `/health`.
fn start_server(
    bin: &str,
    port: u16,
    mode: &str,
    lifecycle: bool,
    max_nodes: u64,
) -> Result<Child, String> {
    let child = Command::new(bin)
        .env_clear()
        .env("KNOTREL_ADDR", format!("127.0.0.1:{port}"))
        .env("KNOTREL_MODE", mode)
        .env("KNOTREL_ENGINE", "compact-bfs")
        .env("KNOTREL_TOPOLOGY_LIFECYCLE", lifecycle.to_string())
        .env("KNOTREL_METRICS_ENABLED", "true")
        .env("KNOTREL_MAX_NODES", max_nodes.to_string())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("spawn {bin}: {e}"))?;
    let address: SocketAddr = ([127, 0, 0, 1], port).into();
    let deadline = Instant::now() + Duration::from_secs(20);
    while Instant::now() < deadline {
        if let Ok(mut conn) = Conn::connect(address)
            && let Ok((200, _, _)) = conn.request("GET", "/health", &[], b"")
        {
            return Ok(child);
        }
        thread::sleep(Duration::from_millis(20));
    }
    Err("server did not become healthy within 20 s".into())
}

/// The deterministic test graph: a random recursive tree plus `n` random
/// extra edges (about `2n` edges, connected).
fn graph(n: u64, seed: u64) -> Vec<(u64, u64)> {
    let mut rng = Rng(seed | 1);
    let mut edges: Vec<(u64, u64)> = (1..n).map(|v| (v, rng.below(v))).collect();
    let mut seen: std::collections::HashSet<(u64, u64)> =
        edges.iter().map(|&(a, b)| (a.min(b), a.max(b))).collect();
    while edges.len() < (2 * n - 1) as usize {
        let (a, b) = (rng.below(n), rng.below(n));
        if a != b && seen.insert((a.min(b), a.max(b))) {
            edges.push((a, b));
        }
    }
    edges
}

fn op_json(op: &str, a: u64, b: Option<u64>, flag: Option<(&str, bool)>) -> String {
    let mut text = match b {
        Some(b) => format!(r#"{{"op":"{op}","source":"{a}","target":"{b}""#),
        None => format!(r#"{{"op":"{op}","node":"{a}""#),
    };
    if let Some((name, value)) = flag {
        text.push_str(&format!(r#","{name}":{value}"#));
    }
    text.push('}');
    text
}

/// Per-client operation stream. Mutations touch only state owned by the
/// client and are undone in alternation, so the graph returns to its initial
/// state every two mutations of the same item.
struct Workload {
    rng: Rng,
    n: u64,
    mix: String,
    /// Client-owned extra edges (absent from the base graph) for link/cut.
    own_edges: Vec<(u64, u64)>,
    /// Client-owned base edges for set_edge_enabled.
    own_base: Vec<(u64, u64)>,
    /// Client-owned nodes for set_node_active.
    own_nodes: Vec<u64>,
    cursor: usize,
    phase: bool,
}

impl Workload {
    fn next_op(&mut self) -> String {
        let mutate_percent = match self.mix.as_str() {
            "read100" => 0,
            "read95" => 5,
            "mixed50" | "lifecycle50" => 50,
            other => panic!("unknown mix {other}"),
        };
        if self.rng.below(100) >= mutate_percent {
            let (a, b) = (self.rng.below(self.n), self.rng.below(self.n));
            return op_json("connected", a, Some(b), None);
        }
        // Advance through owned items; flip the phase after a full pass.
        let index = self.cursor;
        // The phase of this item is read before a pass boundary flips it
        // (revision 1 gave the last item of a pass the next pass's phase).
        let phase = self.phase;
        self.cursor += 1;
        let pool = if self.mix == "lifecycle50" {
            self.own_nodes.len() + self.own_base.len()
        } else {
            self.own_edges.len()
        };
        if self.cursor == pool {
            self.cursor = 0;
            self.phase = !self.phase;
        }
        if self.mix == "lifecycle50" {
            if index < self.own_nodes.len() {
                op_json(
                    "set_node_active",
                    self.own_nodes[index],
                    None,
                    Some(("active", phase)),
                )
            } else {
                let (a, b) = self.own_base[index - self.own_nodes.len()];
                op_json("set_edge_enabled", a, Some(b), Some(("enabled", phase)))
            }
        } else {
            let (a, b) = self.own_edges[index];
            op_json(if phase { "cut" } else { "link" }, a, Some(b), None)
        }
    }
}

/// Parsed Prometheus histogram series: bucket upper bounds with cumulative
/// counts, sum and count, keyed by metric name and label string.
type Histograms = BTreeMap<String, (Vec<(f64, f64)>, f64, f64)>;

fn scrape(address: SocketAddr) -> Result<(Histograms, BTreeMap<String, f64>), String> {
    let mut conn = Conn::connect(address).map_err(|e| e.to_string())?;
    let (status, _, body) = conn
        .request("GET", "/metrics", &[], b"")
        .map_err(|e| e.to_string())?;
    if status != 200 {
        return Err(format!("/metrics: {status}"));
    }
    let text = String::from_utf8_lossy(&body);
    let mut histograms: Histograms = BTreeMap::new();
    let mut gauges = BTreeMap::new();
    for line in text
        .lines()
        .filter(|l| !l.starts_with('#') && !l.is_empty())
    {
        let Some((series, value)) = line.rsplit_once(' ') else {
            continue;
        };
        let value: f64 = value.parse().unwrap_or(f64::NAN);
        let (name, labels) = match series.split_once('{') {
            Some((name, labels)) => (name, labels.trim_end_matches('}')),
            None => (series, ""),
        };
        let strip_le = |labels: &str| -> (String, Option<f64>) {
            let mut le = None;
            let rest: Vec<&str> = labels
                .split(',')
                .filter(|part| {
                    if let Some(bound) = part.strip_prefix("le=\"") {
                        le = bound
                            .trim_end_matches('"')
                            .parse()
                            .ok()
                            .or(Some(f64::INFINITY));
                        false
                    } else {
                        !part.is_empty()
                    }
                })
                .collect();
            (rest.join(","), le)
        };
        if let Some(base) = name.strip_suffix("_bucket") {
            let (key, le) = strip_le(labels);
            let entry =
                histograms
                    .entry(format!("{base}{{{key}}}"))
                    .or_insert((Vec::new(), 0.0, 0.0));
            entry.0.push((le.unwrap_or(f64::INFINITY), value));
        } else if let Some(base) = name.strip_suffix("_sum") {
            histograms
                .entry(format!("{base}{{{labels}}}"))
                .or_insert((Vec::new(), 0.0, 0.0))
                .1 = value;
        } else if let Some(base) = name.strip_suffix("_count") {
            histograms
                .entry(format!("{base}{{{labels}}}"))
                .or_insert((Vec::new(), 0.0, 0.0))
                .2 = value;
        } else {
            gauges.insert(format!("{name}{{{labels}}}"), value);
        }
    }
    Ok((histograms, gauges))
}

/// Mean and bucket quantiles of the difference of two histogram scrapes.
fn histogram_delta(before: &Histograms, after: &Histograms) -> Value {
    let mut out = serde_json::Map::new();
    for (key, (buckets, sum, count)) in after {
        let (old_buckets, old_sum, old_count) =
            before.get(key).cloned().unwrap_or((Vec::new(), 0.0, 0.0));
        let count = count - old_count;
        if count <= 0.0 {
            continue;
        }
        let delta: Vec<(f64, f64)> = buckets
            .iter()
            .map(|&(le, c)| {
                let old = old_buckets
                    .iter()
                    .find(|(b, _)| *b == le)
                    .map_or(0.0, |&(_, c)| c);
                (le, c - old)
            })
            .collect();
        let quantile = |q: f64| {
            delta
                .iter()
                .find(|&&(_, c)| c >= q * count)
                .map(|&(le, _)| {
                    if le.is_finite() {
                        json!(le)
                    } else {
                        json!("+Inf")
                    }
                })
                .unwrap_or(Value::Null)
        };
        out.insert(
            key.clone(),
            json!({"count": count, "mean_s": (sum - old_sum) / count,
                   "p50_le_s": quantile(0.5), "p99_le_s": quantile(0.99)}),
        );
    }
    Value::Object(out)
}

fn percentile(sorted: &[u64], q: f64) -> u64 {
    if sorted.is_empty() {
        return 0;
    }
    let rank = ((q * sorted.len() as f64).ceil() as usize).clamp(1, sorted.len());
    sorted[rank - 1]
}

fn rss_kib(pid: u32) -> Option<u64> {
    let output = Command::new("ps")
        .args(["-o", "rss=", "-p", &pid.to_string()])
        .output()
        .ok()?;
    String::from_utf8_lossy(&output.stdout).trim().parse().ok()
}

/// Source-managed state shared by setup and background threads.
struct Feeder {
    instance: String,
    generation: u64,
    etag: String,
    sequence: u64,
    position: String,
}

fn feeder_headers(instance: &str) -> Vec<(&'static str, String)> {
    vec![("x-knotrel-instance-id", instance.to_owned())]
}

fn import_body(
    feeder: &Feeder,
    mode: &str,
    n: u64,
    edges: &[(u64, u64)],
    position: &str,
) -> Vec<u8> {
    let mut body = format!(
        r#"{{"mode":"{mode}","instance_id":"{}","graph_id":"default","source_id":"src","source_epoch":"e1","source_position":"{position}","feeder_session_id":"probe","feeder_epoch":1,"nodes":["#,
        feeder.instance
    );
    for v in 0..n {
        if v > 0 {
            body.push(',');
        }
        body.push_str(&format!(r#""{v}""#));
    }
    body.push_str(r#"],"edges":["#);
    for (i, (a, b)) in edges.iter().enumerate() {
        if i > 0 {
            body.push(',');
        }
        body.push_str(&format!(r#"{{"source":"{a}","target":"{b}"}}"#));
    }
    body.push_str("]}");
    body.into_bytes()
}

fn post_feeder(
    conn: &mut Conn,
    feeder: &Feeder,
    path: &str,
    body: &[u8],
    etag: Option<&str>,
) -> Result<(u16, Headers, Value), String> {
    let mut headers: Vec<(&str, String)> = feeder_headers(&feeder.instance);
    if let Some(etag) = etag {
        headers.push(("if-match", etag.to_owned()));
    }
    let borrowed: Vec<(&str, &str)> = headers.iter().map(|(k, v)| (*k, v.as_str())).collect();
    let (status, response_headers, reply) = conn
        .request("POST", path, &borrowed, body)
        .map_err(|e| e.to_string())?;
    let value = serde_json::from_slice(&reply).unwrap_or(Value::Null);
    Ok((status, response_headers, value))
}

fn session_body(instance: &str) -> Vec<u8> {
    format!(r#"{{"instance_id":"{instance}","feeder_session_id":"probe","feeder_epoch":1,"lease_duration_ms":60000}}"#).into_bytes()
}

/// Loads the graph: standalone through batches of links, source-managed
/// through one `create_only` import.
fn setup(
    address: SocketAddr,
    mode: &str,
    n: u64,
    edges: &[(u64, u64)],
) -> Result<Option<Feeder>, String> {
    let mut conn = Conn::connect(address).map_err(|e| e.to_string())?;
    if mode == "standalone" {
        let mut ops: Vec<String> = (0..n).map(|v| op_json("add_node", v, None, None)).collect();
        ops.extend(
            edges
                .iter()
                .map(|&(a, b)| op_json("link", a, Some(b), None)),
        );
        for chunk in ops.chunks(1024) {
            let body = format!(r#"{{"operations":[{}]}}"#, chunk.join(","));
            let (status, _, reply) = conn
                .request("POST", "/v1/batch", &[], body.as_bytes())
                .map_err(|e| e.to_string())?;
            if status != 200 {
                return Err(format!(
                    "setup batch: {status} {}",
                    String::from_utf8_lossy(&reply)
                ));
            }
        }
        return Ok(None);
    }
    let (_, _, info) = conn
        .request("GET", "/v1/info", &[], b"")
        .map_err(|e| e.to_string())?;
    let info: Value = serde_json::from_slice(&info).map_err(|e| e.to_string())?;
    let instance = info["instance_id"]
        .as_str()
        .ok_or("no instance_id")?
        .to_owned();
    let mut feeder = Feeder {
        instance,
        generation: 0,
        etag: String::new(),
        sequence: 0,
        position: "p0".into(),
    };
    let (status, _, reply) = post_feeder(
        &mut conn,
        &feeder,
        "/v1/feeder/session",
        &session_body(&feeder.instance),
        None,
    )?;
    if status != 200 {
        return Err(format!("session: {status} {reply}"));
    }
    let body = import_body(&feeder, "create_only", n, edges, "p0");
    let (status, headers, reply) =
        post_feeder(&mut conn, &feeder, "/v1/feeder/import", &body, None)?;
    if status != 201 {
        return Err(format!("import: {status} {reply}"));
    }
    feeder.generation = reply["generation"].as_u64().ok_or("no generation")?;
    feeder.etag = headers
        .iter()
        .find(|(k, _)| k == "etag")
        .map(|(_, v)| v.clone())
        .ok_or("no etag")?;
    Ok(Some(feeder))
}

/// Runs one configuration and returns its JSON record.
#[allow(clippy::too_many_arguments)]
fn run_config(
    address: SocketAddr,
    pid: u32,
    config: &Value,
    n: u64,
    edges: &Arc<Vec<(u64, u64)>>,
    feeder: &mut Option<Feeder>,
    seed: u64,
    ordinal: u64,
) -> Result<Value, String> {
    let mix = config["mix"].as_str().ok_or("mix")?.to_owned();
    let batch = config["batch"].as_u64().ok_or("batch")? as usize;
    let clients = config["clients"].as_u64().ok_or("clients")? as usize;
    let warmup = Duration::from_millis(config["warmup_ms"].as_u64().ok_or("warmup_ms")?);
    let measure = Duration::from_millis(config["measure_ms"].as_u64().ok_or("measure_ms")?);
    let open_rate = config["open_rate"].as_f64();
    let background = config["background"].as_str().unwrap_or("none").to_owned();

    // Renew the feeder lease before each configuration.
    if let Some(feeder) = feeder.as_ref() {
        let mut conn = Conn::connect(address).map_err(|e| e.to_string())?;
        let body = format!(
            r#"{{"instance_id":"{}","feeder_session_id":"probe","feeder_epoch":1}}"#,
            feeder.instance
        );
        let (status, _, reply) = post_feeder(
            &mut conn,
            feeder,
            "/v1/feeder/heartbeat",
            body.as_bytes(),
            None,
        )?;
        if status != 200 {
            return Err(format!("heartbeat: {status} {reply}"));
        }
    }

    let stop = Arc::new(AtomicBool::new(false));
    let start_barrier = Arc::new(Barrier::new(clients + 1));
    let epoch = Arc::new(std::sync::OnceLock::<Instant>::new());
    let mut handles = Vec::new();
    for client in 0..clients {
        let stop = Arc::clone(&stop);
        let start_barrier = Arc::clone(&start_barrier);
        let epoch = Arc::clone(&epoch);
        let edges = Arc::clone(edges);
        let mix = mix.clone();
        handles.push(thread::spawn(move || -> Result<Value, String> {
            let mut rng = Rng((seed ^ 0x9e37_79b9_7f4a_7c15).wrapping_add(client as u64 * 7919) | 1);
            // Disjoint ownership: client c owns items with index ≡ c (mod clients).
            let own_nodes: Vec<u64> = (0..n).filter(|v| *v as usize % clients == client).take(64).collect();
            let own_base: Vec<(u64, u64)> = edges.iter().copied().enumerate().filter(|(i, _)| i % clients == client).map(|(_, e)| e).take(64).collect();
            let own_edges: Vec<(u64, u64)> = (0..64u64)
                .map(|k| {
                    // Extra edges between nodes n+.. are never in the base
                    // graph: endpoints are new IDs owned by this client.
                    // Each configuration gets fresh IDs (256 per client), so
                    // edges left linked by an earlier configuration on the
                    // same server do not turn its links into no-ops.
                    let base = n + 1_000_000 * (client as u64 + 1) + 256 * ordinal;
                    (base + 2 * k, base + 2 * k + 1)
                })
                .collect();
            let mut workload = Workload { rng: Rng(rng.next() | 1), n, mix, own_edges, own_base, own_nodes, cursor: 0, phase: false };
            let mut conn = Conn::connect(address).map_err(|e| e.to_string())?;
            start_barrier.wait();
            let t0 = *epoch.get().expect("epoch set before the barrier releases");
            let measure_start = t0 + warmup;
            let measure_end = measure_start + measure;
            let interval = open_rate.map(|rate| Duration::from_secs_f64(clients as f64 / rate));
            let mut next_due = t0 + interval.map_or(Duration::ZERO, |i| i.mul_f64(client as f64 / clients as f64));
            let mut latencies = Vec::new();
            let mut statuses: BTreeMap<u16, u64> = BTreeMap::new();
            let mut errors = 0u64;
            let mut operations = 0u64;
            let mut item_errors: BTreeMap<String, u64> = BTreeMap::new();
            let mut noop_mutations = 0u64;
            // A body refused with a non-200 status is sent again unchanged,
            // so skipped toggles do not desynchronize the link/cut phases.
            let mut pending_body: Option<String> = None;
            loop {
                let due = match interval {
                    Some(interval) => {
                        let due = next_due;
                        next_due += interval;
                        let now = Instant::now();
                        if due > now {
                            thread::sleep(due - now);
                        }
                        due
                    }
                    None => Instant::now(),
                };
                if due >= measure_end || stop.load(Ordering::Relaxed) {
                    break;
                }
                let body = pending_body.take().unwrap_or_else(|| {
                    let ops: Vec<String> = (0..batch).map(|_| workload.next_op()).collect();
                    format!(r#"{{"operations":[{}]}}"#, ops.join(","))
                });
                let result = conn.request("POST", "/v1/batch", &[], body.as_bytes());
                let done = Instant::now();
                let in_window = due >= measure_start;
                match result {
                    Ok((status, _, reply)) => {
                        if status != 200 {
                            pending_body = Some(body);
                        }
                        if in_window {
                            *statuses.entry(status).or_default() += 1;
                            if status == 200 {
                                let value: Value = serde_json::from_slice(&reply).unwrap_or(Value::Null);
                                match value["results"].as_array() {
                                    Some(results) if results.len() == batch => {
                                        for item in results {
                                            match item["result"].as_str() {
                                                Some("error") => {
                                                    let code = item["code"].as_str().unwrap_or("unknown").to_owned();
                                                    *item_errors.entry(code).or_default() += 1;
                                                }
                                                Some("changed") if item["changed"] == Value::Bool(false) => noop_mutations += 1,
                                                _ => {}
                                            }
                                        }
                                        latencies.push((done - due).as_nanos() as u64);
                                        operations += batch as u64;
                                    }
                                    _ => errors += 1,
                                }
                            }
                        }
                    }
                    Err(_) => {
                        errors += 1;
                        conn = Conn::connect(address).map_err(|e| e.to_string())?;
                    }
                }
            }
            Ok(json!({"latencies": latencies, "statuses": statuses, "errors": errors, "operations": operations,
                      "item_errors": item_errors, "noop_mutations": noop_mutations}))
        }));
    }

    // Background activity (source-managed only).
    let background_handle = if background != "none" {
        let feeder_state = feeder
            .take()
            .ok_or("background activity needs source-managed mode")?;
        let stop = Arc::clone(&stop);
        let edges = Arc::clone(edges);
        let background = background.clone();
        Some(thread::spawn(move || -> (Feeder, Value) {
            let mut feeder_state = feeder_state;
            let mut conn = Conn::connect(address).expect("background connection");
            let mut count = 0u64;
            let mut failures = 0u64;
            let mut refused = 0u64;
            let mut failure_kinds: BTreeMap<String, u64> = BTreeMap::new();
            let mut durations = Vec::new();
            let mut toggled = false;
            let mut pending_events: Option<String> = None;
            if background == "import" {
                // The stored ETag may be stale (events of an earlier
                // configuration advance the state version): read it fresh.
                match conn.request("GET", "/v1/stats", &[], b"") {
                    Ok((200, headers, _)) => {
                        if let Some((_, tag)) = headers.iter().find(|(k, _)| k == "etag") {
                            feeder_state.etag = tag.clone();
                        }
                    }
                    other => {
                        let kind = match other {
                            Ok((status, _, _)) => format!("stats-{status}"),
                            Err(e) => format!("stats-io: {e}"),
                        };
                        *failure_kinds.entry(kind).or_default() += 1;
                    }
                }
            }
            let describe = |result: &Result<(u16, Headers, Value), String>| -> String {
                match result {
                    Ok((status, _, reply)) => format!(
                        "{status} {}",
                        reply["code"]
                            .as_str()
                            .or(reply["error"]["code"].as_str())
                            .unwrap_or("-")
                    ),
                    Err(e) => format!("io: {e}"),
                }
            };
            while !stop.load(Ordering::Relaxed) {
                let start = Instant::now();
                if background == "import" {
                    let position = format!("i{count}");
                    let body = import_body(&feeder_state, "replace", n, &edges, &position);
                    let etag = feeder_state.etag.clone();
                    let result = post_feeder(
                        &mut conn,
                        &feeder_state,
                        "/v1/feeder/import",
                        &body,
                        Some(&etag),
                    );
                    match result {
                        Ok((201, ref headers, ref reply)) => {
                            feeder_state.generation = reply["generation"].as_u64().unwrap_or(0);
                            if let Some((_, tag)) = headers.iter().find(|(k, _)| k == "etag") {
                                feeder_state.etag = tag.clone();
                            }
                            feeder_state.sequence = 0;
                            feeder_state.position = position;
                            count += 1;
                        }
                        Ok((503, _, _)) => {
                            refused += 1;
                            *failure_kinds.entry(describe(&result)).or_default() += 1;
                        }
                        _ => {
                            failures += 1;
                            *failure_kinds.entry(describe(&result)).or_default() += 1;
                            if result.is_err() {
                                conn = Conn::connect(address).expect("background reconnection");
                            }
                        }
                    }
                    durations.push(start.elapsed().as_nanos() as u64);
                    // One import per second (start to start).
                    let elapsed = start.elapsed();
                    if elapsed < Duration::from_secs(1) {
                        let mut left = Duration::from_secs(1) - elapsed;
                        while left > Duration::ZERO && !stop.load(Ordering::Relaxed) {
                            let step = left.min(Duration::from_millis(20));
                            thread::sleep(step);
                            left -= step;
                        }
                    }
                } else {
                    // Feeder catch-up: closed-loop event batches of 64
                    // link/cut toggles on feeder-owned extra edges. A body
                    // refused with 503 is resent unchanged.
                    let body = match pending_events.take() {
                        Some(body) => body,
                        None => {
                            let mut events = Vec::new();
                            for k in 0..64u64 {
                                let sequence = feeder_state.sequence + 1;
                                let position = format!("e{}-{sequence}", feeder_state.generation);
                                let (a, b) =
                                    (n + 1000 * ordinal + 10 * k, n + 1000 * ordinal + 10 * k + 1);
                                events.push(format!(
                            r#"{{"event_id":"ev-{}-{sequence}","delivery_sequence":{sequence},"prev_delivery_sequence":{},"source_position":"{position}","prev_source_position":"{}","op":"{}","source":"{a}","target":"{b}"}}"#,
                            feeder_state.generation,
                            feeder_state.sequence,
                            feeder_state.position,
                            if toggled { "cut" } else { "link" }
                        ));
                                feeder_state.sequence = sequence;
                                feeder_state.position = position;
                            }
                            toggled = !toggled;
                            format!(
                                r#"{{"instance_id":"{}","graph_id":"default","generation":{},"feeder_session_id":"probe","feeder_epoch":1,"source_id":"src","source_epoch":"e1","events":[{}]}}"#,
                                feeder_state.instance,
                                feeder_state.generation,
                                events.join(",")
                            )
                        }
                    };
                    let result = post_feeder(
                        &mut conn,
                        &feeder_state,
                        "/v1/feeder/events",
                        body.as_bytes(),
                        None,
                    );
                    match result {
                        Ok((200, _, _)) => {
                            count += 64;
                            durations.push(start.elapsed().as_nanos() as u64);
                        }
                        Ok((503, _, _)) => {
                            refused += 1;
                            *failure_kinds.entry(describe(&result)).or_default() += 1;
                            pending_events = Some(body);
                            thread::sleep(Duration::from_millis(10));
                        }
                        _ => {
                            failures += 1;
                            *failure_kinds.entry(describe(&result)).or_default() += 1;
                            break;
                        }
                    }
                }
            }
            durations.sort_unstable();
            let summary = json!({"kind": background, "completed": count, "failures": failures,
                                 "refused_503": refused, "failure_kinds": failure_kinds,
                                 "p50_ns": percentile(&durations, 0.5), "max_ns": durations.last().copied().unwrap_or(0)});
            (feeder_state, summary)
        }))
    } else {
        None
    };

    let start = Instant::now();
    epoch.set(start).expect("epoch set once");
    start_barrier.wait();
    // Warmup, then bracket the measure window with scrapes and sample
    // outstanding jobs.
    thread::sleep(warmup.saturating_sub(start.elapsed()));
    let (hist_before, _) = scrape(address)?;
    let mut outstanding = Vec::new();
    let window_end = start + warmup + measure;
    while Instant::now() < window_end {
        if let Ok((_, gauges)) = scrape(address)
            && let Some(value) = gauges.get("knotrel_graph_jobs_outstanding{}")
        {
            outstanding.push(*value);
        }
        thread::sleep(Duration::from_millis(100));
    }
    let mut latencies = Vec::new();
    let mut per_client = Vec::new();
    let mut statuses: BTreeMap<String, u64> = BTreeMap::new();
    let mut errors = 0;
    let mut operations = 0;
    let mut item_errors: BTreeMap<String, u64> = BTreeMap::new();
    let mut noop_mutations = 0u64;
    for handle in handles {
        let result = handle.join().map_err(|_| "client thread panicked")??;
        let client_latencies: Vec<u64> =
            serde_json::from_value(result["latencies"].clone()).map_err(|e| e.to_string())?;
        per_client.push(client_latencies.len() as f64);
        latencies.extend(client_latencies);
        for (status, count) in result["statuses"].as_object().into_iter().flatten() {
            *statuses.entry(status.clone()).or_default() += count.as_u64().unwrap_or(0);
        }
        errors += result["errors"].as_u64().unwrap_or(0);
        operations += result["operations"].as_u64().unwrap_or(0);
        for (code, count) in result["item_errors"].as_object().into_iter().flatten() {
            *item_errors.entry(code.clone()).or_default() += count.as_u64().unwrap_or(0);
        }
        noop_mutations += result["noop_mutations"].as_u64().unwrap_or(0);
    }
    let (hist_after, _) = scrape(address)?;
    stop.store(true, Ordering::Relaxed);
    let background_summary = match background_handle {
        Some(handle) => {
            let (state, summary) = handle.join().map_err(|_| "background thread panicked")?;
            *feeder = Some(state);
            summary
        }
        None => Value::Null,
    };
    latencies.sort_unstable();
    let seconds = measure.as_secs_f64();
    let sum: f64 = per_client.iter().sum();
    let squares: f64 = per_client.iter().map(|x| x * x).sum();
    let jain = if squares > 0.0 {
        sum * sum / (per_client.len() as f64 * squares)
    } else {
        0.0
    };
    let min_max = match (
        per_client.iter().cloned().fold(f64::INFINITY, f64::min),
        per_client.iter().cloned().fold(0.0, f64::max),
    ) {
        (min, max) if max > 0.0 => min / max,
        _ => 0.0,
    };
    outstanding.sort_by(f64::total_cmp);
    Ok(json!({
        "kind": "config", "config": config,
        "completed": latencies.len(), "operations": operations,
        "requests_per_s": latencies.len() as f64 / seconds,
        "operations_per_s": operations as f64 / seconds,
        "offered_requests_per_s": open_rate,
        "latency_ns": {"p50": percentile(&latencies, 0.5), "p90": percentile(&latencies, 0.9),
                        "p99": percentile(&latencies, 0.99), "p999": percentile(&latencies, 0.999),
                        "max": latencies.last().copied().unwrap_or(0),
                        "mean": if latencies.is_empty() { 0.0 } else { latencies.iter().sum::<u64>() as f64 / latencies.len() as f64 }},
        "statuses": statuses, "errors": errors,
        "item_errors": item_errors, "noop_mutations": noop_mutations,
        "fairness": {"jain": jain, "min_over_max": min_max},
        "outstanding_jobs": {"samples": outstanding.len(),
                             "median": outstanding.get(outstanding.len() / 2).copied(),
                             "max": outstanding.last().copied()},
        "server_phases": histogram_delta(&hist_before, &hist_after),
        "background": background_summary,
        "server_rss_kib": rss_kib(pid),
    }))
}

fn main() {
    let mut args = BTreeMap::new();
    let mut items = std::env::args().skip(1);
    while let Some(flag) = items.next() {
        let key = flag.trim_start_matches("--").to_owned();
        args.insert(key, items.next().unwrap_or_default());
    }
    let get = |key: &str| {
        args.get(key)
            .cloned()
            .unwrap_or_else(|| panic!("--{key} is required"))
    };
    let bin = get("server-bin");
    let mode = get("mode");
    let lifecycle: bool = get("lifecycle").parse().expect("--lifecycle true|false");
    let n: u64 = get("nodes").parse().expect("--nodes");
    let seed: u64 = get("seed").parse().expect("--seed");
    let configs: Vec<Value> = std::fs::read_to_string(get("configs"))
        .expect("read --configs")
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).expect("config line is JSON"))
        .collect();
    let port = args
        .get("port")
        .and_then(|p| p.parse().ok())
        .unwrap_or_else(free_port);
    println!(
        "{}",
        json!({"kind": "start", "probe_revision": PROBE_REVISION, "server_bin": bin, "mode": mode, "lifecycle": lifecycle, "nodes": n, "max_nodes": n + NODE_HEADROOM, "seed": seed, "configs": configs.len()})
    );
    let max_nodes = n + NODE_HEADROOM;
    let mut child = match start_server(&bin, port, &mode, lifecycle, max_nodes) {
        Ok(child) => child,
        Err(error) => {
            eprintln!("contention-probe: {error}");
            std::process::exit(1);
        }
    };
    let address: SocketAddr = ([127, 0, 0, 1], port).into();
    let edges = Arc::new(graph(n, seed));
    let outcome = (|| -> Result<(), String> {
        let setup_start = Instant::now();
        let mut feeder = setup(address, &mode, n, &edges)?;
        println!(
            "{}",
            json!({"kind": "setup", "edges": edges.len(), "setup_ns": setup_start.elapsed().as_nanos() as u64, "server_rss_kib": rss_kib(child.id())})
        );
        for (ordinal, config) in configs.iter().enumerate() {
            let record = run_config(
                address,
                child.id(),
                config,
                n,
                &edges,
                &mut feeder,
                seed,
                ordinal as u64,
            )?;
            println!("{record}");
        }
        Ok(())
    })();
    let _ = child.kill();
    let _ = child.wait();
    if let Err(error) = outcome {
        eprintln!("contention-probe: {error}");
        std::process::exit(1);
    }
}
