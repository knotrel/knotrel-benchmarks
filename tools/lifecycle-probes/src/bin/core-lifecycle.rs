//! Core lifecycle probe: paired timing and sustained resources.
//!
//! ```text
//! core-lifecycle pairs --exp ops|optin|degree|degree-remove --engine E
//!     --topology T --nodes N --mix query|mutation|legacy|fresh-churn
//!     --window W --pairs P --warmup K --seed S [--degree D]
//! core-lifecycle resources --arm lifecycle|reference|plain --engine E
//!     --topology T --nodes N --cycles C --churn-percent P
//!     --reuse none|fresh|same|toggle --seed S
//! core-lifecycle resources --arm lifecycle --engine E --workload W --nodes N
//!     [--degree D] --cycles 0 --seed S
//! core-lifecycle pauses --engine E --topology T --nodes N --cycles C
//!     --churn-percent P --seed S
//! ```
//!
//! The first output line is a `build` record: the linked knotrel revision,
//! its dirty state and the build variant.
//!
//! `pairs` builds both arms fresh for every pair (untimed), then times one
//! replay of the same trace on each, alternating which arm runs first
//! (even pair index: candidate first). Before any timing, one untimed replay
//! per arm must give identical result digests and identical end states
//! (counts and `connected` on 200 sampled pairs). Experiments:
//! - `ops`: `LifecycleGraph` vs the application-side `Reference`;
//! - `optin`: `LifecycleGraph` vs the plain engine on a legacy-only trace;
//! - `degree`: a star of degree D (a path among the leaves); repeated
//!   deactivate / query / reactivate of the center, about `--window`
//!   operations (rounded up to a multiple of 3);
//! - `degree-remove`: the same star; each of `--window` cycles removes the
//!   center, re-registers it and re-links it to every leaf.
//!
//! `resources` first computes the whole churn schedule and the expected
//! logical counts after every cycle with an independent model, then drops
//! the model, records a heap and RSS baseline, builds the arm and prints a
//! checkpoint after construction and after every cycle: logical counts,
//! expected counts, storage diagnostics (lifecycle arm), RSS and, in the
//! `count-alloc` build, live heap. Heap and RSS are also reported net of the
//! baseline, which holds the generated topology and the schedule.
//!
//! `resources --workload W` (knotrel#151 M6) takes a `compact` workload
//! (`sparse`, `ring`, `hub`, `star`, `hub-in-sparse`, `iso`) instead of
//! `--topology`, for the lifecycle arm with `--cycles 0` only, and adds a
//! `workload-rss` record with the RSS after the build and the gate.
//!
//! `pauses` (v0.7.0 qualification 3, check T5) replays the fresh-ID churn
//! schedule of `resources --reuse fresh` on the lifecycle arm and times every
//! lifecycle call separately with `Instant`. A call's time includes any engine
//! compaction or catalog rebuild it triggers. After each cycle, outside the
//! timing, it checks the logical counts against the independent model (any
//! difference stops the run) and prints one `cycle` record: number of calls,
//! longest call and its operation kind, summed call time and
//! `retired_vertices` (a drop marks a compaction in that cycle). The last line
//! is a `pauses_end` record with totals and two digests: of the schedule
//! (identical workload) and of the results (identical behaviour).

use knotrel_core::{EngineConfig, LifecycleGraph};
use lifecycle_probes::churn::schedule;
use lifecycle_probes::{
    Mix, Op, Plain, Reference, Rng, Subject, Topology, build_record, generate, parse_engine,
    rss_bytes, run, state, trace,
};
use serde_json::{Value, json};
use std::{collections::HashMap, process::ExitCode, time::Instant};

#[cfg(feature = "count-alloc")]
#[global_allocator]
static GLOBAL: &stats_alloc::StatsAlloc<std::alloc::System> = &stats_alloc::INSTRUMENTED_SYSTEM;

#[cfg(not(feature = "count-alloc"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

/// Fixed seed for end-state sampling, independent of `--seed`.
const SAMPLE_SEED: u64 = 0x5a3b_1e00;

fn live_heap() -> Option<i64> {
    #[cfg(feature = "count-alloc")]
    {
        let stats = GLOBAL.stats();
        Some(stats.bytes_allocated as i64 - stats.bytes_deallocated as i64)
    }
    #[cfg(not(feature = "count-alloc"))]
    {
        None
    }
}

