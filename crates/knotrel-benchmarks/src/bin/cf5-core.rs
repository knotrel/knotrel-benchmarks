//! CF5 core cells K2, K2x and K3 (knotrel `docs/releases/v1.1.0-cf5-qualification-plan.md`).
//!
//! Every engine runs through `ConnectivityGraph`, the product API, so the four
//! engines share one code path and differ only by `EngineConfig`.
//!
//! ```text
//! cf5-core staged    --engine E --vertices V --degree D --seed S   (K2)
//! cf5-core all       --engine E --vertices V --degree D --seed S   (K2x)
//! cf5-core construct --engine E --vertices V --degree D --seed S   (K3, random graph)
//! cf5-core construct --engine E --family F --vertices V --seed S   (K3, K1 family initial graph)
//! ```
//!
//! `E` is a `connectivity-*` key; `D` is the average degree (`E = D·V/2`
//! edges). `--verify true` adds an untimed whole-partition check (the CF5
//! tier-1 correctness smoke); timed campaign observations do not use it.
//! Every `link` and `cut` must report a change (all edges are new on insertion
//! and present on deletion). Output: one JSON object on stdout. Every timed mode checks its
//! answers against an independent union-find oracle computed outside the
//! timed regions and exits non-zero on any disagreement (the CF5 correctness
//! gate). K4 (memory) lives in `tools/lifecycle-probes` (`memory-peak
//! cf5-random`), whose counting allocator this workspace's lints forbid.

use knotrel_benchmarks::cf5::{ALL_SALT, Rng, STAGED_SALT, fingerprint, orders, random_graph};
use knotrel_benchmarks::engines::EngineKind;
use knotrel_benchmarks::{Config, WorkloadKind, generate_with_query_percent};
use knotrel_core::{ConnectivityGraph, EngineConfig, GraphLimits};
use serde_json::{Value, json};
use std::{collections::HashMap, hint::black_box, process::ExitCode, time::Instant};

/// Union-find oracle over vertices `0..n`.
struct UnionFind(Vec<u32>);

impl UnionFind {
    fn new(n: usize) -> Self {
        Self((0..n as u32).collect())
    }
    fn find(&mut self, mut x: u32) -> u32 {
        while self.0[x as usize] != x {
            let parent = self.0[x as usize];
            self.0[x as usize] = self.0[parent as usize];
            x = parent;
        }
        x
    }
    fn union(&mut self, a: u32, b: u32) {
        let (a, b) = (self.find(a), self.find(b));
        if a != b {
            self.0[a as usize] = b;
        }
    }
    fn from_edges(n: usize, edges: &[(u64, u64)]) -> Self {
        let mut uf = Self::new(n);
        for &(a, b) in edges {
            uf.union(a as u32, b as u32);
        }
        uf
    }
}

fn engine(key: &str) -> Result<(EngineKind, EngineConfig), String> {
    let kind = EngineKind::parse(key).map_err(|e| format!("{e}: {key}"))?;
    let config = kind
        .connectivity_engine()
        .ok_or_else(|| format!("{key} is not a connectivity-* engine"))?;
    Ok((kind, config))
}

fn empty_graph(config: EngineConfig, vertices: u64) -> ConnectivityGraph {
    let mut graph = ConnectivityGraph::new(config);
    for node in 0..vertices {
        graph.add_node(node).expect("unlimited graph");
    }
    graph
}

/// `count` queries after a stage: half random pairs, half endpoints of
/// `present` edges, each with its oracle answer.
fn queries(
    rng: &mut Rng,
    vertices: u64,
    present: &[(u64, u64)],
    oracle: &mut UnionFind,
    count: usize,
) -> Vec<(u64, u64, bool)> {
    (0..count)
        .map(|i| {
            let (a, b) = if i % 2 == 0 || present.is_empty() {
                (rng.below(vertices), rng.below(vertices))
            } else {
                present[rng.below(present.len() as u64) as usize]
            };
            let expected = oracle.find(a as u32) == oracle.find(b as u32);
            (a, b, expected)
        })
        .collect()
}

/// Runs `batch` queries, timed, and checks every answer.
fn timed_queries(graph: &ConnectivityGraph, batch: &[(u64, u64, bool)]) -> Result<u128, String> {
    let start = Instant::now();
    let mut answers = Vec::with_capacity(batch.len());
    for &(a, b, _) in batch {
        answers.push(black_box(graph.connected(a, b).map_err(|e| e.to_string())?));
    }
    let elapsed = start.elapsed().as_nanos();
    for (&(a, b, expected), &answer) in batch.iter().zip(&answers) {
        if answer != expected {
            return Err(format!(
                "wrong answer: connected({a}, {b}) = {answer}, expected {expected}"
            ));
        }
    }
    Ok(elapsed)
}

