//! Release-to-release lifecycle cells (v0.6.0 qualification, experiment R).
//!
//! The same source is built twice, once against each knotrel release (the
//! linked checkout is the sibling `../../../knotrel`), and the collector runs
//! the two binaries in alternating fresh processes. Each process prints one
//! observation per cell. Inputs are generated before timing with the same
//! generators and flag draws as `memory-peak` and the `http-lifecycle`
//! `import` scenario.
//!
//! ```text
//! release-cells core-import --topology T --nodes N --inactive-percent I
//!     --disabled-percent D --seed S --warmup W --reps K
//! release-cells http-import (same flags)
//! release-cells churn --topology T --nodes N --cycles C --churn-percent P
//!     --reuse fresh|same|toggle --seed S
//! ```
//!
//! - `core-import`: `LifecycleGraph::try_from_topology` from prebuilt specs;
//!   the graph is dropped outside the timed interval. Observation: median of
//!   `K` timed builds after `W` untimed ones.
//! - `http-import`: one `create_only` import request through an in-process
//!   router with lifecycle support, a fresh router per import (built, given
//!   a session and checked untimed). Timed: the request from submission to
//!   the complete response body, so it covers body handling, parsing,
//!   candidate construction and publication. Observation: median of `K`.
//! - `churn`: the `resources` churn schedule on the lifecycle arm (graph built
//!   untimed). Observation: total time of all cycles; also reported: the
//!   slowest single operation (compaction spikes) and the number of
//!   compactions. Logical counts are checked against the independent model
//!   after every cycle; a mismatch fails the run. A `gate` field (operation
//!   and edge counts, final logical counts, `LifecycleStorage` entry counts)
//!   serves the knotrel#151 cross-arm correctness gate (cell C1).