struct Args(HashMap<String, String>);

impl Args {
    fn parse(items: impl Iterator<Item = String>) -> Result<Self, String> {
        let mut map = HashMap::new();
        let mut items = items.peekable();
        while let Some(flag) = items.next() {
            let key = flag
                .strip_prefix("--")
                .ok_or_else(|| format!("unexpected argument {flag}"))?;
            let value = items
                .next()
                .ok_or_else(|| format!("{flag} needs a value"))?;
            map.insert(key.to_owned(), value);
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
            .map_err(|_| format!("--{key} is not a valid number"))
    }
}

/// A star of degree `degree` around node 0, plus a path among the leaves.
fn star(degree: u64) -> Vec<(u64, u64)> {
    let mut edges: Vec<(u64, u64)> = (1..=degree).map(|leaf| (0, leaf)).collect();
    for leaf in 1..degree {
        edges.push((leaf, leaf + 1));
    }
    edges
}

fn timed<S: Subject>(
    engine: EngineConfig,
    n: u64,
    edges: &[(u64, u64)],
    ops: &[Op],
) -> (u128, u64) {
    let mut subject = S::build(engine, n, edges);
    let start = Instant::now();
    let digest = run(&mut subject, ops);
    let elapsed = start.elapsed().as_nanos();
    drop(subject);
    (elapsed, digest)
}

fn verified<S: Subject>(
    engine: EngineConfig,
    n: u64,
    edges: &[(u64, u64)],
    ops: &[Op],
    samples: &[(u64, u64)],
) -> (u64, u64) {
    let mut subject = S::build(engine, n, edges);
    let digest = run(&mut subject, ops);
    (digest, state(&subject, samples))
}

fn pairs<A: Subject, B: Subject>(
    args: &Args,
    engine: EngineConfig,
    n: u64,
    edges: &[(u64, u64)],
    ops: &[Op],
    labels: (&str, &str),
) -> Result<(), String> {
    let count: usize = args.num("pairs")?;
    let warmup: usize = args.num("warmup")?;
    let mut rng = Rng(SAMPLE_SEED);
    let samples: Vec<(u64, u64)> = (0..200)
        .map(|_| (rng.below(n.max(1)), rng.below(n.max(1))))
        .collect();
    let (digest_a, state_a) = verified::<A>(engine, n, edges, ops, &samples);
    let (digest_b, state_b) = verified::<B>(engine, n, edges, ops, &samples);
    let ok = digest_a == digest_b && state_a == state_b;
    println!(
        "{}",
        json!({"kind":"verify","candidate":labels.0,"reference":labels.1,
               "digest_candidate":format!("{digest_a:016x}"),"digest_reference":format!("{digest_b:016x}"),
               "state_candidate":format!("{state_a:016x}"),"state_reference":format!("{state_b:016x}"),
               "match": ok, "ops": ops.len(), "nodes": n, "edges": edges.len()})
    );
    if !ok {
        return Err("result digests or end states differ between arms".into());
    }
    for index in 0..warmup + count {
        let candidate_first = index % 2 == 0;
        let (a, b) = if candidate_first {
            let a = timed::<A>(engine, n, edges, ops);
            (a, timed::<B>(engine, n, edges, ops))
        } else {
            let b = timed::<B>(engine, n, edges, ops);
            (timed::<A>(engine, n, edges, ops), b)
        };
        if a.1 != digest_a || b.1 != digest_b {
            return Err("digest changed between replays".into());
        }
        let pair = index as i64 - warmup as i64;
        println!(
            "{}",
            json!({"kind": if pair < 0 {"warmup"} else {"pair"}, "pair": pair,
                   "candidate_first": candidate_first,
                   "candidate_ns": a.0 as u64, "reference_ns": b.0 as u64})
        );
    }
    Ok(())
}

fn pairs_command(args: &Args) -> Result<(), String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    let seed: u64 = args.num("seed")?;
    let window: usize = args.num("window")?;
    let exp = args.get("exp")?;
    let (n, edges, ops) = match exp {
        "degree" | "degree-remove" => {
            let degree: u64 = args.num("degree")?;
            let edges = star(degree);
            let mut ops = Vec::new();
            let mut rng = Rng(seed);
            if exp == "degree" {
                for _ in 0..window.div_ceil(3) {
                    ops.push(Op::SetNode(0, false));
                    ops.push(Op::Connected(1 + rng.below(degree), 1 + rng.below(degree)));
                    ops.push(Op::SetNode(0, true));
                }
            } else {
                for _ in 0..window {
                    ops.push(Op::Remove(0));
                    ops.push(Op::AddNode(0));
                    ops.extend((1..=degree).map(|leaf| Op::Link(0, leaf)));
                }
            }
            (degree + 1, edges, ops)
        }
        _ => {
            let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
            let n: u64 = args.num("nodes")?;
            let mix = Mix::parse(args.get("mix")?).ok_or("unknown --mix")?;
            let edges = generate(topology, n, seed);
            let ops = trace(n, &edges, mix, window, seed);
            (n, edges, ops)
        }
    };
    match exp {
        "ops" | "degree" | "degree-remove" => pairs::<LifecycleGraph, Reference>(
            args,
            engine,
            n,
            &edges,
            &ops,
            ("lifecycle", "app_reference"),
        ),
        "optin" => {
            if ops
                .iter()
                .any(|op| !matches!(op, Op::Link(..) | Op::Cut(..) | Op::Connected(..)))
            {
                return Err("--exp optin needs --mix legacy".into());
            }
            pairs::<LifecycleGraph, Plain>(args, engine, n, &edges, &ops, ("lifecycle", "plain"))
        }
        _ => Err("unknown --exp".into()),
    }
}

