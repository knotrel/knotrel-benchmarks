//! Core lifecycle probe: paired timing and sustained resources.
//!
//! ```text
//! core-lifecycle pairs --exp ops|optin|degree --engine E --topology T
//!     --nodes N --mix query|mutation|legacy --window W --pairs P
//!     --warmup K --seed S [--degree D]
//! core-lifecycle resources --arm lifecycle|reference|plain --engine E
//!     --topology T --nodes N --cycles C --churn-percent P
//!     --reuse fresh|same|toggle --seed S
//! ```
//!
//! `pairs` builds both arms fresh for every pair (untimed), then times one
//! replay of the same trace on each, alternating which arm runs first
//! (pair index even: candidate first). One untimed verification replay per
//! arm must give identical result digests before any timing. Experiments:
//! `ops` compares `LifecycleGraph` with the application-side `Reference` on
//! lifecycle mixes; `optin` compares `LifecycleGraph` with the plain engine
//! on a legacy-only trace; `degree` alternately deactivates and reactivates
//! the center of a star of degree D (with a ring among the leaves).
//!
//! `resources` prints one checkpoint after construction and one after each
//! churn cycle: logical counts, engine vertices (lifecycle arm), RSS and,
//! in the `count-alloc` build, live heap bytes.
//!
//! Output: one JSON object per line on stdout.

use knotrel_core::{EngineConfig, LifecycleGraph};
use lifecycle_probes::{
    Mix, Op, Plain, Reference, Rng, Subject, Topology, generate, parse_engine, rss_bytes, run,
    trace,
};
use serde_json::json;
use std::{collections::HashMap, process::ExitCode, time::Instant};

#[cfg(feature = "count-alloc")]
#[global_allocator]
static GLOBAL: &stats_alloc::StatsAlloc<std::alloc::System> = &stats_alloc::INSTRUMENTED_SYSTEM;

#[cfg(not(feature = "count-alloc"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

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
    let (_, digest_a) = timed::<A>(engine, n, edges, ops);
    let (_, digest_b) = timed::<B>(engine, n, edges, ops);
    println!(
        "{}",
        json!({"kind":"verify","candidate":labels.0,"reference":labels.1,
               "digest_candidate":format!("{digest_a:016x}"),"digest_reference":format!("{digest_b:016x}"),
               "match": digest_a == digest_b, "ops": ops.len(), "nodes": n, "edges": edges.len()})
    );
    if digest_a != digest_b {
        return Err("result digests differ between arms".into());
    }
    for index in 0..warmup + count {
        let candidate_first = index % 2 == 0;
        let (first, second) = if candidate_first {
            let a = timed::<A>(engine, n, edges, ops);
            let b = timed::<B>(engine, n, edges, ops);
            (a, b)
        } else {
            let b = timed::<B>(engine, n, edges, ops);
            let a = timed::<A>(engine, n, edges, ops);
            (a, b)
        };
        if first.1 != digest_a || second.1 != digest_b {
            return Err("digest changed between replays".into());
        }
        let pair = index as i64 - warmup as i64;
        println!(
            "{}",
            json!({"kind": if pair < 0 {"warmup"} else {"pair"}, "pair": pair,
                   "candidate_first": candidate_first,
                   "candidate_ns": first.0 as u64, "reference_ns": second.0 as u64})
        );
    }
    Ok(())
}

