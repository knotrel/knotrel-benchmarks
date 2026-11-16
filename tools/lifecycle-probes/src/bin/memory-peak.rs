//! Memory peak diagnostic (D4, v0.5.0 remediation; not a qualification probe).
//!
//! Built only with `--features peak-alloc`. The global allocator is
//! `cap::Cap<System>` with its `stats` feature, which tracks the bytes
//! currently requested from the global allocator (`allocated`) and their
//! running maximum (`max_allocated`). A reallocation is counted at its
//! resulting size; the allocator's internal copy during a reallocation and
//! allocator metadata are not counted. The maximum cannot be reset, so every
//! report gives the high-water mark before and after an interval: a peak
//! inside the interval is exact when the high-water mark rose during it, and
//! is otherwise only known to be at most the earlier mark.
//!
//! ```text
//! memory-peak churn --engine E --topology T --nodes N --cycles C
//!     --churn-percent P --reuse fresh|same|toggle --seed S
//! memory-peak hdt-levels --topology T --nodes N --cycles C --churn-percent P
//!     --reuse same|toggle --seed S --every K
//! memory-peak import-core --engine E --topology T --nodes N
//!     --inactive-percent I --disabled-percent D --seed S
//! memory-peak import-http --engine E --topology T --nodes N
//!     --inactive-percent I --disabled-percent D --seed S --mode create|replace
//! ```
//!
//! `churn` replays the exact `core-lifecycle resources` schedule (`lifecycle_probes::churn`; the
//! logical counts it prints must equal run 3's) on the lifecycle arm. `hdt-levels` applies the same
//! schedule's effective-graph changes directly to an `HdtGraph` and prints
//! its per-level structural counters. The import commands prepare every input
//! first (the HTTP body is built by string formatting, without a JSON value
//! tree) and then measure only the build or the import request.