/// Churn interface for the resource experiment.
trait Churn: Subject {
    fn counts_json(&self) -> Value;
}

impl Churn for LifecycleGraph {
    fn counts_json(&self) -> Value {
        let storage = self.storage_stats();
        json!({"logical": [self.node_count(), self.edge_count(), self.active_node_count(),
                           self.enabled_edge_count(), self.effective_edge_count()],
               "engine_vertices": storage.engine_vertices,
               "retired_vertices": storage.retired_vertices,
               "catalog_node_capacity": storage.catalog_node_capacity,
               "incident_entries": storage.incident_entries,
               "incident_capacity": storage.incident_capacity})
    }
}

impl Churn for Reference {
    fn counts_json(&self) -> Value {
        let l = self.logical();
        json!({"logical": [l[0], l[1], l[2], l[3], l[4]], "engine_vertices": l[5]})
    }
}

impl Churn for Plain {
    fn counts_json(&self) -> Value {
        json!({"logical": [self.0.node_count(), self.0.edge_count()]})
    }
}

fn checkpoint<S: Churn>(
    subject: &S,
    cycle: usize,
    expected: &[usize; 5],
    baseline: (Option<i64>, Option<u64>),
) {
    let heap = live_heap();
    let rss = rss_bytes();
    println!(
        "{}",
        json!({"kind":"checkpoint","cycle":cycle,"counts":subject.counts_json(),"expected":expected,
               "rss_bytes":rss,"live_heap_bytes":heap,
               "net_heap_bytes": heap.zip(baseline.0).map(|(h, b)| h - b),
               "net_rss_bytes": rss.zip(baseline.1).map(|(r, b)| r as i64 - b as i64)})
    );
}

fn churn<S: Churn>(args: &Args, engine: EngineConfig) -> Result<(), String> {
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let cycles: usize = args.num("cycles")?;
    let percent: u64 = args.num("churn-percent")?;
    let seed: u64 = args.num("seed")?;
    let reuse = args.get("reuse")?;
    let edges = generate(topology, n, seed);
    let (plan, expected) = schedule(n, &edges, reuse, cycles, percent, seed)?;
    let baseline = (live_heap(), rss_bytes());
    println!(
        "{}",
        json!({"kind":"baseline","live_heap_bytes":baseline.0,"rss_bytes":baseline.1,
               "schedule_ops": plan.iter().map(Vec::len).sum::<usize>()})
    );
    let mut subject = S::build(engine, n, &edges);
    checkpoint(&subject, 0, &expected[0], baseline);
    for (cycle, ops) in plan.iter().enumerate() {
        for &op in ops {
            subject.apply(op);
        }
        checkpoint(&subject, cycle + 1, &expected[cycle + 1], baseline);
    }
    Ok(())
}

