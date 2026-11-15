//! In-process probe of the complete `knotrel-server` router.
//!
//! Requests pass through the real Axum router (extractors, middleware,
//! worker admission, the blocking graph job and response construction) via
//! `tower::ServiceExt::oneshot`, without sockets. Three modes:
//!
//! - `timing`: wall-clock nanoseconds for each scenario's timed window. Use
//!   the default build, which installs mimalloc like `knotrel-server`.
//! - `count`: heap operations inside each timed window. Requires the
//!   `count-alloc` build (system allocator wrapped by `stats_alloc`); its
//!   timings are *not* production timings and are not reported.
//! - `verify`: one untimed pass whose normalized responses (status, metadata
//!   headers, body, and `_total` metric counters when metrics are enabled)
//!   are folded into one FNV-1a-64 digest per scenario. Baseline and
//!   candidate builds must report identical digests.
//!
//! Every request body is serialized before its timed window. Each timed
//! window contains only request dispatch, response collection and a status
//! check. One JSON object per scenario is printed to stdout.
//!
//! ```text
//! router-probe --mode timing|count|verify [--metrics] [--iterations N]
//! ```

use axum::{
    Router,
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_server::{Lifecycle, ServerConfig, ServerMode, router_with_lifecycle};
use std::time::Instant;
use tower::ServiceExt;

#[cfg(feature = "count-alloc")]
#[global_allocator]
static GLOBAL: &stats_alloc::StatsAlloc<std::alloc::System> = &stats_alloc::INSTRUMENTED_SYSTEM;

#[cfg(not(feature = "count-alloc"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

/// Vertices in the standalone chain graph.
const CHAIN_NODES: u64 = 10_000;
/// Operations per batch request and events per feeder request.
const BATCH: usize = 1_024;
/// Vertices in the import scenario (edges form a path: `IMPORT_NODES - 1`).
const IMPORT_NODES: u64 = 100_000;
/// Concurrent in-process clients in the contention scenario.
const CLIENTS: usize = 8;
/// Untimed warmup requests before each timed window.
const WARMUP: usize = 50;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Mode {
    Timing,
    Count,
    Verify,
}

struct Options {
    mode: Mode,
    metrics: bool,
    iterations: usize,
}

fn parse_options() -> Options {
    let mut mode = None;
    let mut metrics = false;
    let mut iterations = 2_000;
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--mode" => {
                mode = Some(match args.next().as_deref() {
                    Some("timing") => Mode::Timing,
                    Some("count") => Mode::Count,
                    Some("verify") => Mode::Verify,
                    _ => fail("--mode requires timing, count or verify"),
                });
            }
            "--metrics" => metrics = true,
            "--iterations" => {
                iterations = args
                    .next()
                    .and_then(|value| value.parse().ok())
                    .filter(|&value: &usize| value >= CLIENTS * 10)
                    .unwrap_or_else(|| fail("--iterations requires an integer >= 80"));
            }
            other => fail(&format!("unknown argument: {other}")),
        }
    }
    let mode = mode.unwrap_or_else(|| fail("--mode is required"));
    if mode == Mode::Count && !cfg!(feature = "count-alloc") {
        fail("--mode count requires a build with --features count-alloc");
    }
    if mode == Mode::Timing && cfg!(feature = "count-alloc") {
        fail("--mode timing requires the default (mimalloc) build");
    }
    Options {
        mode,
        metrics,
        iterations,
    }
}

fn fail(message: &str) -> ! {
    eprintln!("router-probe: {message}");
    std::process::exit(2);
}

/// Heap operation counters at one instant (zero in non-counting builds).
#[derive(Clone, Copy, Default)]
struct Heap {
    allocations: u64,
    reallocations: u64,
    bytes_allocated: u64,
}

impl Heap {
    #[cfg(feature = "count-alloc")]
    fn now() -> Self {
        let stats = GLOBAL.stats();
        Self {
            allocations: stats.allocations as u64,
            reallocations: stats.reallocations as u64,
            bytes_allocated: stats.bytes_allocated as u64,
        }
    }

    #[cfg(not(feature = "count-alloc"))]
    fn now() -> Self {
        Self::default()
    }
}