/// `--verify` (the CF5 tier-1 correctness smoke, never in timed observations):
/// a check of the whole partition that also catches false "connected"
/// answers, which the protocol's queries rarely probe. For up to 2 000 random
/// vertices, `connected(v, representative(v))` must be true; for up to 2 000
/// pairs of distinct oracle components, `connected` between their
/// representatives must be false. Untimed.
fn verify_partition(
    graph: &ConnectivityGraph,
    vertices: u64,
    oracle: &mut UnionFind,
    rng: &mut Rng,
) -> Result<(), String> {
    let mut representative: HashMap<u32, u64> = HashMap::new();
    for v in 0..vertices {
        representative.entry(oracle.find(v as u32)).or_insert(v);
    }
    for _ in 0..2_000 {
        let v = rng.below(vertices);
        let r = representative[&oracle.find(v as u32)];
        if !graph.connected(v, r).map_err(|e| e.to_string())? {
            return Err(format!("verify: {v} and {r} must be connected"));
        }
    }
    let mut roots: Vec<u64> = representative.values().copied().collect();
    roots.sort_unstable();
    if roots.len() > 1 {
        for _ in 0..2_000 {
            let i = rng.below(roots.len() as u64) as usize;
            let j = rng.below(roots.len() as u64) as usize;
            if i != j
                && graph
                    .connected(roots[i], roots[j])
                    .map_err(|e| e.to_string())?
            {
                return Err(format!(
                    "verify: {} and {} must not be connected",
                    roots[i], roots[j]
                ));
            }
        }
    }
    Ok(())
}

/// K2: the staged protocol of De Man et al. §8.2.
fn staged(
    config: EngineConfig,
    vertices: u64,
    edges: &[(u64, u64)],
    seed: u64,
    verify: bool,
) -> Result<Value, String> {
    const STAGES: usize = 10;
    const QUERIES: usize = 1_000;
    let (mut rng, insert_order, delete_order) = orders(edges, seed, STAGED_SALT);
    let mut graph = empty_graph(config, vertices);
    let n = vertices as usize;
    let mut oracle = UnionFind::new(n);
    let (mut update_ns, mut query_ns) = (0u128, 0u128);
    let mut changed = true;
    let bounds: Vec<usize> = (0..=STAGES).map(|i| i * edges.len() / STAGES).collect();
    let mut present: Vec<(u64, u64)> = Vec::with_capacity(edges.len());
    for stage in 0..STAGES {
        let chunk = &insert_order[bounds[stage]..bounds[stage + 1]];
        let start = Instant::now();
        for &(a, b) in chunk {
            changed &= black_box(graph.link(a, b).map_err(|e| e.to_string())?);
        }
        update_ns += start.elapsed().as_nanos();
        for &(a, b) in chunk {
            oracle.union(a as u32, b as u32);
        }
        present.extend_from_slice(chunk);
        let batch = queries(&mut rng, vertices, &present, &mut oracle, QUERIES);
        query_ns += timed_queries(&graph, &batch)?;
        if verify {
            verify_partition(&graph, vertices, &mut oracle, &mut rng)?;
        }
    }
    for stage in 0..STAGES {
        let chunk = &delete_order[bounds[stage]..bounds[stage + 1]];
        let start = Instant::now();
        for &(a, b) in chunk {
            changed &= black_box(graph.cut(a, b).map_err(|e| e.to_string())?);
        }
        update_ns += start.elapsed().as_nanos();
        // The edges left are exactly the rest of the deletion order: deterministic.
        let left = &delete_order[bounds[stage + 1]..];
        let mut oracle = UnionFind::from_edges(n, left);
        let batch = queries(&mut rng, vertices, left, &mut oracle, QUERIES);
        query_ns += timed_queries(&graph, &batch)?;
        if verify {
            verify_partition(&graph, vertices, &mut oracle, &mut rng)?;
        }
    }
    if !changed {
        return Err("a link or cut of a new or present edge reported no change".into());
    }
    if graph.edge_count() != 0 {
        return Err("edges left after delete-all".into());
    }
    Ok(json!({"update_ns": update_ns, "query_ns": query_ns,
              "stages": STAGES, "queries_per_stage": QUERIES}))
}