fn pairs_command(args: &Args) -> Result<(), String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
    let seed: u64 = args.num("seed")?;
    let window: usize = args.num("window")?;
    let exp = args.get("exp")?;
    let (n, edges, ops) = if exp == "degree" {
        let degree: u64 = args.num("degree")?;
        let edges = star(degree);
        let mut ops = Vec::with_capacity(window);
        let mut rng = Rng(seed);
        while ops.len() < window {
            ops.push(Op::SetNode(0, false));
            ops.push(Op::Connected(1 + rng.below(degree), 1 + rng.below(degree)));
            ops.push(Op::SetNode(0, true));
        }
        (degree + 1, edges, ops)
    } else {
        let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
        let n: u64 = args.num("nodes")?;
        let mix = Mix::parse(args.get("mix")?).ok_or("unknown --mix")?;
        let edges = generate(topology, n, seed);
        let ops = trace(n, &edges, mix, window, seed);
        (n, edges, ops)
    };
    match exp {
        "ops" | "degree" => pairs::<LifecycleGraph, Reference>(
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

/// Uniform churn interface for the resource experiment.
trait Churn: Subject {
    fn counts(&self) -> serde_json::Value;
}

impl Churn for LifecycleGraph {
    fn counts(&self) -> serde_json::Value {
        json!({"nodes": self.node_count(), "edges": self.edge_count(),
               "active_nodes": self.active_node_count(), "enabled_edges": self.enabled_edge_count(),
               "effective_edges": self.effective_edge_count(), "engine_vertices": self.engine_vertex_count()})
    }
}

impl Churn for Reference {
    fn counts(&self) -> serde_json::Value {
        json!({})
    }
}

impl Churn for Plain {
    fn counts(&self) -> serde_json::Value {
        json!({"nodes": self.0.node_count(), "edges": self.0.edge_count()})
    }
}

fn checkpoint<S: Churn>(subject: &S, cycle: usize) {
    println!(
        "{}",
        json!({"kind":"checkpoint","cycle":cycle,"counts":subject.counts(),
               "rss_bytes":rss_bytes(),"live_heap_bytes":live_heap()})
    );
}

/// Churn: each cycle picks `churn%` of the live IDs. `fresh` removes each and
/// registers a new, never-used ID with `relink` random edges; `same` removes
/// and re-registers the same ID with `relink` edges; `toggle` deactivates
/// them, disables one random incident pair, then reactivates and re-enables.
fn churn<S: Churn>(args: &Args, engine: EngineConfig) -> Result<(), String> {
    let topology = Topology::parse(args.get("topology")?).ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let cycles: usize = args.num("cycles")?;
    let percent: u64 = args.num("churn-percent")?;
    let seed: u64 = args.num("seed")?;
    let reuse = args.get("reuse")?.to_owned();
    let edges = generate(topology, n, seed);
    // Re-link count keeps the registered edge count roughly steady.
    let relink = (2 * edges.len() as u64 / n.max(1)).max(1);
    let mut subject = S::build(engine, n, &edges);
    checkpoint(&subject, 0);
    let mut rng = Rng(seed ^ 0xc0ffee);
    let mut live: Vec<u64> = (0..n).collect();
    let mut next_id = n;
    for cycle in 1..=cycles {
        let picks = (live.len() as u64 * percent / 100).max(1);
        for _ in 0..picks {
            let index = rng.below(live.len() as u64) as usize;
            let v = live[index];
            match reuse.as_str() {
                "fresh" | "same" => {
                    subject.apply(Op::Remove(v));
                    let id = if reuse == "fresh" {
                        next_id += 1;
                        next_id
                    } else {
                        v
                    };
                    live[index] = id;
                    subject.apply(Op::AddNode(id));
                    for _ in 0..relink {
                        let w = live[rng.below(live.len() as u64) as usize];
                        subject.apply(Op::Link(id, w));
                    }
                }
                "toggle" => {
                    let w = live[rng.below(live.len() as u64) as usize];
                    subject.apply(Op::SetNode(v, false));
                    subject.apply(Op::SetEdge(v, w, false));
                    subject.apply(Op::SetNode(v, true));
                    subject.apply(Op::SetEdge(v, w, true));
                }
                _ => return Err("unknown --reuse".into()),
            }
        }
        checkpoint(&subject, cycle);
    }
    Ok(())
}

fn resources_command(args: &Args) -> Result<(), String> {
    let engine = parse_engine(args.get("engine")?).ok_or("unknown --engine")?;
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

fn main() -> ExitCode {
    let mut items = std::env::args().skip(1);
    let command = items.next().unwrap_or_default();
    let result = Args::parse(items).and_then(|args| match command.as_str() {
        "pairs" => pairs_command(&args),
        "resources" => resources_command(&args),
        _ => Err("usage: core-lifecycle pairs|resources --flag value ...".into()),
    });
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
