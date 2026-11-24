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
//!     [--engine compact-bfs|ett|hdt|cluster-forest]
//! ```
//!
//! `--engine` sets `KNOTREL_ENGINE` for the server (default `compact-bfs`, the
//! only engine of the campaigns before CF5).
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
//! # Revision 3 (v0.7.0 re-qualification amendment 4, future collections)
//!
//! A background import refreshes its `If-Match` token with bounded retries
//! instead of one unretried `GET /v1/stats` (attempt a3-3 kept a stale token
//! for a whole window after one `503 busy`; diagnostic D5):
//! - the refresh retries a 503 or an I/O error with backoff 10, 20, 40, 80,
//!   then 160 ms per wait, at most [`REFRESH_ATTEMPTS`] attempts (1.27 s of
//!   backoff; each attempt is further bounded only by the connection's 60 s
//!   read timeout); an exhausted refresh is a recorded failure
//!   (`refresh-exhausted`), and one ended by any other status or a 200
//!   without an `ETag` is a distinct failure (`refresh-failed-status`);
//! - it runs when an import configuration starts and after any `412`; after a
//!   `412` the import is retried once with the fresh token, and a second `412`
//!   is a recorded failure (`precondition-after-refresh`);
//! - the background summary records stats attempts and refusals, refreshes,
//!   exhausted refreshes and refresh latency, imports attempted and completed,
//!   `412`s and retries, and per-import latency including refresh and retry;
//! - `import_starved` is true when any refresh fails, any import fails after
//!   a refresh, or fewer imports complete than are attempted (including an
//!   import refused with 503, which is not retried), so a starving
//!   configuration never looks successful.
//!
//! # Revision 4 (v0.7.0 qualification 3)
//!
//! The refresh gets an overall time budget, [`REFRESH_BUDGET`] = 1 s from its
//! first request: one period of the background import cadence (one import
//! per second, start to start), so a refresh that cannot finish within one
//! period counts as a stalled, starved background activity, not a slow
//! success. Backoff is unchanged, the attempt cap is [`REFRESH_ATTEMPTS`] = 10
//! (cumulative backoff before the tenth attempt: 950 ms), each request's read
//! timeout and any reconnect are bounded by the remaining budget, and an
//! exhausted refresh records its reason (`refresh-exhausted-deadline` or
//! `refresh-exhausted-attempts`; `refresh_exhausted` keeps the total).
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
    /// Revision 4: set when a timed-out refresh could not replace this
    /// connection; a late reply may still be queued on it, so every further
    /// request fails (the caller then reconnects) instead of reading that reply.
    poisoned: bool,
}

impl Conn {
    fn connect(address: SocketAddr) -> std::io::Result<Self> {
        Self::from_stream(TcpStream::connect(address)?)
    }

    /// [`Conn::connect`] with a connect timeout (revision 4 refresh).
    fn connect_within(address: SocketAddr, timeout: Duration) -> std::io::Result<Self> {
        Self::from_stream(TcpStream::connect_timeout(&address, timeout)?)
    }

    fn from_stream(stream: TcpStream) -> std::io::Result<Self> {
        stream.set_nodelay(true)?;
        stream.set_read_timeout(Some(READ_TIMEOUT))?;
        Ok(Self {
            reader: BufReader::new(stream.try_clone()?),
            writer: stream,
            poisoned: false,
        })
    }