/// K2x: insert all edges, then delete all, unstaged and without queries.
fn insert_delete_all(
    config: EngineConfig,
    vertices: u64,
    edges: &[(u64, u64)],
    seed: u64,
    verify: bool,
) -> Result<Value, String> {
    let mut changed = true;
    let (mut rng, insert_order, delete_order) = orders(edges, seed, ALL_SALT);
    let mut graph = empty_graph(config, vertices);
    let start = Instant::now();
    for &(a, b) in &insert_order {
        changed &= black_box(graph.link(a, b).map_err(|e| e.to_string())?);
    }
    let insert_ns = start.elapsed().as_nanos();
    // Oracle check after insertion, outside the timed regions.
    let mut oracle = UnionFind::from_edges(vertices as usize, edges);
    let batch = queries(&mut rng, vertices, edges, &mut oracle, 1_000);
    timed_queries(&graph, &batch)?;
    if verify {
        verify_partition(&graph, vertices, &mut oracle, &mut rng)?;
    }
    let start = Instant::now();
    for &(a, b) in &delete_order {
        changed &= black_box(graph.cut(a, b).map_err(|e| e.to_string())?);
    }
    let delete_ns = start.elapsed().as_nanos();
    if !changed {
        return Err("a link or cut of a new or present edge reported no change".into());
    }
    for &(a, b) in edges.iter().take(1_000) {
        if graph.connected(a, b).map_err(|e| e.to_string())? {
            return Err(format!("({a}, {b}) still connected after delete-all"));
        }
    }
    if verify {
        let mut empty = UnionFind::new(vertices as usize);
        verify_partition(&graph, vertices, &mut empty, &mut rng)?;
    }
    Ok(json!({"insert_ns": insert_ns, "delete_ns": delete_ns}))
}

/// K3: `try_from_edges` of a complete graph.
fn construct(
    config: EngineConfig,
    vertices: u64,
    edges: &[(u64, u64)],
    seed: u64,
    verify: bool,
) -> Result<Value, String> {
    let nodes: Vec<u64> = (0..vertices).collect();
    let start = Instant::now();
    let graph = ConnectivityGraph::try_from_edges(config, GraphLimits::default(), &nodes, edges)
        .map_err(|e| e.to_string())?;
    let construct_ns = start.elapsed().as_nanos();
    let mut rng = Rng(seed ^ 0xC0);
    let mut oracle = UnionFind::from_edges(vertices as usize, edges);
    let batch = queries(&mut rng, vertices, edges, &mut oracle, 1_000);
    timed_queries(&graph, &batch)?;
    if verify {
        verify_partition(&graph, vertices, &mut oracle, &mut rng)?;
    }
    Ok(json!({"construct_ns": construct_ns}))
}

fn run(args: &[String]) -> Result<Value, String> {
    let mode = args.first().ok_or("missing mode")?.as_str();
    let mut flags: HashMap<String, String> = HashMap::new();
    let mut items = args[1..].iter();
    while let Some(flag) = items.next() {
        let key = flag
            .strip_prefix("--")
            .ok_or_else(|| format!("unexpected {flag}"))?;
        flags.insert(
            key.to_owned(),
            items.next().ok_or("flag without value")?.clone(),
        );
    }
    let get = |key: &str| flags.get(key).ok_or_else(|| format!("--{key} is required"));
    let number = |key: &str| -> Result<u64, String> {
        get(key)?
            .parse()
            .map_err(|_| format!("--{key} must be a number"))
    };
    let (kind, config) = engine(get("engine")?)?;
    let verify = match flags.get("verify").map(String::as_str) {
        None | Some("false") => false,
        Some("true") => true,
        Some(_) => return Err("--verify must be true or false".into()),
    };
    let vertices = number("vertices")?;
    let seed = number("seed")?;
    let (edges, family) = match flags.get("family") {
        Some(name) => {
            let kind = WorkloadKind::parse(name).map_err(|e| e.to_string())?;
            let workload = generate_with_query_percent(
                kind,
                Config {
                    nodes: vertices,
                    rounds: 1,
                    seed,
                },
                50,
            )
            .map_err(|e| e.to_string())?;
            (workload.initial_edges, Some(name.clone()))
        }
        None => (random_graph(vertices, number("degree")?, seed)?, None),
    };
    let result = match mode {
        "staged" => staged(config, vertices, &edges, seed, verify)?,
        "all" => insert_delete_all(config, vertices, &edges, seed, verify)?,
        "construct" => construct(config, vertices, &edges, seed, verify)?,
        other => return Err(format!("unknown mode {other}")),
    };
    Ok(json!({
        "schema": "cf5-core-1",
        "mode": mode,
        "engine": kind.key(),
        "engine_identity": kind.name(),
        "vertices": vertices,
        "edges": edges.len(),
        "degree": flags.get("degree").and_then(|d| d.parse::<u64>().ok()),
        "edges_fingerprint": fingerprint(&edges),
        "family": family,
        "seed": seed,
        "verified": verify,
        "debug_assertions": cfg!(debug_assertions),
        "result": result,
    }))
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(report) => {
            println!("{report}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("cf5-core: {error}");
            ExitCode::FAILURE
        }
    }
}