/// One timed window: requests, elapsed nanoseconds and heap deltas.
struct Window {
    requests: usize,
    elapsed_ns: u128,
    start: Heap,
    end: Heap,
}

/// FNV-1a-64 accumulator for verification digests.
struct Digest(u64);

impl Digest {
    fn new() -> Self {
        Self(0xcbf2_9ce4_8422_2325)
    }

    fn update(&mut self, bytes: &[u8]) {
        for &byte in bytes {
            self.0 ^= u64::from(byte);
            self.0 = self.0.wrapping_mul(0x0000_0100_0000_01b3);
        }
        // Separator, so adjacent fields cannot run together.
        self.0 ^= 0xff;
        self.0 = self.0.wrapping_mul(0x0000_0100_0000_01b3);
    }
}

/// Headers whose values are part of the externally visible contract.
const VERIFIED_HEADERS: [&str; 8] = [
    "content-type",
    "etag",
    "x-knotrel-instance-id",
    "x-knotrel-graph-id",
    "x-knotrel-generation",
    "x-knotrel-state-version",
    "x-knotrel-source-position",
    "x-knotrel-sync-status",
];

struct Probe {
    router: Router,
    /// Random per-process instance ID, replaced by a placeholder in digests.
    instance: Option<String>,
    digest: Option<Digest>,
    requests: usize,
}

impl Probe {
    fn new(router: Router, verify: bool) -> Self {
        Self {
            router,
            instance: None,
            digest: verify.then(Digest::new),
            requests: 0,
        }
    }

    /// Sends one request, returning its status and body; in verify mode the
    /// normalized response is added to the scenario digest.
    async fn send(&mut self, request: Request<Body>) -> (StatusCode, Vec<u8>) {
        let response = self
            .router
            .clone()
            .oneshot(request)
            .await
            .expect("infallible");
        let status = response.status();
        // Standalone mode exposes its random instance ID only in this header.
        if self.digest.is_some()
            && self.instance.is_none()
            && let Some(id) = response.headers().get("x-knotrel-instance-id")
        {
            self.instance = Some(String::from_utf8_lossy(id.as_bytes()).into_owned());
        }
        // Headers are copied only for verification, never in timed modes.
        let headers = self.digest.is_some().then(|| response.headers().clone());
        let body = to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body")
            .to_vec();
        self.requests += 1;
        if let (Some(digest), Some(headers)) = (self.digest.as_mut(), headers) {
            let normalize = |text: &str| match &self.instance {
                Some(id) => text.replace(id.as_str(), "<instance-id>"),
                None => text.to_owned(),
            };
            digest.update(status.as_str().as_bytes());
            for name in VERIFIED_HEADERS {
                let value = headers
                    .get(name)
                    .map(|value| normalize(&String::from_utf8_lossy(value.as_bytes())));
                digest.update(name.as_bytes());
                digest.update(value.unwrap_or_else(|| "<absent>".into()).as_bytes());
            }
            digest.update(normalize(&String::from_utf8_lossy(&body)).as_bytes());
        }
        (status, body)
    }

    /// Sends every prepared request inside one timed window.
    async fn window(&mut self, label: &str, requests: Vec<Request<Body>>) -> Window {
        let count = requests.len();
        let start = Heap::now();
        let clock = Instant::now();
        for request in requests {
            let (status, _) = self.send(request).await;
            if !status.is_success() {
                fail(&format!("{label}: unexpected status {status}"));
            }
        }
        let elapsed_ns = clock.elapsed().as_nanos();
        Window {
            requests: count,
            elapsed_ns,
            start,
            end: Heap::now(),
        }
    }

