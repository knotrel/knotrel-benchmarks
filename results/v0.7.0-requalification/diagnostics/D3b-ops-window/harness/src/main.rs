//! D3b diagnostic (DIAGNOSTICS-PLAN-2.md): core-level replay of the B4 `ops` sparse 100k
//! window. Not part of the qualification.
//!
//! Every pair of the frozen `http-lifecycle --scenario ops` builds fresh arms and sends the
//! same deterministic trace, so the window replays exactly at core level:
//! - lifecycle arm: the trace (`connected` filtered out, as in `ops`) applied to a
//!   `LifecycleGraph` built as the probe's `standalone` server builds it (`add_node` then
//!   `link`, incrementally);
//! - plain arm: the probe's application planner (copied verbatim) turns the trace, in
//!   chunks of 256, into legacy operations applied to a plain `ConnectivityGraph`.
//!   Planning is untimed, as in the frozen reference.
//!
//! Modes: `time` (whole-window replays, alternating arms; plus a separate per-operation
//! pass with one clock read per operation), `profile` (repeated replays for `sample`),
//! and with the `counters` feature `counters` (work counters per operation type, against
//! the instrumented core of `d3b-counters.diff`).
//!
//! ```text
//! d3b-replay time --nodes 100000 --requests 40 --seed 5000001 --replays 24 --warmup 2
//! d3b-replay profile --arm lifecycle --seconds 10 ...
//! d3b-replay counters ...
//! ```

use knotrel_core::{EngineConfig, LifecycleGraph};
use lifecycle_probes::{Mix, Op, Plain, Subject, Topology, generate, trace};
use rustc_hash::FxHashMap;
use serde_json::json;
use std::{collections::HashMap, hint::black_box, time::Instant};

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

/// Application-side planner, verbatim from the frozen `http-lifecycle.rs`.
#[derive(Default)]
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

fn kind(op: &Op) -> &'static str {
    match op {
        Op::AddNode(_) => "add_node",
        Op::Link(..) => "link",
        Op::Cut(..) => "cut",
        Op::Connected(..) => "connected",
        Op::SetNode(_, true) => "set_node_active(true)",
        Op::SetNode(_, false) => "set_node_active(false)",
        Op::SetEdge(_, _, true) => "set_edge_enabled(true)",
        Op::SetEdge(_, _, false) => "set_edge_enabled(false)",
        Op::Remove(_) => "remove_node",
    }
}

#[inline(never)]
fn replay_lifecycle(graph: &mut LifecycleGraph, ops: &[Op]) -> u64 {
    let mut digest = 0u64;
    for &op in ops {
        digest = digest.wrapping_mul(31).wrapping_add(graph.apply(op));
    }
    digest
}

#[inline(never)]
fn replay_plain(graph: &mut Plain, ops: &[Op]) -> u64 {
    let mut digest = 0u64;
    for &op in ops {
        digest = digest.wrapping_mul(31).wrapping_add(graph.apply(op));
    }
    digest
}

fn per_op<S: Subject>(graph: &mut S, ops: &[Op], acc: &mut HashMap<&'static str, (u64, u64, u64)>) {
    for &op in ops {
        let start = Instant::now();
        let code = graph.apply(op);
        let ns = start.elapsed().as_nanos() as u64;
        let e = acc.entry(kind(&op)).or_default();
        e.0 += 1;
        e.1 += ns;
        e.2 += u64::from(code == 0);
    }
}