    /// Sets the read and write timeouts of the underlying socket (shared by reader
    /// and writer). A read timeout bounds each `read`, not a whole response.
    fn set_read_timeout(&self, timeout: Duration) -> std::io::Result<()> {
        let timeout = Some(timeout.max(Duration::from_millis(1)));
        self.writer.set_write_timeout(timeout)?;
        self.writer.set_read_timeout(timeout)
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
        if self.poisoned {
            return Err(std::io::Error::other(
                "connection poisoned by a timed-out refresh",
            ));
        }
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

/// Probe revision recorded in every `start` record (1 = frozen v0.6.0 campaign,
/// 2 = v0.6.0 supplementary run and v0.7.0 campaigns, 3 = amendment 4 refresh,
/// 4 = refresh time budget, qualification 3).
const PROBE_REVISION: u32 = 4;

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
    engine: &str,
) -> Result<Child, String> {
    let child = Command::new(bin)
        .env_clear()
        .env("KNOTREL_ADDR", format!("127.0.0.1:{port}"))
        .env("KNOTREL_MODE", mode)
        .env("KNOTREL_ENGINE", engine)
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

/// Maximum `GET /v1/stats` attempts per refresh (revision 4; 12 in revision 3).
const REFRESH_ATTEMPTS: u32 = 10;

/// Overall time budget of one refresh, from its first request (revision 4): one period
/// of the background import cadence (one import per second, start to start). A refresh
/// that cannot finish within one period has stalled the background activity.
const REFRESH_BUDGET: Duration = Duration::from_millis(1_000);

/// Read timeout outside a refresh (as set by [`Conn::connect`]).
const READ_TIMEOUT: Duration = Duration::from_secs(60);

/// Connect timeout used to replace a connection after a refresh I/O error once
/// the budget is spent (revision 4).
const RECONNECT_FLOOR: Duration = Duration::from_millis(200);

/// Backoff before refresh attempt `attempt + 1` (revision 3): 10 ms doubling to 160 ms.
fn refresh_backoff(attempt: u32) -> Duration {
    Duration::from_millis(10u64 << attempt.min(4))
}

/// Outcome of one bounded `If-Match` refresh (revisions 3 and 4).
#[derive(Debug, Default, PartialEq, Eq)]
struct Refresh {
    etag: Option<String>,
    attempts: u32,
    refused_503: u32,
    io_errors: u32,
    other: u32,
    latency_ns: u64,
    /// Why an unsuccessful refresh stopped without a definite answer:
    /// `deadline` (the budget ran out) or `attempts` (the cap was reached).
    exhausted: Option<&'static str>,
}

/// Reads the live `ETag` from `GET /v1/stats`, retrying a 503 or an I/O error
/// with [`refresh_backoff`], within `budget` from the first request and at most
/// [`REFRESH_ATTEMPTS`] attempts. Each request's read timeout is the remaining
/// budget, and a backoff never sleeps past it. Any other status ends the
/// refresh unsuccessfully. A broken connection is replaced (connect bounded by
/// the remaining budget). The connection's read timeout is restored on return.
fn refresh_etag(conn: &mut Conn, address: SocketAddr, budget: Duration) -> Refresh {
    let start = Instant::now();
    let deadline = start + budget;
    let mut out = Refresh::default();
    loop {
        if out.attempts >= REFRESH_ATTEMPTS {
            out.exhausted = Some("attempts");
            break;
        }
        if out.attempts > 0 {
            let left = deadline.saturating_duration_since(Instant::now());
            thread::sleep(refresh_backoff(out.attempts - 1).min(left));
        }
        let left = deadline.saturating_duration_since(Instant::now());
        if left.is_zero() {
            out.exhausted = Some("deadline");
            break;
        }
        let _ = conn.set_read_timeout(left);
        out.attempts += 1;
        match conn.request("GET", "/v1/stats", &[], b"") {
            Ok((200, headers, _)) => {
                out.etag = headers
                    .iter()
                    .find(|(k, _)| k == "etag")
                    .map(|(_, v)| v.clone());
                if out.etag.is_none() {
                    out.other += 1;
                }
                break;
            }
            Ok((503, _, _)) => out.refused_503 += 1,
            Ok(_) => {
                out.other += 1;
                break;
            }
            Err(_) => {
                out.io_errors += 1;
                // Always replace the connection: a late reply may be queued on it.
                // When the budget is spent, reconnect with a short fixed timeout; if
                // that fails too, poison it so no later request reads the late reply.
                let left = deadline.saturating_duration_since(Instant::now());
                match Conn::connect_within(address, left.max(RECONNECT_FLOOR)) {
                    Ok(fresh) => *conn = fresh,
                    Err(_) => conn.poisoned = true,
                }
            }
        }
    }
    let _ = conn.set_read_timeout(READ_TIMEOUT);
    let _ = conn.writer.set_write_timeout(None);
    out.latency_ns = start.elapsed().as_nanos() as u64;
    out
}

/// Revision 3 import accounting for one background configuration.
#[derive(Debug, Default)]
struct ImportStats {
    stats_attempts: u64,
    stats_refused_503: u64,
    stats_io_errors: u64,
    stats_other: u64,
    refreshes: u64,
    refresh_exhausted: u64,
    refresh_exhausted_deadline: u64,
    refresh_exhausted_attempts: u64,
    refresh_failed_status: u64,
    refresh_latencies: Vec<u64>,
    attempted: u64,
    precondition_412: u64,
    retries: u64,
    precondition_after_refresh: u64,
}

impl ImportStats {
    /// Records a refresh; returns its token, or the failure kind
    /// (`refresh-exhausted-deadline` or `refresh-exhausted-attempts` when
    /// refusals or I/O errors used up the budget or the attempt cap,
    /// `refresh-failed-status` for any other status or a 200 without an
    /// `ETag`).
    fn record(&mut self, refresh: Refresh) -> Result<String, &'static str> {
        self.stats_attempts += u64::from(refresh.attempts);
        self.stats_refused_503 += u64::from(refresh.refused_503);
        self.stats_io_errors += u64::from(refresh.io_errors);
        self.stats_other += u64::from(refresh.other);
        self.refreshes += 1;
        self.refresh_latencies.push(refresh.latency_ns);
        match refresh.etag {
            Some(tag) => Ok(tag),
            None if refresh.other > 0 => {
                self.refresh_failed_status += 1;
                Err("refresh-failed-status")
            }
            None => {
                self.refresh_exhausted += 1;
                if refresh.exhausted == Some("attempts") {
                    self.refresh_exhausted_attempts += 1;
                    Err("refresh-exhausted-attempts")
                } else {
                    self.refresh_exhausted_deadline += 1;
                    Err("refresh-exhausted-deadline")
                }
            }
        }
    }

    /// True when the configuration's imports cannot be taken as successful.
    fn starved(&self, completed: u64) -> bool {
        self.refresh_exhausted > 0
            || self.refresh_failed_status > 0
            || self.precondition_after_refresh > 0
            || completed < self.attempted
    }

    fn summary(&mut self, completed: u64) -> Value {
        self.refresh_latencies.sort_unstable();
        json!({"stats_attempts": self.stats_attempts, "stats_refused_503": self.stats_refused_503,
               "stats_io_errors": self.stats_io_errors, "stats_other": self.stats_other,
               "refreshes": self.refreshes, "refresh_exhausted": self.refresh_exhausted,
               "refresh_exhausted_deadline": self.refresh_exhausted_deadline,
               "refresh_exhausted_attempts": self.refresh_exhausted_attempts,
               "refresh_budget_ms": REFRESH_BUDGET.as_millis() as u64,
               "refresh_failed_status": self.refresh_failed_status,
               "refresh_latency_p50_ns": percentile(&self.refresh_latencies, 0.5),
               "refresh_latency_max_ns": self.refresh_latencies.last().copied().unwrap_or(0),
               "imports_attempted": self.attempted, "imports_completed": completed,
               "precondition_412": self.precondition_412, "retries": self.retries,
               "precondition_after_refresh": self.precondition_after_refresh,
               "import_starved": self.starved(completed)})
    }
}

/// Sends one replacement import with the stored token; after a `412`,
/// refreshes the token ([`refresh_etag`]) and retries once (revision 3).
/// Returns the final response; the caller accounts it as before.
fn import_with_refresh(
    conn: &mut Conn,
    address: SocketAddr,
    feeder: &mut Feeder,
    body: &[u8],
    imports: &mut ImportStats,
    failure_kinds: &mut BTreeMap<String, u64>,
) -> Result<(u16, Headers, Value), String> {
    imports.attempted += 1;
    let etag = feeder.etag.clone();
    let result = post_feeder(conn, feeder, "/v1/feeder/import", body, Some(&etag));
    if !matches!(result, Ok((412, _, _))) {
        return result;
    }
    imports.precondition_412 += 1;
    let tag = match imports.record(refresh_etag(conn, address, REFRESH_BUDGET)) {
        Ok(tag) => tag,
        Err(kind) => {
            // The caller then counts the 412 as this import's failure, so one
            // import records two failure kinds (PROTOCOL §11).
            *failure_kinds.entry(kind.into()).or_default() += 1;
            return result;
        }
    };
    feeder.etag = tag;
    imports.retries += 1;
    let etag = feeder.etag.clone();
    let retried = post_feeder(conn, feeder, "/v1/feeder/import", body, Some(&etag));
    if matches!(retried, Ok((412, _, _))) {
        imports.precondition_412 += 1;
        imports.precondition_after_refresh += 1;
    }
    retried
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
            let mut imports = ImportStats::default();
            if background == "import" {
                // The stored ETag may be stale (events of an earlier
                // configuration advance the state version): read it fresh,
                // with bounded retries (revision 3).
                // A failed initial refresh counts in `failures` (PROTOCOL §11).
                match imports.record(refresh_etag(&mut conn, address, REFRESH_BUDGET)) {
                    Ok(tag) => feeder_state.etag = tag,
                    Err(kind) => {
                        failures += 1;
                        *failure_kinds.entry(kind.into()).or_default() += 1;
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
                    // Revision 4: a refresh that could not replace a timed-out
                    // connection poisoned it; reconnect before the next import so the
                    // import is actually sent (its failure accounting stays honest).
                    if conn.poisoned {
                        conn = Conn::connect(address).expect("background reconnection");
                    }
                    let position = format!("i{count}");
                    let body = import_body(&feeder_state, "replace", n, &edges, &position);
                    let result = import_with_refresh(
                        &mut conn,
                        address,
                        &mut feeder_state,
                        &body,
                        &mut imports,
                        &mut failure_kinds,
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
            let mut summary = json!({"kind": background, "completed": count, "failures": failures,
                                 "refused_503": refused, "failure_kinds": failure_kinds,
                                 "p50_ns": percentile(&durations, 0.5), "max_ns": durations.last().copied().unwrap_or(0)});
            if background == "import" {
                // Revision 3 accounting; `p50_ns`/`max_ns` above already include
                // refresh and retry time (each duration spans the whole attempt).
                summary["imports"] = imports.summary(count);
            }
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
    let engine = args
        .get("engine")
        .cloned()
        .unwrap_or_else(|| "compact-bfs".to_owned());
    assert!(
        ["compact-bfs", "ett", "hdt", "cluster-forest"].contains(&engine.as_str()),
        "--engine must be compact-bfs, ett, hdt or cluster-forest"
    );
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
        json!({"kind": "start", "probe_revision": PROBE_REVISION, "server_bin": bin, "mode": mode, "engine": engine, "lifecycle": lifecycle, "nodes": n, "max_nodes": n + NODE_HEADROOM, "seed": seed, "configs": configs.len()})
    );
    let max_nodes = n + NODE_HEADROOM;
    let mut child = match start_server(&bin, port, &mode, lifecycle, max_nodes, &engine) {
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

#[cfg(test)]
mod tests {
    //! Revision 3 refresh and retry against a scripted stub server.
    use super::*;
    use std::sync::Mutex;

    /// One scripted response: status, optional `etag` header.
    type Reply = (u16, Option<&'static str>);

    /// Serves `script` in order on one keep-alive connection; records each
    /// request as `"METHOD PATH if-match"`.
    fn stub(script: Vec<Reply>) -> (SocketAddr, Arc<Mutex<Vec<String>>>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        let seen = Arc::new(Mutex::new(Vec::new()));
        let log = Arc::clone(&seen);
        thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut writer = stream;
            for (status, etag) in script {
                let mut line = String::new();
                if reader.read_line(&mut line).unwrap() == 0 {
                    return;
                }
                let target: Vec<&str> = line.split_whitespace().take(2).collect();
                let (mut length, mut if_match) = (0usize, String::from("-"));
                loop {
                    let mut header = String::new();
                    reader.read_line(&mut header).unwrap();
                    let header = header.trim_end().to_owned();
                    if header.is_empty() {
                        break;
                    }
                    let (name, value) = header.split_once(':').unwrap();
                    match name.to_ascii_lowercase().as_str() {
                        "content-length" => length = value.trim().parse().unwrap(),
                        "if-match" => if_match = value.trim().to_owned(),
                        _ => {}
                    }
                }
                let mut body = vec![0; length];
                reader.read_exact(&mut body).unwrap();
                log.lock()
                    .unwrap()
                    .push(format!("{} {} {if_match}", target[0], target[1]));
                let reply = if status == 201 {
                    r#"{"generation":2}"#
                } else {
                    "{}"
                };
                let etag = etag.map(|t| format!("etag: {t}\r\n")).unwrap_or_default();
                write!(
                    writer,
                    "HTTP/1.1 {status} X\r\n{etag}content-length: {}\r\n\r\n{reply}",
                    reply.len()
                )
                .unwrap();
            }
        });
        (address, seen)
    }

    fn feeder() -> Feeder {
        Feeder {
            instance: "i".into(),
            generation: 1,
            etag: "\"stale\"".into(),
            sequence: 0,
            position: "p".into(),
        }
    }

    #[test]
    fn backoff_doubles_to_160_ms() {
        let waits: Vec<u64> = (0..6)
            .map(|a| refresh_backoff(a).as_millis() as u64)
            .collect();
        assert_eq!(waits, [10, 20, 40, 80, 160, 160]);
    }

    #[test]
    fn refresh_retries_503_then_reads_the_etag() {
        let (address, seen) = stub(vec![(503, None), (503, None), (200, Some("\"live\""))]);
        let mut conn = Conn::connect(address).unwrap();
        let refresh = refresh_etag(&mut conn, address, REFRESH_BUDGET);
        assert_eq!(refresh.etag.as_deref(), Some("\"live\""));
        assert_eq!((refresh.attempts, refresh.refused_503), (3, 2));
        assert!(refresh.latency_ns >= 30_000_000, "10 + 20 ms of backoff");
        assert_eq!(seen.lock().unwrap().len(), 3);
    }

    #[test]
    fn persistent_503_exhausts_the_refresh() {
        // A generous budget, so the attempt cap binds (with instant refusals and the 1 s
        // budget, sleep overshoot can end the refresh on the deadline just before the
        // tenth attempt; both are exhaustion).
        let (address, _) = stub(vec![(503, None); REFRESH_ATTEMPTS as usize]);
        let mut conn = Conn::connect(address).unwrap();
        let refresh = refresh_etag(&mut conn, address, Duration::from_secs(5));
        assert_eq!(refresh.exhausted, Some("attempts"));
        assert_eq!(refresh.etag, None);
        assert_eq!(
            (refresh.attempts, refresh.refused_503),
            (REFRESH_ATTEMPTS, REFRESH_ATTEMPTS)
        );
        let mut imports = ImportStats::default();
        assert_eq!(imports.record(refresh), Err("refresh-exhausted-attempts"));
        assert_eq!(imports.refresh_exhausted, 1);
        assert!(imports.starved(0));
        assert_eq!(imports.summary(0)["import_starved"], Value::Bool(true));
    }

    #[test]
    fn a_412_refreshes_and_the_retry_succeeds() {
        let (address, seen) = stub(vec![
            (412, None),
            (503, None),
            (200, Some("\"live\"")),
            (201, Some("\"next\"")),
        ]);
        let mut conn = Conn::connect(address).unwrap();
        let (mut feeder, mut imports, mut kinds) =
            (feeder(), ImportStats::default(), BTreeMap::new());
        let result = import_with_refresh(
            &mut conn,
            address,
            &mut feeder,
            b"{}",
            &mut imports,
            &mut kinds,
        );
        assert!(matches!(result, Ok((201, _, _))));
        assert_eq!(
            *seen.lock().unwrap(),
            [
                "POST /v1/feeder/import \"stale\"",
                "GET /v1/stats -",
                "GET /v1/stats -",
                "POST /v1/feeder/import \"live\""
            ]
        );
        assert_eq!(
            (imports.attempted, imports.precondition_412, imports.retries),
            (1, 1, 1)
        );
        assert_eq!(
            (
                imports.stats_attempts,
                imports.stats_refused_503,
                imports.precondition_after_refresh
            ),
            (2, 1, 0)
        );
        assert!(!imports.starved(1));
        assert!(kinds.is_empty());
    }

    #[test]
    fn a_412_after_refresh_is_a_recorded_failure() {
        let (address, _) = stub(vec![(412, None), (200, Some("\"live\"")), (412, None)]);
        let mut conn = Conn::connect(address).unwrap();
        let (mut feeder, mut imports, mut kinds) =
            (feeder(), ImportStats::default(), BTreeMap::new());
        let result = import_with_refresh(
            &mut conn,
            address,
            &mut feeder,
            b"{}",
            &mut imports,
            &mut kinds,
        );
        assert!(matches!(result, Ok((412, _, _))));
        assert_eq!(
            (imports.precondition_412, imports.precondition_after_refresh),
            (2, 1)
        );
        assert!(imports.starved(0));
    }

    #[test]
    fn a_412_with_an_exhausted_refresh_is_not_retried() {
        let mut script = vec![(412, None)];
        script.extend(vec![(503, None); REFRESH_ATTEMPTS as usize]);
        let (address, seen) = stub(script);
        let mut conn = Conn::connect(address).unwrap();
        let (mut feeder, mut imports, mut kinds) =
            (feeder(), ImportStats::default(), BTreeMap::new());
        let result = import_with_refresh(
            &mut conn,
            address,
            &mut feeder,
            b"{}",
            &mut imports,
            &mut kinds,
        );
        assert!(matches!(result, Ok((412, _, _))));
        assert_eq!(imports.retries, 0);
        let exhausted = kinds
            .get("refresh-exhausted-attempts")
            .copied()
            .unwrap_or(0)
            + kinds
                .get("refresh-exhausted-deadline")
                .copied()
                .unwrap_or(0);
        assert_eq!(exhausted, 1, "{kinds:?}");
        assert_eq!(
            seen.lock()
                .unwrap()
                .iter()
                .filter(|r| r.starts_with("POST"))
                .count(),
            1
        );
        assert!(imports.starved(0));
    }

    #[test]
    fn a_non_503_status_ends_the_refresh_as_a_distinct_failure() {
        let (address, seen) = stub(vec![(500, None)]);
        let mut conn = Conn::connect(address).unwrap();
        let refresh = refresh_etag(&mut conn, address, REFRESH_BUDGET);
        assert_eq!(
            (refresh.attempts, refresh.other, refresh.etag.clone()),
            (1, 1, None)
        );
        assert_eq!(seen.lock().unwrap().len(), 1);
        let mut imports = ImportStats::default();
        assert_eq!(imports.record(refresh), Err("refresh-failed-status"));
        assert_eq!(
            (
                imports.refresh_failed_status,
                imports.refresh_exhausted,
                imports.stats_other
            ),
            (1, 0, 1)
        );
        assert!(imports.starved(0));
        let summary = imports.summary(0);
        assert_eq!(summary["refresh_failed_status"], 1);
        assert_eq!(summary["stats_other"], 1);
    }

    #[test]
    fn a_200_without_an_etag_is_a_failed_refresh() {
        let (address, _) = stub(vec![(200, None)]);
        let mut conn = Conn::connect(address).unwrap();
        let mut imports = ImportStats::default();
        assert_eq!(
            imports.record(refresh_etag(&mut conn, address, REFRESH_BUDGET)),
            Err("refresh-failed-status")
        );
        assert!(imports.starved(0));
    }

    #[test]
    fn an_io_error_reconnects_and_retries() {
        // First connection: closed without a reply. Second: 200 with a token.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        thread::spawn(move || {
            let (first, _) = listener.accept().unwrap();
            let mut line = String::new();
            BufReader::new(first.try_clone().unwrap())
                .read_line(&mut line)
                .unwrap();
            drop(first);
            let (second, _) = listener.accept().unwrap();
            let mut reader = BufReader::new(second.try_clone().unwrap());
            let mut writer = second;
            // Request line, then headers up to the blank line (a GET has no body).
            let mut header = String::new();
            reader.read_line(&mut header).unwrap();
            loop {
                header.clear();
                reader.read_line(&mut header).unwrap();
                if header.trim_end().is_empty() {
                    break;
                }
            }
            write!(
                writer,
                "HTTP/1.1 200 OK\r\netag: \"live\"\r\ncontent-length: 2\r\n\r\n{{}}"
            )
            .unwrap();
        });
        let mut conn = Conn::connect(address).unwrap();
        let refresh = refresh_etag(&mut conn, address, REFRESH_BUDGET);
        assert_eq!(refresh.etag.as_deref(), Some("\"live\""));
        assert_eq!((refresh.attempts, refresh.io_errors), (2, 1));
    }

    #[test]
    fn slow_refusals_exhaust_the_time_budget() {
        // Each 503 arrives after 300 ms: the 1 s budget ends before the attempt cap.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut writer = stream;
            loop {
                let mut header = String::new();
                if reader.read_line(&mut header).unwrap_or(0) == 0 {
                    return;
                }
                if header.trim_end().is_empty() {
                    thread::sleep(Duration::from_millis(300));
                    if write!(writer, "HTTP/1.1 503 X\r\ncontent-length: 2\r\n\r\n{{}}").is_err() {
                        return;
                    }
                }
            }
        });
        let mut conn = Conn::connect(address).unwrap();
        let refresh = refresh_etag(&mut conn, address, REFRESH_BUDGET);
        assert_eq!(
            (refresh.etag.clone(), refresh.exhausted),
            (None, Some("deadline"))
        );
        assert!(refresh.attempts < REFRESH_ATTEMPTS, "{refresh:?}");
        assert!(refresh.latency_ns < 1_400_000_000, "{refresh:?}");
        let mut imports = ImportStats::default();
        assert_eq!(imports.record(refresh), Err("refresh-exhausted-deadline"));
        assert_eq!(
            (
                imports.refresh_exhausted,
                imports.refresh_exhausted_deadline
            ),
            (1, 1)
        );
        assert!(imports.starved(0));
    }

    #[test]
    fn a_silent_server_is_bounded_by_the_budget() {
        // The server accepts and never answers: the read timeout is the remaining budget.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        thread::spawn(move || {
            let mut held = Vec::new();
            while let Ok((stream, _)) = listener.accept() {
                held.push(stream);
            }
        });
        let mut conn = Conn::connect(address).unwrap();
        let start = Instant::now();
        let refresh = refresh_etag(&mut conn, address, Duration::from_millis(300));
        assert!(start.elapsed() < Duration::from_millis(800), "{refresh:?}");
        assert_eq!(
            (refresh.etag.clone(), refresh.exhausted),
            (None, Some("deadline"))
        );
        assert!(refresh.io_errors >= 1);
    }

    #[test]
    fn a_late_reply_is_never_read_as_the_next_answer() {
        // First connection: answers /v1/stats only after the budget. Second
        // connection (the replacement): answers 201 to the next request.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        thread::spawn(move || {
            let (first, _) = listener.accept().unwrap();
            let late = thread::spawn(move || {
                let mut reader = BufReader::new(first.try_clone().unwrap());
                let mut writer = first;
                let mut line = String::new();
                loop {
                    line.clear();
                    if reader.read_line(&mut line).unwrap_or(0) == 0 || line.trim_end().is_empty() {
                        break;
                    }
                }
                thread::sleep(Duration::from_millis(500));
                let _ = write!(
                    writer,
                    "HTTP/1.1 200 OK\r\netag: \"late\"\r\ncontent-length: 2\r\n\r\n{{}}"
                );
                thread::sleep(Duration::from_millis(500));
            });
            let (second, _) = listener.accept().unwrap();
            let mut reader = BufReader::new(second.try_clone().unwrap());
            let mut writer = second;
            let mut header = String::new();
            loop {
                header.clear();
                if reader.read_line(&mut header).unwrap_or(0) == 0 || header.trim_end().is_empty() {
                    break;
                }
            }
            let mut body = [0u8; 2];
            let _ = reader.read_exact(&mut body);
            let _ = write!(
                writer,
                "HTTP/1.1 201 Created\r\ncontent-length: 2\r\n\r\n{{}}"
            );
            late.join().unwrap();
        });
        let mut conn = Conn::connect(address).unwrap();
        let refresh = refresh_etag(&mut conn, address, Duration::from_millis(150));
        assert_eq!(
            (refresh.etag.clone(), refresh.exhausted),
            (None, Some("deadline"))
        );
        let (status, _, _) = conn
            .request("POST", "/v1/feeder/import", &[], b"{}")
            .unwrap();
        assert_eq!(status, 201, "the next request read the late refresh reply");
    }

    #[test]
    fn budget_and_cap_are_consistent() {
        let backoff_before_last: Duration = (0..REFRESH_ATTEMPTS - 1).map(refresh_backoff).sum();
        assert_eq!(backoff_before_last, Duration::from_millis(950));
        assert!(backoff_before_last < REFRESH_BUDGET);
    }

    #[test]
    fn fewer_completed_than_attempted_is_starved() {
        let imports = ImportStats {
            attempted: 5,
            ..ImportStats::default()
        };
        assert!(imports.starved(4));
        assert!(!imports.starved(5));
    }
}