    /// Folds the `_total` counter lines of `/metrics` into the digest.
    async fn digest_metric_counters(&mut self) {
        if self.digest.is_none() {
            return;
        }
        let response = self
            .router
            .clone()
            .oneshot(
                Request::get("/metrics")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("infallible");
        if response.status() == StatusCode::NOT_FOUND {
            return;
        }
        let body = to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let mut lines: Vec<_> = String::from_utf8_lossy(&body)
            .lines()
            .filter(|line| !line.starts_with('#') && line.contains("_total"))
            .map(str::to_owned)
            .collect();
        lines.sort();
        let digest = self.digest.as_mut().expect("verify mode");
        for line in lines {
            digest.update(line.as_bytes());
        }
    }
}

fn post(path: &str, instance: Option<&str>, body: String) -> Request<Body> {
    let mut builder = Request::post(path).header("content-type", "application/json");
    if let Some(instance) = instance {
        builder = builder.header("x-knotrel-instance-id", instance);
    }
    builder.body(Body::from(body)).expect("request")
}

fn op(kind: &str, source: u64, target: u64) -> String {
    format!(r#"{{"op":"{kind}","source":"{source}","target":"{target}"}}"#)
}

fn batch(ops: impl Iterator<Item = String>) -> String {
    format!(
        r#"{{"operations":[{}]}}"#,
        ops.collect::<Vec<_>>().join(",")
    )
}

fn emit(options: &Options, scenario: &str, window: &Window, digest: Option<u64>) {
    let mut record = serde_json::json!({
        "schema": 1,
        "mode": match options.mode {
            Mode::Timing => "timing",
            Mode::Count => "count",
            Mode::Verify => "verify",
        },
        "metrics": options.metrics,
        "scenario": scenario,
        "requests": window.requests,
    });
    match options.mode {
        Mode::Timing => record["elapsed_ns"] = window.elapsed_ns.to_string().into(),
        Mode::Count => {
            record["allocations"] = (window.end.allocations - window.start.allocations).into();
            record["reallocations"] =
                (window.end.reallocations - window.start.reallocations).into();
            record["bytes_allocated"] =
                (window.end.bytes_allocated - window.start.bytes_allocated).into();
        }
        Mode::Verify => record["digest"] = format!("{:016x}", digest.unwrap_or(0)).into(),
    }
    println!("{record}");
}

/// Runs `make` for warmup, then times (or verifies) a fresh batch of requests.
async fn scenario(
    probe: &mut Probe,
    options: &Options,
    label: &str,
    iterations: usize,
    mut make: impl FnMut(usize) -> Request<Body>,
) {
    let verify = options.mode == Mode::Verify;
    let iterations = if verify {
        iterations.min(20)
    } else {
        iterations
    };
    if !verify {
        let warm: Vec<_> = (0..WARMUP).map(&mut make).collect();
        probe.window(label, warm).await;
    }
    probe.digest = verify.then(Digest::new);
    let requests: Vec<_> = (0..iterations).map(&mut make).collect();
    let window = probe.window(label, requests).await;
    probe.digest_metric_counters().await;
    let digest = probe.digest.as_ref().map(|digest| digest.0);
    emit(options, label, &window, digest);
}

async fn standalone(options: &Options) {
    let config = ServerConfig::default().with_metrics_enabled(options.metrics);
    let lifecycle = Lifecycle::new();
    let mut probe = Probe::new(
        router_with_lifecycle(config, lifecycle.clone()),
        options.mode == Mode::Verify,
    );
    lifecycle.mark_ready();
    for start in (1..CHAIN_NODES).step_by(BATCH) {
        let end = (start + BATCH as u64).min(CHAIN_NODES);
        let body = batch((start..end).map(|v| op("link", v, v + 1)));
        let (status, _) = probe.send(post("/v1/batch", None, body)).await;
        assert!(status.is_success(), "setup batch failed");
    }
    let iterations = options.iterations;
    scenario(&mut probe, options, "single_connected", iterations, |i| {
        let v = 1 + (i as u64 % (CHAIN_NODES - 2));
        post("/v1/operations", None, op("connected", v, v + 1))
    })
    .await;
    if options.mode != Mode::Verify {
        concurrent(&probe.router, options).await;
    }
    scenario(
        &mut probe,
        options,
        "batch_1024_connected",
        iterations / 10,
        |i| {
            let base = 1 + (i as u64 % 100);
            let body = batch((0..BATCH as u64).map(|k| op("connected", base + k, base + k + 1)));
            post("/v1/batch", None, body)
        },
    )
    .await;
    // Alternating cut and relink batches restore the chain after each pair.
    let mut cut = true;
    scenario(
        &mut probe,
        options,
        "batch_1024_cut_link",
        iterations / 10,
        |_| {
            let kind = if cut { "cut" } else { "link" };
            cut = !cut;
            let body = batch((0..BATCH as u64).map(|k| op(kind, 1 + 2 * k, 2 + 2 * k)));
            post("/v1/batch", None, body)
        },
    )
    .await;
    if options.mode == Mode::Verify {
        errors(&mut probe, options).await;
    }
}

/// Client-visible error contract: every response must match across builds.
async fn errors(probe: &mut Probe, options: &Options) {
    probe.digest = Some(Digest::new());
    let cases = [
        post("/v1/operations", None, "{".into()),
        post("/v1/operations", None, op("connected", 1, 999_999_999)),
        post("/v1/operations", None, op("link", 7, 7)),
        post(
            "/v1/operations",
            None,
            r#"{"op":"connected","source":"abc","target":"1"}"#.into(),
        ),
        post(
            "/v1/operations",
            None,
            r#"{"op":"connected","source":"18446744073709551616","target":"1"}"#.into(),
        ),
        post(
            "/v1/operations",
            None,
            r#"{"op":"connected","source":1,"target":"1"}"#.into(),
        ),
        post("/v1/operations", None, r#"{"op":"explode"}"#.into()),
        post("/v1/batch", None, r#"{"operations":[]}"#.into()),
        Request::post("/v1/operations")
            .header("content-type", "text/plain")
            .body(Body::from(op("connected", 1, 2)))
            .expect("request"),
        Request::get("/v1/nowhere")
            .body(Body::empty())
            .expect("request"),
    ];
    let count = cases.len();
    for request in cases {
        probe.send(request).await;
    }
    probe.digest_metric_counters().await;
    let digest = probe.digest.as_ref().map(|digest| digest.0);
    let window = Window {
        requests: count,
        elapsed_ns: 0,
        start: Heap::default(),
        end: Heap::default(),
    };
    emit(options, "error_contract", &window, digest);
}

/// `CLIENTS` concurrent clients issuing single queries (timing/count only).
async fn concurrent(router: &Router, options: &Options) {
    let per_client = options.iterations / CLIENTS;
    let run = |count: usize| {
        let tasks: Vec<_> = (0..CLIENTS)
            .map(|client| {
                let router = router.clone();
                let requests: Vec<_> = (0..count)
                    .map(|i| {
                        let v = 1 + ((client * count + i) as u64 % (CHAIN_NODES - 2));
                        post("/v1/operations", None, op("connected", v, v + 1))
                    })
                    .collect();
                async move {
                    for request in requests {
                        let response = router.clone().oneshot(request).await.expect("infallible");
                        let status = response.status();
                        to_bytes(response.into_body(), usize::MAX)
                            .await
                            .expect("body");
                        assert!(status.is_success(), "concurrent request failed");
                    }
                }
            })
            .collect();
        tasks
    };
    let warm: Vec<_> = run(WARMUP / CLIENTS + 1)
        .into_iter()
        .map(tokio::spawn)
        .collect();
    for task in warm {
        task.await.expect("client");
    }
    let prepared = run(per_client);
    let start = Heap::now();
    let clock = Instant::now();
    let handles: Vec<_> = prepared.into_iter().map(tokio::spawn).collect();
    for handle in handles {
        handle.await.expect("client");
    }
    let window = Window {
        requests: per_client * CLIENTS,
        elapsed_ns: clock.elapsed().as_nanos(),
        start,
        end: Heap::now(),
    };
    emit(options, "concurrent8_single_connected", &window, None);
}

async fn source_managed(options: &Options) {
    let config = ServerConfig::default()
        .with_mode(ServerMode::SourceManaged)
        .with_metrics_enabled(options.metrics)
        .with_max_import_body_bytes(64 * 1024 * 1024)
        .expect("import limit");
    let lifecycle = Lifecycle::new();
    let mut probe = Probe::new(
        router_with_lifecycle(config, lifecycle.clone()),
        options.mode == Mode::Verify,
    );
    lifecycle.mark_ready();
    let (_, info) = probe
        .send(
            Request::get("/v1/info")
                .body(Body::empty())
                .expect("request"),
        )
        .await;
    let info: serde_json::Value = serde_json::from_slice(&info).expect("info");
    let instance = info["instance_id"].as_str().expect("instance").to_owned();
    probe.instance = Some(instance.clone());
    let session = format!(
        r#"{{"instance_id":"{instance}","feeder_session_id":"probe","feeder_epoch":1,"lease_duration_ms":60000}}"#
    );
    let (status, _) = probe
        .send(post("/v1/feeder/session", Some(&instance), session))
        .await;
    assert!(status.is_success(), "session failed");

    let nodes: Vec<_> = (0..IMPORT_NODES).map(|v| format!(r#""{v}""#)).collect();
    let edges: Vec<_> = (1..IMPORT_NODES)
        .map(|v| format!(r#"{{"source":"{}","target":"{v}"}}"#, v - 1))
        .collect();
    let body = format!(
        r#"{{"mode":"create_only","instance_id":"{instance}","graph_id":"default","source_id":"s","source_epoch":"e","source_position":"p0","feeder_session_id":"probe","feeder_epoch":1,"nodes":[{}],"edges":[{}]}}"#,
        nodes.join(","),
        edges.join(",")
    );
    drop((nodes, edges));
    // A single import per process: generation 0 accepts one create_only.
    probe.digest = (options.mode == Mode::Verify).then(Digest::new);
    let request = post("/v1/feeder/import", Some(&instance), body);
    let start = Heap::now();
    let clock = Instant::now();
    let (status, response) = probe.send(request).await;
    let elapsed_ns = clock.elapsed().as_nanos();
    let end = Heap::now();
    if status != StatusCode::CREATED {
        fail(&format!(
            "import failed: {status} {}",
            String::from_utf8_lossy(&response)
        ));
    }
    let window = Window {
        requests: 1,
        elapsed_ns,
        start,
        end,
    };
    probe.digest_metric_counters().await;
    let digest = probe.digest.as_ref().map(|digest| digest.0);
    emit(options, "import_100000_chain", &window, digest);

    let mut sequence = 0_u64;
    let mut position = String::from("p0");
    let mut events = |cut: bool| {
        let items: Vec<_> = (0..BATCH as u64)
            .map(|k| {
                sequence += 1;
                let previous = std::mem::replace(&mut position, format!("p{sequence}"));
                format!(
                    r#"{{"event_id":"e{sequence}","delivery_sequence":{sequence},"prev_delivery_sequence":{},"source_position":"{position}","prev_source_position":"{previous}","op":"{}","source":"{}","target":"{}"}}"#,
                    sequence - 1,
                    if cut { "cut" } else { "link" },
                    2 * k,
                    2 * k + 1
                )
            })
            .collect();
        format!(
            r#"{{"instance_id":"{instance}","graph_id":"default","generation":1,"feeder_session_id":"probe","feeder_epoch":1,"source_id":"s","source_epoch":"e","events":[{}]}}"#,
            items.join(",")
        )
    };
    // Delivery sequences must be contiguous, so bodies are built in order.
    let windows = if options.mode == Mode::Verify {
        4
    } else {
        options.iterations / 10
    };
    let warm: Vec<_> = if options.mode == Mode::Verify {
        Vec::new()
    } else {
        (0..WARMUP).map(|i| events(i % 2 == 0)).collect()
    };
    let timed: Vec<_> = (0..windows).map(|i| events(i % 2 == 0)).collect();
    let instance_header = instance.clone();
    let to_request = |body: String| post("/v1/feeder/events", Some(instance_header.as_str()), body);
    if !warm.is_empty() {
        probe
            .window(
                "feeder_events_1024",
                warm.into_iter().map(to_request).collect(),
            )
            .await;
    }
    probe.digest = (options.mode == Mode::Verify).then(Digest::new);
    let window = probe
        .window(
            "feeder_events_1024",
            timed.into_iter().map(to_request).collect(),
        )
        .await;
    probe.digest_metric_counters().await;
    let digest = probe.digest.as_ref().map(|digest| digest.0);
    emit(options, "feeder_events_1024", &window, digest);
}

fn main() {
    let options = parse_options();
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("runtime");
    runtime.block_on(async {
        standalone(&options).await;
        source_managed(&options).await;
    });
}
