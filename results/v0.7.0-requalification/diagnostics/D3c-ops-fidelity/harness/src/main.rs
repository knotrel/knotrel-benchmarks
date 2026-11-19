//! D3c diagnostic (DIAGNOSTICS-PLAN-3.md): B4 `ops` sparse 100k on one binary, one process,
//! one workload. Not part of the qualification.
//!
//! Each pair, in a rotating order, runs three server windows through the real router on
//! fresh standalone servers built as the frozen probe builds them:
//! - `L`: lifecycle server, the lifecycle trace in batches of 256;
//! - `P`: plain server, the frozen planner's legacy operations (planning untimed: the
//!   frozen reference);
//! - `PP`: plain server, the same requests, with the planner's planning of each 256-op chunk
//!   timed inside the window before that chunk's requests (the future reference).
//!
//! and two core replays of the same operations (`core-L`, `core-P`) with one clock pair per
//! call, the method the instrumented server (`d3c-instrument.diff`) uses around each
//! `state.apply`. The server's apply-phase and in-call totals are read per window.
//!
//! ```text
//! d3c-ops --nodes 100000 --requests 40 --seed 5000001 --pairs 24 --warmup 2
//! ```

use axum::{
    Router,
    body::{Body, Bytes, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_core::{EngineConfig, LifecycleGraph};
use knotrel_server::{ServerConfig, ServerMode, router_with_config};
use lifecycle_probes::{Mix, Op, Plain, Subject, Topology, generate, trace};
use rustc_hash::FxHashMap;
use serde_json::{Value, json};
use std::{collections::HashMap, hint::black_box, time::Instant};
use tower::ServiceExt;

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

const BATCH: usize = 1_024;

fn config(lifecycle: bool) -> ServerConfig {
    ServerConfig::new("127.0.0.1:0".parse().unwrap(), EngineConfig::CompactBfs, 32)
        .unwrap()
        .with_mode(ServerMode::Standalone)
        .with_topology_lifecycle(lifecycle)
        .expect("compact-bfs supports lifecycle")
        .with_metrics_enabled(false)
        .with_graph_limits(knotrel_core::GraphLimits::default())
}

/// The frozen probe's wire encoding of one operation.
fn wire(op: &Op) -> Value {
    match *op {
        Op::AddNode(v) => json!({"op":"add_node","node":v.to_string()}),
        Op::Link(a, b) => json!({"op":"link","source":a.to_string(),"target":b.to_string()}),
        Op::Cut(a, b) => json!({"op":"cut","source":a.to_string(),"target":b.to_string()}),
        Op::Connected(a, b) => json!({"op":"connected","source":a.to_string(),"target":b.to_string()}),
        Op::SetNode(v, f) => json!({"op":"set_node_active","node":v.to_string(),"active":f}),
        Op::SetEdge(a, b, f) => json!({"op":"set_edge_enabled","source":a.to_string(),"target":b.to_string(),"enabled":f}),
        Op::Remove(v) => json!({"op":"remove_node","node":v.to_string()}),
    }
}

fn batch_body(ops: &[Op]) -> Bytes {
    Bytes::from(json!({"operations": ops.iter().map(wire).collect::<Vec<_>>()}).to_string())
}

async fn post(app: &Router, body: Bytes) -> StatusCode {
    let request = Request::post("/v1/batch").header("content-type", "application/json").body(Body::from(body)).unwrap();
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let _ = to_bytes(response.into_body(), 64 << 20).await.unwrap();
    status
}

/// The frozen probe's `standalone`: `add_node` for every node, then `link` for every edge,
/// in batches of 1,024.
async fn standalone(lifecycle: bool, n: u64, edges: &[(u64, u64)]) -> Router {
    let app = router_with_config(config(lifecycle));
    let mut ops: Vec<Op> = (0..n).map(Op::AddNode).collect();
    ops.extend(edges.iter().map(|&(a, b)| Op::Link(a, b)));
    for chunk in ops.chunks(BATCH) {
        assert_eq!(post(&app, batch_body(chunk)).await, StatusCode::OK);
    }
    app
}

/// Application-side planner, verbatim from the frozen `http-lifecycle.rs`.
#[derive(Default, Clone)]
struct Planner {
    nodes: FxHashMap<u64, (bool, FxHashMap<u64, bool>)>,
}

impl Planner {
    fn new(n: u64, edges: &[(u64, u64)]) -> Self {
        let mut planner = Self::default();
        let mut sink = Vec::new();
        for v in 0..n {
            planner.plan(Op::AddNode(v), &mut sink);
        }
        for &(a, b) in edges {
            planner.plan(Op::Link(a, b), &mut sink);
        }
        planner
    }
    fn active(&self, v: u64) -> bool {
        self.nodes.get(&v).is_some_and(|node| node.0)
    }
    fn plan(&mut self, op: Op, out: &mut Vec<Op>) {
        match op {
            Op::AddNode(v) => {
                if let std::collections::hash_map::Entry::Vacant(entry) = self.nodes.entry(v) {
                    entry.insert((true, FxHashMap::default()));
                    out.push(Op::AddNode(v));
                }
            }
            Op::Link(a, b) => {
                if a == b || self.nodes.get(&a).is_some_and(|n| n.1.contains_key(&b)) {
                    return;
                }
                self.plan(Op::AddNode(a), out);
                self.plan(Op::AddNode(b), out);
                self.nodes.get_mut(&a).unwrap().1.insert(b, true);
                self.nodes.get_mut(&b).unwrap().1.insert(a, true);
                if self.active(a) && self.active(b) {
                    out.push(Op::Link(a, b));
                }
            }
            Op::Cut(a, b) => {
                let Some(enabled) = self.nodes.get(&a).and_then(|n| n.1.get(&b).copied()) else {
                    return;
                };
                let effective = enabled && self.active(a) && self.active(b);
                self.nodes.get_mut(&a).unwrap().1.remove(&b);
                self.nodes.get_mut(&b).unwrap().1.remove(&a);
                if effective {
                    out.push(Op::Cut(a, b));
                }
            }
            Op::SetNode(v, active) => {
                let Some(node) = self.nodes.get(&v) else {
                    return;
                };
                if node.0 == active {
                    return;
                }
                for (&w, &enabled) in &node.1 {
                    if enabled && self.active(w) {
                        out.push(if active { Op::Link(v, w) } else { Op::Cut(v, w) });
                    }
                }
                self.nodes.get_mut(&v).unwrap().0 = active;
            }
            Op::SetEdge(a, b, enabled) => {
                let Some(&current) = self.nodes.get(&a).and_then(|n| n.1.get(&b)) else {
                    return;
                };
                if current == enabled || !self.nodes.contains_key(&b) {
                    return;
                }
                self.nodes.get_mut(&a).unwrap().1.insert(b, enabled);
                self.nodes.get_mut(&b).unwrap().1.insert(a, enabled);
                if self.active(a) && self.active(b) {
                    out.push(if enabled { Op::Link(a, b) } else { Op::Cut(a, b) });
                }
            }
            Op::Remove(v) => {
                let Some((active, neighbors)) = self.nodes.remove(&v) else {
                    return;
                };
                for (w, enabled) in neighbors {
                    let node = self.nodes.get_mut(&w).unwrap();
                    node.1.remove(&v);
                    if enabled && active && node.0 {
                        out.push(Op::Cut(v, w));
                    }
                }
            }
            Op::Connected(a, b) => {
                if self.active(a) && self.active(b) {
                    out.push(Op::Connected(a, b));
                }
            }
        }
    }
}


/// One clock pair per call, as the instrumented server does around `state.apply`.
fn core_per_call<S: Subject>(graph: &mut S, ops: &[Op]) -> u64 {
    let mut total = 0u64;
    for &op in ops {
        let t = Instant::now();
        black_box(graph.apply(op));
        total += t.elapsed().as_nanos() as u64;
    }
    total
}

struct Window {
    ns: u64,
    planning_ns: u64,
    counters: [u64; 4],
}

async fn window(app: &Router, chunks: &[Vec<Bytes>], planner: Option<(&mut Planner, &[Op])>) -> Window {
    knotrel_server::d3c::reset();
    let mut planning_ns = 0u64;
    let start = Instant::now();
    match planner {
        None => {
            for body in chunks.iter().flatten() {
                assert!(post(app, body.clone()).await.is_success());
            }
        }
        Some((planner, ops)) => {
            for (chunk, bodies) in ops.chunks(256).zip(chunks) {
                let t = Instant::now();
                let mut legacy = Vec::new();
                for &op in chunk {
                    planner.plan(op, &mut legacy);
                }
                black_box(&legacy);
                planning_ns += t.elapsed().as_nanos() as u64;
                for body in bodies {
                    assert!(post(app, body.clone()).await.is_success());
                }
            }
        }
    }
    let ns = start.elapsed().as_nanos() as u64;
    Window { ns, planning_ns, counters: knotrel_server::d3c::snapshot() }
}

fn main() {
    let mut args = HashMap::new();
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        args.insert(k.trim_start_matches("--").to_owned(), it.next().unwrap_or_default());
    }
    let num = |k: &str| args.get(k).unwrap_or_else(|| panic!("--{k}")).parse::<u64>().unwrap();
    let (n, requests, seed, pairs, warmup) = (num("nodes"), num("requests"), num("seed"), num("pairs"), num("warmup"));
    let edges = generate(Topology::Sparse, n, seed);
    let ops: Vec<Op> = trace(n, &edges, Mix::MutationHeavy, requests as usize * 256, seed)
        .into_iter()
        .filter(|op| !matches!(op, Op::Connected(..)))
        .collect();
    // Request bodies, prebuilt untimed as in the frozen probe: per 256-op chunk.
    let l_chunks: Vec<Vec<Bytes>> = ops.chunks(256).map(|c| vec![batch_body(c)]).collect();
    let mut planner = Planner::new(n, &edges);
    let base_planner = planner.clone();
    let mut plain_ops = Vec::new();
    let mut p_chunks: Vec<Vec<Bytes>> = Vec::new();
    for chunk in ops.chunks(256) {
        let mut legacy = Vec::new();
        for &op in chunk {
            planner.plan(op, &mut legacy);
        }
        p_chunks.push(legacy.chunks(BATCH).map(batch_body).collect());
        plain_ops.extend(legacy);
    }
    println!("{}", json!({"kind":"setup","nodes":n,"edges":edges.len(),"lifecycle_ops":ops.len(),"plain_ops":plain_ops.len(),
        "lifecycle_requests":l_chunks.iter().map(Vec::len).sum::<usize>(),"plain_requests":p_chunks.iter().map(Vec::len).sum::<usize>(),
        "counters":knotrel_server::d3c::NAMES}));
    let rt = tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap();
    let orders = [["L", "P", "PP", "core-L", "core-P"], ["P", "PP", "core-L", "core-P", "L"], ["PP", "core-L", "core-P", "L", "P"],
                  ["core-L", "core-P", "L", "P", "PP"], ["core-P", "L", "P", "PP", "core-L"]];
    for i in 0..(warmup + pairs) {
        let order = orders[(i % 5) as usize];
        let mut row = serde_json::Map::new();
        for arm in order {
            let value = match arm {
                "L" => {
                    let app = rt.block_on(standalone(true, n, &edges));
                    let w = rt.block_on(window(&app, &l_chunks, None));
                    json!({"window_ns":w.ns,"counters":w.counters})
                }
                "P" => {
                    let app = rt.block_on(standalone(false, n, &edges));
                    let w = rt.block_on(window(&app, &p_chunks, None));
                    json!({"window_ns":w.ns,"counters":w.counters})
                }
                "PP" => {
                    let app = rt.block_on(standalone(false, n, &edges));
                    let mut fresh = base_planner.clone();
                    let w = rt.block_on(window(&app, &p_chunks, Some((&mut fresh, &ops))));
                    json!({"window_ns":w.ns,"planning_ns":w.planning_ns,"counters":w.counters})
                }
                "core-L" => {
                    let mut g = <LifecycleGraph as Subject>::build(EngineConfig::CompactBfs, n, &edges);
                    json!({"per_call_ns":core_per_call(&mut g, &ops)})
                }
                _ => {
                    let mut g = <Plain as Subject>::build(EngineConfig::CompactBfs, n, &edges);
                    json!({"per_call_ns":core_per_call(&mut g, &plain_ops)})
                }
            };
            row.insert(arm.to_string(), value);
        }
        println!("{}", json!({"kind":"pair","index":i,"warmup":i < warmup,"order":order,"arms":row}));
    }
}