/// knotrel#151 M6: `resources --workload W` (a `compact` workload, lifecycle
/// arm, `--cycles 0`): builds by `add_node` over every ID in ascending order,
/// then `link` in workload order (the `Subject::build` method), and prints
/// the baseline and the construction checkpoint with RSS.
fn workload_resources(args: &Args, engine: EngineConfig) -> Result<(), String> {
    use lifecycle_probes::compact::{self, Workload};
    if args.get("arm")? != "lifecycle" || args.num::<usize>("cycles")? != 0 {
        return Err("--workload supports only --arm lifecycle --cycles 0".into());
    }
    let nodes = args.0.get("nodes").map_or(Ok(0), |_| args.num("nodes"))?;
    let degree = args.0.get("degree").map_or(Ok(0), |_| args.num("degree"))?;
    let w = Workload::generate(args.get("workload")?, nodes, degree, args.num("seed")?)?;
    let baseline = (live_heap(), rss_bytes());
    println!(
        "{}",
        json!({"kind":"baseline","live_heap_bytes":baseline.0,"rss_bytes":baseline.1,"schedule_ops":0})
    );
    let mut graph = LifecycleGraph::new(engine).map_err(|e| e.to_string())?;
    for &v in &w.ids {
        graph.add_node(v).map_err(|e| e.to_string())?;
    }
    for &(a, b) in &w.edges {
        graph.link(a, b).map_err(|e| e.to_string())?;
    }
    compact::check_logical(&graph, w.expected(), "build")?;
    let expected = w.expected();
    checkpoint(&graph, 0, &expected, baseline);
    let rss = rss_bytes();
    println!(
        "{}",
        json!({"kind":"workload-rss","engine":engine.as_str(),"workload":w.label,
               "rss_after_build":rss,"net_rss_bytes":rss.zip(baseline.1).map(|(r, b)| r as i64 - b as i64),
               "gate":compact::gate(&w, &graph)})
    );
    Ok(())
}

fn resources_command(args: &Args) -> Result<(), String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    if args.0.contains_key("workload") {
        return workload_resources(args, engine);
    }
    match args.get("arm")? {
        "lifecycle" => churn::<LifecycleGraph>(args, engine),
        "reference" => churn::<Reference>(args, engine),
        "plain" => {
            if args.get("reuse")? != "none" || args.num::<usize>("cycles")? != 0 {
                return Err("the plain arm supports only --reuse none --cycles 0".into());
            }
            churn::<Plain>(args, engine)
        }
        _ => Err("unknown --arm".into()),
    }
}

/// FNV-1a step over one 64-bit word.
fn fnv(digest: u64, word: u64) -> u64 {
    (digest ^ word).wrapping_mul(0x0100_0000_01b3)
}

/// Order-sensitive digest of one operation (kind and arguments).
fn op_digest(digest: u64, op: Op) -> u64 {
    match op {
        Op::AddNode(v) => fnv(fnv(digest, 1), v),
        Op::Link(a, b) => fnv(fnv(fnv(digest, 2), a), b),
        Op::Cut(a, b) => fnv(fnv(fnv(digest, 3), a), b),
        Op::Connected(a, b) => fnv(fnv(fnv(digest, 4), a), b),
        Op::SetNode(v, on) => fnv(fnv(fnv(digest, 5), v), u64::from(on)),
        Op::SetEdge(a, b, on) => fnv(fnv(fnv(fnv(digest, 6), a), b), u64::from(on)),
        Op::Remove(v) => fnv(fnv(digest, 7), v),
    }
}

fn op_kind(op: Op) -> &'static str {
    match op {
        Op::AddNode(_) => "add_node",
        Op::Link(..) => "link",
        Op::Cut(..) => "cut",
        Op::Connected(..) => "connected",
        Op::SetNode(..) => "set_node_active",
        Op::SetEdge(..) => "set_edge_enabled",
        Op::Remove(_) => "remove_node",
    }
}

fn logical(graph: &LifecycleGraph) -> [usize; 5] {
    [
        graph.node_count(),
        graph.edge_count(),
        graph.active_node_count(),
        graph.enabled_edge_count(),
        graph.effective_edge_count(),
    ]
}