fn main() {
    let mut argv = std::env::args().skip(1);
    let mode = argv.next().expect("mode");
    let mut args = HashMap::new();
    while let Some(k) = argv.next() {
        args.insert(k.trim_start_matches("--").to_owned(), argv.next().unwrap_or_default());
    }
    let num = |k: &str| args.get(k).unwrap_or_else(|| panic!("--{k}")).parse::<u64>().unwrap();
    let (n, requests, seed) = (num("nodes"), num("requests"), num("seed"));
    let edges = generate(Topology::Sparse, n, seed);
    let ops: Vec<Op> = trace(n, &edges, Mix::MutationHeavy, requests as usize * 256, seed)
        .into_iter()
        .filter(|op| !matches!(op, Op::Connected(..)))
        .collect();
    let mut planner = Planner::new(n, &edges);
    let mut plain_ops = Vec::new();
    for chunk in ops.chunks(256) {
        for &op in chunk {
            planner.plan(op, &mut plain_ops);
        }
    }
    let mut mix: HashMap<&str, [u64; 2]> = HashMap::new();
    for op in &ops {
        mix.entry(kind(op)).or_default()[0] += 1;
    }
    for op in &plain_ops {
        mix.entry(kind(op)).or_default()[1] += 1;
    }
    println!("{}", json!({"kind":"setup","nodes":n,"edges":edges.len(),"lifecycle_ops":ops.len(),"plain_ops":plain_ops.len(),"mix":mix}));
    let build_l = || <LifecycleGraph as Subject>::build(EngineConfig::CompactBfs, n, &edges);
    let build_p = || <Plain as Subject>::build(EngineConfig::CompactBfs, n, &edges);
    match mode.as_str() {
        "time" => {
            let (replays, warmup) = (num("replays"), num("warmup"));
            for i in 0..(warmup + replays) {
                let mut row = serde_json::Map::new();
                let order = if i % 2 == 0 { ["lifecycle", "plain"] } else { ["plain", "lifecycle"] };
                for arm in order {
                    let ns = if arm == "lifecycle" {
                        let mut g = build_l();
                        let s = Instant::now();
                        black_box(replay_lifecycle(&mut g, &ops));
                        s.elapsed().as_nanos() as u64
                    } else {
                        let mut g = build_p();
                        let s = Instant::now();
                        black_box(replay_plain(&mut g, &plain_ops));
                        s.elapsed().as_nanos() as u64
                    };
                    row.insert(arm.into(), json!(ns));
                }
                let mut types = serde_json::Map::new();
                for arm in order {
                    let mut acc = HashMap::new();
                    if arm == "lifecycle" { per_op(&mut build_l(), &ops, &mut acc) } else { per_op(&mut build_p(), &plain_ops, &mut acc) }
                    types.insert(arm.into(), json!(acc.iter().map(|(k, v)| (k.to_string(), json!({"count":v.0,"ns":v.1,"noop":v.2}))).collect::<serde_json::Map<_, _>>()));
                }
                println!("{}", json!({"kind":"replay","index":i,"warmup":i < warmup,"order":order,"window_ns":row,"per_op":types}));
            }
        }
        "planner" => {
            // Supplementary (declared in the README): the reference's application-side
            // planning of the same trace, untimed in the frozen probe, timed here.
            let (replays, warmup) = (num("replays"), num("warmup"));
            for i in 0..(warmup + replays) {
                let mut planner = Planner::new(n, &edges);
                let mut out = Vec::with_capacity(plain_ops.len());
                let s = Instant::now();
                for chunk in ops.chunks(256) {
                    for &op in chunk {
                        planner.plan(op, &mut out);
                    }
                }
                let ns = s.elapsed().as_nanos() as u64;
                assert_eq!(out.len(), plain_ops.len());
                println!("{}", json!({"kind":"planner","index":i,"warmup":i < warmup,"ns":ns}));
            }
        }
        "profile" => {
            let arm = args.get("arm").expect("--arm").clone();
            let until = Instant::now() + std::time::Duration::from_secs(num("seconds"));
            let mut replays = 0u64;
            while Instant::now() < until {
                if arm == "lifecycle" {
                    let mut g = build_l();
                    black_box(replay_lifecycle(&mut g, &ops));
                } else {
                    let mut g = build_p();
                    black_box(replay_plain(&mut g, &plain_ops));
                }
                replays += 1;
            }
            println!("{}", json!({"kind":"profile","arm":arm,"replays":replays}));
        }
        #[cfg(feature = "counters")]
        "counters" => {
            for (arm, list) in [("lifecycle", &ops), ("plain", &plain_ops)] {
                let mut per: HashMap<&'static str, (u64, [u64; 10])> = HashMap::new();
                let mut gl = (arm == "lifecycle").then(build_l);
                let mut gp = (arm == "plain").then(build_p);
                for &op in list.iter() {
                    let before = knotrel_core::diag_d3b::snapshot();
                    let code = match (&mut gl, &mut gp) {
                        (Some(g), _) => g.apply(op),
                        (_, Some(g)) => g.apply(op),
                        _ => unreachable!(),
                    };
                    let after = knotrel_core::diag_d3b::snapshot();
                    let e = per.entry(kind(&op)).or_default();
                    e.0 += u64::from(code == 0);
                    for i in 0..10 {
                        e.1[i] += after[i] - before[i];
                    }
                }
                let out: serde_json::Map<_, _> = per.iter().map(|(k, (noop, c))| (k.to_string(), json!({"noop":noop,
                    "counters": knotrel_core::diag_d3b::NAMES.iter().zip(c).map(|(n, v)| (n.to_string(), json!(v))).collect::<serde_json::Map<_, _>>()}))).collect();
                println!("{}", json!({"kind":"counters","arm":arm,"per_type":out}));
            }
        }
        other => panic!("unknown mode {other}"),
    }
}
