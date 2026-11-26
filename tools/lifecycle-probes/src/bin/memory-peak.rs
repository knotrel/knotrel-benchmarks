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
//! memory-peak cf5-random --engine E --vertices V --degree D --seed S
//! memory-peak compact-import --engine E --workload W --nodes N [--degree D] --seed S
//! memory-peak compact-build --engine E --workload W --nodes N [--degree D] --seed S
//! memory-peak compact-import-http --engine E --workload W --nodes N [--degree D]
//!     --seed S --mode create|replace
//! memory-peak mass-removal --engine E --workload W --nodes N --seed S --percent P
//! ```
//!
//! The `compact-*` and `mass-removal` commands are the deterministic memory
//! cells of the knotrel#151 comparison (M1, M1-iso, M2, M3, M5;
//! `lifecycle_probes::compact`). Each prints one JSON object with net live
//! heap and high-water values relative to a baseline read after every input
//! is prepared, and a `gate` field (input fingerprint, logical counts,
//! `LifecycleStorage` entry counts; M3: the import reply's counts, the server
//! exposes no storage counts). `churn` ends with a `churn-end` record (M4):
//! live at end and high-water, both net of the baseline, and the gate.
//!
//! `cf5-random` is CF5 block K4: the K2 graph and staged orders
//! (`knotrel_benchmarks::cf5`), all insertions then all deletions through
//! `ConnectivityGraph`, with live bytes after registration, after the
//! insertions and after the deletions, and the high-water mark.
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
use lifecycle_probes::compact::{self, Workload};
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
        json!({"kind":"baseline","engine":engine.as_str(),"live_heap_bytes":base_live,"peak_heap_bytes":base_peak,"rss_bytes":rss_bytes()})
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
            json!({"kind":"checkpoint","engine":engine.as_str(),"cycle":cycle,
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
    // M4 (knotrel#151): one closing record with the cell metrics and the gate.
    let (live, peak) = heap();
    let ops = plan.iter().map(Vec::len).sum::<usize>();
    println!(
        "{}",
        json!({"kind":"churn-end","engine":engine.as_str(),
               "live_at_end": live as i64 - base_live as i64,
               "high_water": peak as i64 - base_live as i64,
               "gate": {"schedule_ops": ops, "edges": edges.len(),
                        "logical": compact::logical(&graph),
                        "expected": expected[cycles],
                        "storage": compact::storage_entries(&graph)},
               "capacities": compact::storage_capacities(&graph), "rss_bytes": rss_bytes()})
    );
    if compact::logical(&graph) != expected[cycles] {
        return Err("churn logical counts differ from the model".into());
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
        json!({"kind":"import-core","engine":engine.as_str(),"live_before":live_before,"peak_before":peak_before,
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

/// CF5 K4 (see the module documentation). Inputs are generated before the
/// baseline reading; the measured phases allocate only inside the engine.
fn cf5_random(args: &Args) -> Result<(), String> {
    use knotrel_benchmarks::cf5::{STAGED_SALT, fingerprint, orders, random_graph};
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    let vertices: u64 = args.num("vertices")?;
    let degree: u64 = args.num("degree")?;
    let seed: u64 = args.num("seed")?;
    let edges = random_graph(vertices, degree, seed)?;
    let (_, insert, delete) = orders(&edges, seed, STAGED_SALT);
    let (live_before, peak_before) = heap();
    let mut graph = knotrel_core::ConnectivityGraph::new(engine);
    for node in 0..vertices {
        graph.add_node(node).map_err(|e| e.to_string())?;
    }
    let (after_construction, _) = heap();
    for &(a, b) in &insert {
        graph.link(a, b).map_err(|e| e.to_string())?;
    }
    let (after_inserts, _) = heap();
    for &(a, b) in &delete {
        graph.cut(a, b).map_err(|e| e.to_string())?;
    }
    let (after_deletes, peak_after) = heap();
    if graph.edge_count() != 0 {
        return Err("edges left after delete-all".into());
    }
    let net = |live: usize| live as i64 - live_before as i64;
    println!(
        "{}",
        json!({"kind":"cf5-random","engine":engine.as_str(),"vertices":vertices,
               "degree":degree,"edges":edges.len(),"seed":seed,
               "edges_fingerprint":fingerprint(&edges),
               "live_after_construction":net(after_construction),
               "live_after_inserts":net(after_inserts),
               "live_after_deletes":net(after_deletes),
               "peak":net(peak_after),"peak_exact":peak_after > peak_before,
               "rss_bytes":rss_bytes()})
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
        json!({"kind":"import-http","engine":engine.as_str(),"mode":mode,"status":status.as_u16(),"body_bytes":body_bytes,
               "live_before":live_before,"peak_before":peak_before,"live_after":live_after,"peak_after":peak_after,
               "peak_exact": peak_after > peak_before,
               "transient_over_final": peak_after as i64 - live_after as i64,
               "transient_over_before": peak_after as i64 - live_before as i64,
               "rss_bytes": rss_bytes()})
    );
    Ok(())
}

// ---- knotrel#151 memory cells ----

fn compact_workload(args: &Args) -> Result<(EngineConfig, Workload), String> {
    let engine = parse_engine(args.get("engine")?)
        .filter(|e| LifecycleGraph::supports_engine(*e))
        .ok_or("--engine is not a lifecycle engine")?;
    let nodes = args.0.get("nodes").map_or(Ok(0), |_| args.num("nodes"))?;
    let degree = args.0.get("degree").map_or(Ok(0), |_| args.num("degree"))?;
    let w = Workload::generate(args.get("workload")?, nodes, degree, args.num("seed")?)?;
    Ok((engine, w))
}

/// Net live heap, high-water and exactness relative to a baseline reading.
fn net(base: (usize, usize), now: (usize, usize)) -> Value {
    json!({"live": now.0 as i64 - base.0 as i64, "high_water": now.1 as i64 - base.0 as i64,
           "peak_exact": now.1 > base.1})
}

/// M1 and M1-iso: bulk import.
fn compact_import(args: &Args) -> Result<(), String> {
    let (engine, w) = compact_workload(args)?;
    let (nodes, specs) = compact::specs(&w);
    let base = heap();
    let graph = LifecycleGraph::try_from_topology(engine, GraphLimits::default(), &nodes, &specs)
        .map_err(|e| e.to_string())?;
    let after = heap();
    compact::check_logical(&graph, w.expected(), "import")?;
    let m = net(base, after);
    println!(
        "{}",
        json!({"kind":"compact-import","engine":engine.as_str(),"workload":w.label,
               "live_after": m["live"], "high_water": m["high_water"], "peak_exact": m["peak_exact"],
               "nodes": w.ids.len(), "edges_registered": w.edges.len(),
               "gate": compact::gate(&w, &graph), "capacities": compact::storage_capacities(&graph),
               "rss_bytes": rss_bytes()})
    );
    drop(graph);
    Ok(())
}

/// M2: incremental build in seeded random edge order.
fn compact_build(args: &Args) -> Result<(), String> {
    let (engine, w) = compact_workload(args)?;
    let edges = compact::incremental_edges(&w, args.num("seed")?);
    let base = heap();
    let graph = compact::build_incremental(engine, &w.ids, &edges)?;
    let after = heap();
    compact::check_logical(&graph, w.expected(), "build")?;
    let m = net(base, after);
    println!(
        "{}",
        json!({"kind":"compact-build","engine":engine.as_str(),"workload":w.label,
               "live_after": m["live"], "high_water": m["high_water"], "peak_exact": m["peak_exact"],
               "nodes": w.ids.len(), "edges_registered": w.edges.len(),
               "gate": compact::gate(&w, &graph), "capacities": compact::storage_capacities(&graph),
               "rss_bytes": rss_bytes()})
    );
    drop(graph);
    Ok(())
}

/// M5: remove `P`% of the nodes, then register as many fresh IDs.
fn mass_removal(args: &Args) -> Result<(), String> {
    let (engine, w) = compact_workload(args)?;
    let plan = compact::mass_plan(&w, args.num("percent")?, args.num("seed")?);
    let (nodes, specs) = compact::specs(&w);
    let base = heap();
    let mut graph =
        LifecycleGraph::try_from_topology(engine, GraphLimits::default(), &nodes, &specs)
            .map_err(|e| e.to_string())?;
    let built = heap();
    for &v in &plan.removed {
        if !graph.remove_node(v) {
            return Err(format!("remove_node({v}) reported no change"));
        }
    }
    let removed = heap();
    compact::check_logical(&graph, plan.after_removal, "after removal")?;
    let after_removal = json!({"logical": compact::logical(&graph),
                               "storage": compact::storage_entries(&graph)});
    for &v in &plan.fresh {
        if !graph.add_node(v).map_err(|e| e.to_string())? {
            return Err(format!("add_node({v}) reported no change"));
        }
    }
    let end = heap();
    compact::check_logical(&graph, plan.at_end, "at end")?;
    let mut gate = compact::gate(&w, &graph);
    gate["after_removal"] = after_removal;
    println!(
        "{}",
        json!({"kind":"mass-removal","engine":engine.as_str(),"workload":w.label,
               "live_after_build": built.0 as i64 - base.0 as i64,
               "live_after_removal": removed.0 as i64 - base.0 as i64,
               "high_water": end.1 as i64 - base.0 as i64,
               "high_water_rose_after_build": end.1 > built.1,
               "live_at_end": end.0 as i64 - base.0 as i64,
               "removed": plan.removed.len(), "gate": gate,
               "capacities": compact::storage_capacities(&graph), "rss_bytes": rss_bytes()})
    );
    drop(graph);
    Ok(())
}

fn workload_body(mode: &str, instance: &str, w: &Workload) -> Bytes {
    let mut body = String::with_capacity(48 * w.edges.len() + 24 * w.ids.len() + 512);
    write!(
        body,
        r#"{{"mode":"{mode}","instance_id":"{instance}","graph_id":"default","source_id":"src","source_epoch":"e1","source_position":"p0","feeder_session_id":"s","feeder_epoch":1,"nodes":["#
    )
    .unwrap();
    for (i, v) in w.ids.iter().enumerate() {
        if i > 0 {
            body.push(',');
        }
        write!(body, r#""{v}""#).unwrap();
    }
    body.push_str(r#"],"edges":["#);
    for (i, (a, b)) in w.edges.iter().enumerate() {
        if i > 0 {
            body.push(',');
        }
        write!(body, r#"{{"source":"{a}","target":"{b}"}}"#).unwrap();
    }
    body.push_str("]}");
    Bytes::from(body)
}

/// M3: import replace with the old graph published (or create).
async fn compact_import_http(args: &Args) -> Result<(), String> {
    let (engine, w) = compact_workload(args)?;
    let mode = args.get("mode")?;
    if mode != "create" && mode != "replace" {
        return Err("--mode is create or replace".into());
    }
    let config = ServerConfig::new("127.0.0.1:0".parse().unwrap(), engine, 32)
        .map_err(|e| e.to_string())?
        .with_mode(ServerMode::SourceManaged)
        .with_topology_lifecycle(true)
        .map_err(|e| e.to_string())?
        .with_max_import_body_bytes(512 << 20)
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
    let request = |path: &str, body: Bytes, etag: Option<&str>| {
        let mut builder = Request::post(path)
            .header("content-type", "application/json")
            .header("x-knotrel-instance-id", instance.as_str());
        if let Some(etag) = etag {
            builder = builder.header("if-match", etag);
        }
        builder.body(Body::from(body)).unwrap()
    };
    let session = json!({"instance_id":instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000}).to_string();
    let (status, _, _) = send(
        &app,
        request("/v1/feeder/session", Bytes::from(session), None),
    )
    .await;
    if status != StatusCode::OK {
        return Err(format!("session: {status}"));
    }
    let reference = heap();
    let mut etag = None;
    if mode == "replace" {
        let body = workload_body("create_only", &instance, &w);
        let (status, tag, reply) = send(&app, request("/v1/feeder/import", body, None)).await;
        if status != StatusCode::CREATED {
            return Err(format!(
                "initial import: {status} {}",
                String::from_utf8_lossy(&reply)
            ));
        }
        etag = Some(tag.ok_or("no etag after initial import")?);
    }
    let published = heap();
    let body = workload_body(
        if mode == "replace" {
            "replace"
        } else {
            "create_only"
        },
        &instance,
        &w,
    );
    let body_bytes = body.len();
    let before = heap();
    let (status, _, reply) = send(&app, request("/v1/feeder/import", body, etag.as_deref())).await;
    let after = heap();
    if !status.is_success() {
        return Err(format!(
            "measured import: {status} {}",
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
    if counts != json!(w.expected()) {
        return Err(format!(
            "import counts {counts}, expected {:?}",
            w.expected()
        ));
    }
    println!(
        "{}",
        json!({"kind":"compact-import-http","engine":engine.as_str(),"workload":w.label,"mode":mode,
               "status":status.as_u16(),"body_bytes":body_bytes,
               "live_published": published.0 as i64 - reference.0 as i64,
               "high_water": after.1 as i64 - reference.0 as i64,
               "peak_exact": after.1 > before.1,
               "live_after_swap": after.0 as i64 - reference.0 as i64,
               "nodes": w.ids.len(), "edges_registered": w.edges.len(),
               "gate": {"fingerprint": w.fingerprint(), "logical": counts},
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
        "cf5-random" => cf5_random(&args),
        "compact-import" => compact_import(&args),
        "compact-build" => compact_build(&args),
        "mass-removal" => mass_removal(&args),
        "compact-import-http" => tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| e.to_string())
            .and_then(|rt| rt.block_on(compact_import_http(&args))),
        "import-http" => tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| e.to_string())
            .and_then(|rt| rt.block_on(import_http(&args))),
        _ => Err(
            "usage: memory-peak churn|hdt-levels|import-core|import-http|cf5-random|compact-import|compact-build|compact-import-http|mass-removal --flag value ..."
                .into(),
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