fn pauses_command(args: &Args) -> Result<(), String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let cycles: usize = args.num("cycles")?;
    let percent: u64 = args.num("churn-percent")?;
    let seed: u64 = args.num("seed")?;
    let edges = generate(topology, n, seed);
    let (plan, expected) = schedule(n, &edges, "fresh", cycles, percent, seed)?;
    let schedule_digest = plan
        .iter()
        .flatten()
        .fold(0xcbf2_9ce4_8422_2325_u64, |d, &op| op_digest(d, op));
    let mut graph = <LifecycleGraph as Subject>::build(engine, n, &edges);
    if logical(&graph) != expected[0] {
        return Err("construction: logical counts differ from the model".into());
    }
    let storage = graph.storage_stats();
    println!(
        "{}",
        json!({"kind":"pauses_start","engine":args.get("engine")?,
               "topology":args.get("topology")?,"nodes":n,"edges":edges.len(),"cycles":cycles,
               "churn_percent":percent,"seed":seed,"reuse":"fresh",
               "schedule_ops": plan.iter().map(Vec::len).sum::<usize>(),
               "schedule_digest":format!("{schedule_digest:016x}"),
               "retired_vertices":storage.retired_vertices,
               "catalog_node_capacity":storage.catalog_node_capacity})
    );
    let mut result_digest = 0xcbf2_9ce4_8422_2325_u64;
    let (mut calls, mut timed_ns, mut longest) = (0_u64, 0_u128, 0_u128);
    let wall = Instant::now();
    for (cycle, ops) in plan.iter().enumerate() {
        let (mut max_ns, mut max_kind, mut sum_ns) = (0_u128, "", 0_u128);
        for &op in ops {
            let start = Instant::now();
            let result = graph.apply(op);
            let elapsed = start.elapsed().as_nanos();
            result_digest = fnv(result_digest, result);
            sum_ns += elapsed;
            if elapsed > max_ns {
                max_ns = elapsed;
                max_kind = op_kind(op);
            }
        }
        if logical(&graph) != expected[cycle + 1] {
            return Err(format!(
                "cycle {}: logical counts differ from the model",
                cycle + 1
            ));
        }
        calls += ops.len() as u64;
        timed_ns += sum_ns;
        longest = longest.max(max_ns);
        let storage = graph.storage_stats();
        println!(
            "{}",
            json!({"kind":"cycle","cycle":cycle + 1,"calls":ops.len(),"max_ns":max_ns as u64,
                   "max_op":max_kind,"sum_ns":sum_ns as u64,
                   "retired_vertices":storage.retired_vertices,
                   "engine_vertices":storage.engine_vertices,
                   "catalog_node_capacity":storage.catalog_node_capacity})
        );
    }
    println!(
        "{}",
        json!({"kind":"pauses_end","cycles":cycles,"calls":calls,"timed_ns":timed_ns as u64,
               "max_ns":longest as u64,"wall_ns":wall.elapsed().as_nanos() as u64,
               "schedule_digest":format!("{schedule_digest:016x}"),
               "result_digest":format!("{result_digest:016x}"),
               "final_logical":logical(&graph)})
    );
    Ok(())
}

fn main() -> ExitCode {
    let mut items = std::env::args().skip(1);
    let command = items.next().unwrap_or_default();
    println!("{}", build_record("core-lifecycle"));
    let result = Args::parse(items).and_then(|args| match command.as_str() {
        "pairs" => pairs_command(&args),
        "resources" => resources_command(&args),
        "pauses" => pauses_command(&args),
        _ => Err("usage: core-lifecycle pairs|resources|pauses --flag value ...".into()),
    });
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn op_digest_depends_on_kind_arguments_and_order() {
        let base = 0xcbf2_9ce4_8422_2325_u64;
        let ab = op_digest(op_digest(base, Op::AddNode(1)), Op::Remove(2));
        let ba = op_digest(op_digest(base, Op::Remove(2)), Op::AddNode(1));
        assert_ne!(ab, ba);
        assert_ne!(
            op_digest(base, Op::AddNode(1)),
            op_digest(base, Op::Remove(1))
        );
        assert_ne!(
            op_digest(base, Op::Link(1, 2)),
            op_digest(base, Op::Link(2, 1))
        );
        assert_ne!(
            op_digest(base, Op::SetNode(1, true)),
            op_digest(base, Op::SetNode(1, false))
        );
    }
}