use axum::{
    Router,
    body::{Body, Bytes, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_core::{EdgeSpec, EngineConfig, GraphLimits, HdtGraph, LifecycleGraph, NodeSpec};
use knotrel_server::{ServerConfig, ServerMode, router_with_config};
use lifecycle_probes::churn::{Model, schedule};
use lifecycle_probes::{
    Op, Rng, Subject, Topology, build_record, generate, parse_engine, rss_bytes,
};
use serde_json::{Value, json};
use std::{alloc::System, collections::HashMap, fmt::Write as _, process::ExitCode};
use tower::ServiceExt;

#[global_allocator]
static GLOBAL: cap::Cap<System> = cap::Cap::new(System, usize::MAX);

/// Current live requested heap and its running maximum, in bytes.
fn heap() -> (usize, usize) {
    (GLOBAL.allocated(), GLOBAL.max_allocated())
}

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

// ---- churn: lifecycle arm with peak tracking ----

fn churn(args: &Args) -> Result<(), String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let cycles: usize = args.num("cycles")?;
    let percent: u64 = args.num("churn-percent")?;
    let seed: u64 = args.num("seed")?;
    let reuse = args.get("reuse")?;
    let edges = generate(topology, n, seed);
    let (plan, expected) = schedule(n, &edges, reuse, cycles, percent, seed)?;
    let (base_live, base_peak) = heap();
    println!(
        "{}",
        json!({"kind":"baseline","live_heap_bytes":base_live,"peak_heap_bytes":base_peak,"rss_bytes":rss_bytes()})
    );
    let mut graph = <LifecycleGraph as Subject>::build(engine, n, &edges);
    let mut previous_peak = base_peak;
    let mut previous_vertices = graph.engine_vertex_count();
    for cycle in 0..=cycles {
        if cycle > 0 {
            for &op in &plan[cycle - 1] {
                graph.apply(op);
            }
        }
        let (live, peak) = heap();
        let storage = graph.storage_stats();
        let vertices = storage.engine_vertices;
        println!(
            "{}",
            json!({"kind":"checkpoint","cycle":cycle,
                   "logical":[graph.node_count(), graph.edge_count(), graph.active_node_count(),
                              graph.enabled_edge_count(), graph.effective_edge_count()],
                   "expected": expected[cycle],
                   "engine_vertices": vertices, "retired_vertices": storage.retired_vertices,
                   "compacted_in_cycle": cycle > 0 && vertices < previous_vertices,
                   "catalog_nodes": storage.catalog_nodes, "catalog_node_capacity": storage.catalog_node_capacity,
                   "incident_entries": storage.incident_entries, "incident_capacity": storage.incident_capacity,
                   "live_heap_bytes": live, "net_live_heap_bytes": live as i64 - base_live as i64,
                   "peak_heap_bytes": peak, "peak_rose_in_cycle": peak > previous_peak,
                   "rss_bytes": rss_bytes()})
        );
        previous_peak = peak;
        previous_vertices = vertices;
    }
    Ok(())
}

// ---- hdt-levels: engine-level replay of the effective-graph changes ----

fn hdt_levels(args: &Args) -> Result<(), String> {
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let cycles: usize = args.num("cycles")?;
    let percent: u64 = args.num("churn-percent")?;
    let seed: u64 = args.num("seed")?;
    let every: usize = args.num("every")?;
    let reuse = args.get("reuse")?;
    if reuse == "fresh" {
        return Err(
            "hdt-levels supports same and toggle (fresh IDs need facade compaction)".into(),
        );
    }
    let edges = generate(topology, n, seed);
    let (plan, _) = schedule(n, &edges, reuse, cycles, percent, seed)?;
    let (base_live, _) = heap();
    let mut model = Model::default();
    let mut graph = HdtGraph::new();
    for v in 0..n {
        model.apply(Op::AddNode(v));
        graph.add_node(v);
    }
    for &(a, b) in &edges {
        model.apply(Op::Link(a, b));
        graph.link(a, b).map_err(|e| e.to_string())?;
    }
    let report = |cycle: usize, graph: &HdtGraph| {
        let (live, peak) = heap();
        let s = graph.storage_stats();
        let levels: Vec<Value> = s
            .levels
            .iter()
            .map(|l| json!({"level": l.level, "record_slots": l.vertices, "tree_edges": l.tree_edges,
                            "tree_incidences": l.tree_incidences, "non_tree_incidences": l.non_tree_incidences,
                            "token_capacity_bytes": l.token_capacity_bytes,
                            "adjacency_capacity_bytes": l.adjacency_capacity_bytes,
                            "mapping_capacity_bytes": l.mapping_capacity_bytes}))
            .collect();
        println!(
            "{}",
            json!({"kind":"levels","cycle":cycle,"edges":graph.edge_count(),
                   "vector_capacity_bytes": s.vector_capacity_bytes, "ordered_payload_bytes": s.ordered_payload_bytes,
                   "net_live_heap_bytes": live as i64 - base_live as i64, "peak_heap_bytes": peak,
                   "rss_bytes": rss_bytes(), "levels": levels})
        );
    };
    report(0, &graph);
    for (index, ops) in plan.iter().enumerate() {
        for &op in ops {
            match op {
                Op::SetNode(v, _) => {
                    let neighbors: Vec<u64> = model.adjacency[&v].iter().copied().collect();
                    let before: Vec<bool> =
                        neighbors.iter().map(|&w| model.effective(v, w)).collect();
                    model.apply(op);
                    for (w, was) in neighbors.into_iter().zip(before) {
                        let now = model.effective(v, w);
                        if was && !now {
                            graph.cut(v, w).map_err(|e| e.to_string())?;
                        } else if !was && now {
                            graph.link(v, w).map_err(|e| e.to_string())?;
                        }
                    }
                }
                Op::SetEdge(a, b, _) | Op::Link(a, b) => {
                    let was = model.effective(a, b);
                    model.apply(op);
                    let now = model.effective(a, b);
                    if was && !now {
                        graph.cut(a, b).map_err(|e| e.to_string())?;
                    } else if !was && now {
                        graph.link(a, b).map_err(|e| e.to_string())?;
                    }
                }
                Op::Remove(v) => {
                    let effective: Vec<u64> =
                        model.adjacency.get(&v).map_or_else(Vec::new, |set| {
                            set.iter()
                                .copied()
                                .filter(|&w| model.effective(v, w))
                                .collect()
                        });
                    for w in effective {
                        graph.cut(v, w).map_err(|e| e.to_string())?;
                    }
                    model.apply(op);
                }
                Op::AddNode(v) => {
                    model.apply(op);
                    graph.add_node(v);
                }
                Op::Cut(..) | Op::Connected(..) => unreachable!("not used by churn schedules"),
            }
        }
        let cycle = index + 1;
        if graph.edge_count() != model.counts()[4] {
            return Err(format!(
                "engine edges diverge from the model at cycle {cycle}"
            ));
        }
        if cycle % every == 0 {
            report(cycle, &graph);
        }
    }
    Ok(())
}

// ---- imports ----

struct Flags {
    inactive: Vec<bool>,
    disabled: Vec<bool>,
}

/// Engine, node count, registered edges and their flags.
type FlaggedInput = (EngineConfig, u64, Vec<(u64, u64)>, Flags);

fn flagged_input(args: &Args) -> Result<FlaggedInput, String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let seed: u64 = args.num("seed")?;
    let inactive_percent: u64 = args.num("inactive-percent")?;
    let disabled_percent: u64 = args.num("disabled-percent")?;
    let edges = generate(topology, n, seed);
    // The same draws as the http-lifecycle `import` scenario.
    let mut rng = Rng(seed ^ 0x1a);
    let inactive = (0..n).map(|_| rng.below(100) < inactive_percent).collect();
    let disabled = edges
        .iter()
        .map(|_| rng.below(100) < disabled_percent)
        .collect();
    Ok((engine, n, edges, Flags { inactive, disabled }))
}