use axum::{
    Router,
    body::{Body, Bytes, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_core::{EdgeSpec, GraphLimits, LifecycleGraph, NodeSpec};
use knotrel_server::{ServerConfig, ServerMode, router_with_config};
use lifecycle_probes::churn::schedule;
use lifecycle_probes::{Rng, Subject, Topology, build_record, generate, rss_bytes};
use serde_json::{Value, json};
use std::{collections::HashMap, fmt::Write as _, process::ExitCode, time::Instant};
use tower::ServiceExt;

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

struct Args(HashMap<String, String>);

impl Args {
    fn parse(items: impl Iterator<Item = String>) -> Result<Self, String> {
        let mut map = HashMap::new();
        let mut items = items;
        while let Some(flag) = items.next() {
            let key = flag
                .strip_prefix("--")
                .ok_or("flags must start with --")?
                .to_owned();
            map.insert(key, items.next().ok_or("missing value")?);
        }
        Ok(Self(map))
    }
    fn get(&self, key: &str) -> Result<&str, String> {
        self.0
            .get(key)
            .map(String::as_str)
            .ok_or_else(|| format!("--{key} is required"))
    }
    fn num<T: std::str::FromStr>(&self, key: &str) -> Result<T, String> {
        self.get(key)?
            .parse()
            .map_err(|_| format!("--{key} is invalid"))
    }
}

/// The lifecycle engine of a cell: `--engine` (CF5 arms), `compact-bfs`
/// when absent (the frozen v0.9.0/v1.0.0 cells pass no engine).
fn engine_arg(args: &Args) -> Result<knotrel_core::EngineConfig, String> {
    match args.0.get("engine") {
        None => Ok(knotrel_core::EngineConfig::CompactBfs),
        Some(name) => lifecycle_probes::parse_engine(name)
            .filter(|engine| knotrel_core::LifecycleGraph::supports_engine(*engine))
            .ok_or_else(|| format!("--engine {name} is not a lifecycle engine")),
    }
}

/// Median of a nonempty sample (lower median for even sizes).
fn median(values: &mut [u64]) -> u64 {
    values.sort_unstable();
    values[(values.len() - 1) / 2]
}

/// Flagged topology: node count, registered edges, inactive and disabled flags.
struct Flagged {
    n: u64,
    edges: Vec<(u64, u64)>,
    inactive: Vec<bool>,
    disabled: Vec<bool>,
}

fn flagged(args: &Args) -> Result<Flagged, String> {
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let seed: u64 = args.num("seed")?;
    let inactive_percent: u64 = args.num("inactive-percent")?;
    let disabled_percent: u64 = args.num("disabled-percent")?;
    let edges = generate(topology, n, seed);
    // The same draws as `memory-peak` and the http-lifecycle `import` scenario.
    let mut rng = Rng(seed ^ 0x1a);
    let inactive = (0..n).map(|_| rng.below(100) < inactive_percent).collect();
    let disabled = edges
        .iter()
        .map(|_| rng.below(100) < disabled_percent)
        .collect();
    Ok(Flagged {
        n,
        edges,
        inactive,
        disabled,
    })
}

fn core_import(args: &Args) -> Result<Value, String> {
    let input = flagged(args)?;
    let warmup: usize = args.num("warmup")?;
    let reps: usize = args.num("reps")?;
    let nodes: Vec<NodeSpec> = (0..input.n)
        .map(|v| NodeSpec {
            node: v,
            active: !input.inactive[v as usize],
        })
        .collect();
    let specs: Vec<EdgeSpec> = input
        .edges
        .iter()
        .zip(&input.disabled)
        .map(|(&(source, target), &off)| EdgeSpec {
            source,
            target,
            enabled: !off,
        })
        .collect();
    let engine = engine_arg(args)?;
    let mut times = Vec::with_capacity(reps);
    let mut counts = None;
    for rep in 0..warmup + reps {
        let start = Instant::now();
        let graph =
            LifecycleGraph::try_from_topology(engine, GraphLimits::default(), &nodes, &specs)
                .map_err(|e| e.to_string())?;
        let elapsed = start.elapsed().as_nanos() as u64;
        let observed = [
            graph.node_count(),
            graph.edge_count(),
            graph.active_node_count(),
            graph.enabled_edge_count(),
            graph.effective_edge_count(),
        ];
        if *counts.get_or_insert(observed) != observed {
            return Err("counts differ between builds".into());
        }
        drop(graph);
        if rep >= warmup {
            times.push(elapsed);
        }
    }
    let observation = median(&mut times.clone());
    Ok(
        json!({"kind":"core-import","engine":engine.as_str(),"observation_ns":observation,"times_ns":times,
              "counts":counts,"rss_bytes":rss_bytes()}),
    )
}

fn import_body(instance: &str, input: &Flagged) -> Bytes {
    let mut body = String::with_capacity(64 * input.edges.len() + 32 * input.n as usize + 512);
    write!(
        body,
        r#"{{"mode":"create_only","instance_id":"{instance}","graph_id":"default","source_id":"src","source_epoch":"e1","source_position":"p0","feeder_session_id":"s","feeder_epoch":1,"nodes":["#
    )
    .unwrap();
    for v in 0..input.n {
        if v > 0 {
            body.push(',');
        }
        if input.inactive[v as usize] {
            write!(body, r#"{{"node":"{v}","active":false}}"#).unwrap();
        } else {
            write!(body, r#""{v}""#).unwrap();
        }
    }
    body.push_str(r#"],"edges":["#);
    for (i, (&(a, b), &off)) in input.edges.iter().zip(&input.disabled).enumerate() {
        if i > 0 {
            body.push(',');
        }
        if off {
            write!(body, r#"{{"source":"{a}","target":"{b}","enabled":false}}"#).unwrap();
        } else {
            write!(body, r#"{{"source":"{a}","target":"{b}"}}"#).unwrap();
        }
    }
    body.push_str("]}");
    Bytes::from(body)
}

async fn send(app: &Router, request: Request<Body>) -> (StatusCode, Vec<u8>) {
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let bytes = to_bytes(response.into_body(), 64 << 20)
        .await
        .unwrap()
        .to_vec();
    (status, bytes)
}

/// A fresh lifecycle router with a feeder session; returns it and its
/// instance ID.
async fn fresh_router(engine: knotrel_core::EngineConfig) -> Result<(Router, String), String> {
    let config = ServerConfig::new("127.0.0.1:0".parse().unwrap(), engine, 32)
        .map_err(|e| e.to_string())?
        .with_mode(ServerMode::SourceManaged)
        .with_topology_lifecycle(true)
        .map_err(|e| e.to_string())?
        .with_metrics_enabled(false)
        .with_graph_limits(GraphLimits::default());
    let app = router_with_config(config);
    let (_, info) = send(&app, Request::get("/v1/info").body(Body::empty()).unwrap()).await;
    let info: Value = serde_json::from_slice(&info).map_err(|e| e.to_string())?;
    let instance = info["instance_id"]
        .as_str()
        .ok_or("no instance id")?
        .to_owned();
    let session = json!({"instance_id":instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000}).to_string();
    let (status, _) = send(
        &app,
        Request::post("/v1/feeder/session")
            .header("content-type", "application/json")
            .header("x-knotrel-instance-id", instance.as_str())
            .body(Body::from(session))
            .unwrap(),
    )
    .await;
    if status != StatusCode::OK {
        return Err(format!("session: {status}"));
    }
    Ok((app, instance))
}

async fn http_import(args: &Args) -> Result<Value, String> {
    let engine = engine_arg(args)?;
    let input = flagged(args)?;
    let warmup: usize = args.num("warmup")?;
    let reps: usize = args.num("reps")?;
    let mut times = Vec::with_capacity(reps);
    let mut body_bytes = 0;
    let mut reply_counts: Option<Value> = None;
    for rep in 0..warmup + reps {
        let (app, instance) = fresh_router(engine).await?;
        let body = import_body(&instance, &input);
        body_bytes = body.len();
        let request = Request::post("/v1/feeder/import")
            .header("content-type", "application/json")
            .header("x-knotrel-instance-id", instance.as_str())
            .body(Body::from(body))
            .unwrap();
        let start = Instant::now();
        let (status, reply) = send(&app, request).await;
        let elapsed = start.elapsed().as_nanos() as u64;
        if status != StatusCode::CREATED {
            return Err(format!(
                "import: {status} {}",
                String::from_utf8_lossy(&reply)
            ));
        }
        let reply: Value = serde_json::from_slice(&reply).map_err(|e| e.to_string())?;
        let counts = json!([
            reply["node_count"],
            reply["edge_count"],
            reply["active_node_count"],
            reply["enabled_edge_count"],
            reply["effective_edge_count"]
        ]);
        if *reply_counts.get_or_insert_with(|| counts.clone()) != counts {
            return Err("import counts differ between requests".into());
        }
        drop(app);
        if rep >= warmup {
            times.push(elapsed);
        }
    }
    let observation = median(&mut times.clone());
    Ok(
        json!({"kind":"http-import","engine":engine.as_str(),"observation_ns":observation,"times_ns":times,
              "body_bytes":body_bytes,"counts":reply_counts,"rss_bytes":rss_bytes()}),
    )
}

fn churn(args: &Args) -> Result<Value, String> {
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let cycles: usize = args.num("cycles")?;
    let percent: u64 = args.num("churn-percent")?;
    let seed: u64 = args.num("seed")?;
    let reuse = args.get("reuse")?;
    let edges = generate(topology, n, seed);
    let (plan, expected) = schedule(n, &edges, reuse, cycles, percent, seed)?;
    let engine = engine_arg(args)?;
    let mut graph = <LifecycleGraph as Subject>::build(engine, n, &edges);
    let mut total: u64 = 0;
    let mut slowest: u64 = 0;
    let mut operations: u64 = 0;
    let mut compactions = 0;
    let mut cycle_ns = Vec::with_capacity(cycles);
    for (index, ops) in plan.iter().enumerate() {
        let mut cycle_total = 0;
        for &op in ops {
            let vertices = graph.engine_vertex_count();
            let start = Instant::now();
            graph.apply(op);
            let elapsed = start.elapsed().as_nanos() as u64;
            cycle_total += elapsed;
            slowest = slowest.max(elapsed);
            operations += 1;
            compactions += usize::from(graph.engine_vertex_count() < vertices);
        }
        total += cycle_total;
        cycle_ns.push(cycle_total);
        let logical = [
            graph.node_count(),
            graph.edge_count(),
            graph.active_node_count(),
            graph.enabled_edge_count(),
            graph.effective_edge_count(),
        ];
        if logical != expected[index + 1] {
            return Err(format!("logical counts diverge at cycle {}", index + 1));
        }
    }
    Ok(
        json!({"kind":"churn","engine":engine.as_str(),"observation_ns":total,"cycle_ns":cycle_ns,"slowest_op_ns":slowest,
              "operations":operations,"compactions":compactions,
              "engine_vertices":graph.engine_vertex_count(),"nodes":graph.node_count(),
              // knotrel#151 C1: the cross-arm gate (added fields only).
              "gate":{"operations":operations,"edges":edges.len(),
                      "logical":lifecycle_probes::compact::logical(&graph),
                      "storage":lifecycle_probes::compact::storage_entries(&graph)},
              "rss_bytes":rss_bytes()}),
    )
}

fn main() -> ExitCode {
    let mut items = std::env::args().skip(1);
    let command = items.next().unwrap_or_default();
    println!("{}", build_record("release-cells"));
    let result = Args::parse(items).and_then(|args| match command.as_str() {
        "core-import" => core_import(&args),
        "http-import" => tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| e.to_string())
            .and_then(|runtime| runtime.block_on(http_import(&args))),
        "churn" => churn(&args),
        other => Err(format!("unknown command {other:?}")),
    });
    match result {
        Ok(value) => {
            println!("{value}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("release-cells: {error}");
            ExitCode::FAILURE
        }
    }
}