fn import_core(args: &Args) -> Result<(), String> {
    let (engine, n, edges, flags) = flagged_input(args)?;
    let nodes: Vec<NodeSpec> = (0..n)
        .map(|v| NodeSpec {
            node: v,
            active: !flags.inactive[v as usize],
        })
        .collect();
    let specs: Vec<EdgeSpec> = edges
        .iter()
        .zip(&flags.disabled)
        .map(|(&(source, target), &off)| EdgeSpec {
            source,
            target,
            enabled: !off,
        })
        .collect();
    drop(edges);
    let (live_before, peak_before) = heap();
    let graph = LifecycleGraph::try_from_topology(engine, GraphLimits::default(), &nodes, &specs)
        .map_err(|e| e.to_string())?;
    let (live_after, peak_after) = heap();
    let storage = graph.storage_stats();
    println!(
        "{}",
        json!({"kind":"import-core","live_before":live_before,"peak_before":peak_before,
               "live_after":live_after,"peak_after":peak_after,
               "peak_exact": peak_after > peak_before,
               "transient_over_final": peak_after as i64 - live_after as i64,
               "graph_bytes": live_after as i64 - live_before as i64,
               "nodes": graph.node_count(), "edges": graph.edge_count(), "effective": graph.effective_edge_count(),
               "catalog_node_capacity": storage.catalog_node_capacity, "incident_capacity": storage.incident_capacity,
               "rss_bytes": rss_bytes()})
    );
    drop(graph);
    Ok(())
}

fn import_body(mode: &str, instance: &str, n: u64, edges: &[(u64, u64)], flags: &Flags) -> Bytes {
    let mut body = String::with_capacity(64 * edges.len() + 32 * n as usize + 512);
    write!(
        body,
        r#"{{"mode":"{mode}","instance_id":"{instance}","graph_id":"default","source_id":"src","source_epoch":"e1","source_position":"p0","feeder_session_id":"s","feeder_epoch":1,"nodes":["#
    )
    .unwrap();
    for v in 0..n {
        if v > 0 {
            body.push(',');
        }
        if flags.inactive[v as usize] {
            write!(body, r#"{{"node":"{v}","active":false}}"#).unwrap();
        } else {
            write!(body, r#""{v}""#).unwrap();
        }
    }
    body.push_str(r#"],"edges":["#);
    for (i, (&(a, b), &off)) in edges.iter().zip(&flags.disabled).enumerate() {
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

async fn send(app: &Router, request: Request<Body>) -> (StatusCode, Option<String>, Vec<u8>) {
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let etag = response
        .headers()
        .get("etag")
        .map(|v| v.to_str().unwrap().to_owned());
    let bytes = to_bytes(response.into_body(), 64 << 20)
        .await
        .unwrap()
        .to_vec();
    (status, etag, bytes)
}

async fn import_http(args: &Args) -> Result<(), String> {
    let (engine, n, edges, flags) = flagged_input(args)?;
    let mode = args.get("mode")?;
    let config = ServerConfig::new("127.0.0.1:0".parse().unwrap(), engine, 32)
        .map_err(|e| e.to_string())?
        .with_mode(ServerMode::SourceManaged)
        .with_topology_lifecycle(true)
        .map_err(|e| e.to_string())?
        .with_metrics_enabled(false)
        .with_graph_limits(GraphLimits::default());
    let app = router_with_config(config);
    let (_, _, info) = send(&app, Request::get("/v1/info").body(Body::empty()).unwrap()).await;
    let info: Value = serde_json::from_slice(&info).map_err(|e| e.to_string())?;
    let instance = info["instance_id"]
        .as_str()
        .ok_or("no instance id")?
        .to_owned();
    let session = json!({"instance_id":instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000}).to_string();
    let request = |path: &str, body: Bytes, etag: Option<&str>| {
        let mut builder = Request::post(path)
            .header("content-type", "application/json")
            .header("x-knotrel-instance-id", instance.as_str());
        if let Some(etag) = etag {
            builder = builder.header("if-match", etag);
        }
        builder.body(Body::from(body)).unwrap()
    };
    let (status, _, _) = send(
        &app,
        request("/v1/feeder/session", Bytes::from(session), None),
    )
    .await;
    if status != StatusCode::OK {
        return Err(format!("session: {status}"));
    }
    let mut etag = None;
    if mode == "replace" {
        let body = import_body("create_only", &instance, n, &edges, &flags);
        let (status, tag, _) = send(&app, request("/v1/feeder/import", body, None)).await;
        if status != StatusCode::CREATED {
            return Err(format!("initial import: {status}"));
        }
        etag = Some(tag.ok_or("no etag after initial import")?);
    }
    let body = import_body(
        if mode == "replace" {
            "replace"
        } else {
            "create_only"
        },
        &instance,
        n,
        &edges,
        &flags,
    );
    let body_bytes = body.len();
    let (live_before, peak_before) = heap();
    let (status, _, reply) = send(&app, request("/v1/feeder/import", body, etag.as_deref())).await;
    let (live_after, peak_after) = heap();
    if !status.is_success() {
        return Err(format!(
            "measured import: {status} {}",
            String::from_utf8_lossy(&reply)
        ));
    }
    println!(
        "{}",
        json!({"kind":"import-http","mode":mode,"status":status.as_u16(),"body_bytes":body_bytes,
               "live_before":live_before,"peak_before":peak_before,"live_after":live_after,"peak_after":peak_after,
               "peak_exact": peak_after > peak_before,
               "transient_over_final": peak_after as i64 - live_after as i64,
               "transient_over_before": peak_after as i64 - live_before as i64,
               "rss_bytes": rss_bytes()})
    );
    Ok(())
}

fn main() -> ExitCode {
    let mut items = std::env::args().skip(1);
    let command = items.next().unwrap_or_default();
    println!("{}", build_record("memory-peak"));
    let result = Args::parse(items).and_then(|args| match command.as_str() {
        "churn" => churn(&args),
        "hdt-levels" => hdt_levels(&args),
        "import-core" => import_core(&args),
        "import-http" => tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| e.to_string())
            .and_then(|rt| rt.block_on(import_http(&args))),
        _ => Err(
            "usage: memory-peak churn|hdt-levels|import-core|import-http --flag value ...".into(),
        ),
    });
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
