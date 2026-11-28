//! `query-shape-probe`: per-query latency, allocations and reused scratch of
//! `knotrel_core::Graph::connected` (v1.2.0 qualification, attempt 3: plan
//! section 14.5, K3, and section 14.7, M1).
//!
//! One process is one observation. Stdout carries exactly one JSON object;
//! diagnostics go to stderr. Exit 0 on success, 2 when any answer is wrong
//! (the JSON is still printed, with `wrong_answers > 0`), 1 on usage or setup
//! errors.
//!
//! ```text
//! query-shape-probe shape --shape s1|s2|l1|l2|l3 --threads N
//!     [--vertices 100000] [--seed 42] [--queries Q]
//! query-shape-probe sequence --kind large-then-small --threads T
//!     [--chain-vertices 1000000] [--vertices 100000] [--small-queries 10000] [--seed 42]
//! ```
//!
//! # Measurement boundaries
//!
//! - Graph build, union-find answers, query generation and the fingerprint
//!   are untimed and happen before the threads start.
//! - `shape`: every thread runs `max(1, Q/100)` untimed warmup queries, then
//!   `Q` timed queries, each timed alone with `Instant` around one
//!   `connected` call. Allocations are counted on the thread itself, between
//!   the first and the last timed query; the latency buffer is allocated
//!   before that window.
//! - `sequence`: every thread reads its own net live-heap counter after the
//!   start barrier (its latency buffer is already allocated), runs one query
//!   across the chain's ends, reads again, runs the short queries, reads
//!   again. The deltas are what `connected` left allocated on that thread:
//!   its reused thread-local scratch.
//!
//! The counting allocator keeps per-thread counters only (no shared atomics
//! on the allocation path), as in the prototype bench.

use knotrel_core::Graph;
use query_shape_probe::{Fnv1a64, Instance, JsonObject, Query, Shape, nearest_rank};
use std::process::ExitCode;
use std::sync::Barrier;
use std::time::Instant;

#[allow(unsafe_code)]
mod counting {
    //! Global allocator with thread-local counters.
    use std::alloc::{GlobalAlloc, Layout, System};
    use std::cell::Cell;

    thread_local! {
        static ALLOCS: Cell<u64> = const { Cell::new(0) };
        static BYTES: Cell<u64> = const { Cell::new(0) };
        static NET: Cell<i64> = const { Cell::new(0) };
    }

    /// Counts allocations (alloc + realloc), allocated bytes and the net live
    /// bytes of the calling thread.
    pub struct Counting;

    // SAFETY: every method forwards to `System` with the caller's arguments;
    // the counters are const-initialized `Cell`s without destructors, so
    // `try_with` never allocates or recurses.
    unsafe impl GlobalAlloc for Counting {
        unsafe fn alloc(&self, l: Layout) -> *mut u8 {
            let _ = ALLOCS.try_with(|c| c.set(c.get() + 1));
            let _ = BYTES.try_with(|c| c.set(c.get() + l.size() as u64));
            let _ = NET.try_with(|c| c.set(c.get() + l.size() as i64));
            unsafe { System.alloc(l) }
        }
        unsafe fn alloc_zeroed(&self, l: Layout) -> *mut u8 {
            let _ = ALLOCS.try_with(|c| c.set(c.get() + 1));
            let _ = BYTES.try_with(|c| c.set(c.get() + l.size() as u64));
            let _ = NET.try_with(|c| c.set(c.get() + l.size() as i64));
            unsafe { System.alloc_zeroed(l) }
        }
        unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
            let _ = NET.try_with(|c| c.set(c.get() - l.size() as i64));
            unsafe { System.dealloc(p, l) }
        }
        unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
            let _ = ALLOCS.try_with(|c| c.set(c.get() + 1));
            let _ = BYTES.try_with(|c| c.set(c.get() + n as u64));
            let _ = NET.try_with(|c| c.set(c.get() + n as i64 - l.size() as i64));
            unsafe { System.realloc(p, l, n) }
        }
    }

    /// Allocation count of the calling thread.
    pub fn allocs() -> u64 {
        ALLOCS.with(Cell::get)
    }

    /// Allocated bytes of the calling thread.
    pub fn bytes() -> u64 {
        BYTES.with(Cell::get)
    }

    /// Net live bytes allocated minus freed by the calling thread.
    pub fn net() -> i64 {
        NET.with(Cell::get)
    }
}

#[global_allocator]
static ALLOC: counting::Counting = counting::Counting;

thread_local! {
    /// A thread-local with a destructor, touched before the first counter
    /// reading. std keeps a per-thread list of TLS destructors that allocates
    /// on its first registration; touching this first means a destructor that
    /// knotrel's scratch registers later does not show up as retained bytes.
    static DTOR_WARM: std::cell::RefCell<Vec<u8>> = const { std::cell::RefCell::new(Vec::new()) };
}

fn warm_tls_destructors() {
    DTOR_WARM.with(|v| std::hint::black_box(v.borrow().len()));
}

const DEFAULT_VERTICES: u64 = 100_000;
const DEFAULT_CHAIN_VERTICES: u64 = 1_000_000;
const DEFAULT_SMALL_QUERIES: usize = 10_000;
const DEFAULT_SEED: u64 = 42;
/// M1 counts allocations of the short queries after the first this many.
const ALLOC_GRACE: usize = 100;

/// Test hook, debug builds only (release builds ignore it): with
/// `QSP_TEST_CORRUPT_EXPECTED=1`, the last query of stream 0 expects the
/// wrong answer, so the tests can check the wrong-answer gate (exit 2).
fn corrupt_for_test(streams: &mut [Vec<Query>]) {
    if cfg!(debug_assertions)
        && std::env::var_os("QSP_TEST_CORRUPT_EXPECTED").is_some_and(|v| v == "1")
        && let Some(q) = streams.first_mut().and_then(|s| s.last_mut())
    {
        q.expected = !q.expected;
    }
}

fn usage() -> &'static str {
    "usage:\n  query-shape-probe shape --shape s1|s2|l1|l2|l3 --threads N [--vertices 100000] [--seed 42] [--queries Q]\n  query-shape-probe sequence --kind large-then-small --threads T [--chain-vertices 1000000] [--vertices 100000] [--small-queries 10000] [--seed 42]"
}

struct Args {
    pairs: Vec<(String, String)>,
}

impl Args {
    fn parse(rest: &[String], allowed: &[&str]) -> Result<Self, String> {
        let mut pairs = Vec::new();
        let mut it = rest.iter();
        while let Some(k) = it.next() {
            let key = k
                .strip_prefix("--")
                .ok_or_else(|| format!("unexpected argument {k:?}"))?;
            if !allowed.contains(&key) {
                return Err(format!("unknown option --{key}"));
            }
            let v = it.next().ok_or_else(|| format!("--{key} needs a value"))?;
            if pairs.iter().any(|(k, _): &(String, String)| k == key) {
                return Err(format!("--{key} given twice"));
            }
            pairs.push((key.to_string(), v.clone()));
        }
        Ok(Self { pairs })
    }

    fn get(&self, key: &str) -> Option<&str> {
        self.pairs
            .iter()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v.as_str())
    }

    fn num<T: std::str::FromStr>(&self, key: &str, default: Option<T>) -> Result<T, String> {
        match self.get(key) {
            Some(v) => v
                .replace('_', "")
                .parse()
                .map_err(|_| format!("--{key}: not a number: {v:?}")),
            None => default.ok_or_else(|| format!("--{key} is required")),
        }
    }
}

fn build_graph(vertices: u64, edges: &[(u64, u64)]) -> Result<(Graph, u64), String> {
    let mut g = Graph::new();
    for v in 0..vertices {
        g.add_node(v);
    }
    let mut added = 0u64;
    for &(a, b) in edges {
        match g.link(a, b) {
            Ok(true) => added += 1,
            Ok(false) => {}
            Err(e) => return Err(format!("link({a}, {b}) failed: {e:?}")),
        }
    }
    Ok((g, added))
}

/// Runs one query and reports whether the answer matched.
#[inline(always)]
fn check(g: &Graph, q: &Query) -> bool {
    match g.connected(q.a, q.b) {
        Ok(ans) => std::hint::black_box(ans) == q.expected,
        Err(_) => false,
    }
}

fn latency_obj(sorted: &[u64]) -> JsonObject {
    if sorted.is_empty() {
        return JsonObject::new()
            .raw("p50", "null")
            .raw("p99", "null")
            .raw("max", "null");
    }
    JsonObject::new()
        .num("p50", nearest_rank(sorted, 50, 100))
        .num("p99", nearest_rank(sorted, 99, 100))
        .num("max", sorted[sorted.len() - 1])
        .float(
            "mean",
            sorted.iter().map(|&x| x as f64).sum::<f64>() / sorted.len() as f64,
        )
}

struct ShapeThread {
    latencies: Vec<u64>,
    wrong: u64,
    allocs: u64,
    bytes: u64,
}

fn run_shape(args: &Args, t0: Instant) -> Result<(String, u64), String> {
    let shape_s = args.get("shape").ok_or("--shape is required")?;
    let shape = Shape::parse(shape_s).ok_or_else(|| format!("unknown shape {shape_s:?}"))?;
    let threads: usize = args.num("threads", None)?;
    let vertices: u64 = args.num("vertices", Some(DEFAULT_VERTICES))?;
    let seed: u64 = args.num("seed", Some(DEFAULT_SEED))?;
    let queries: usize = args.num("queries", Some(shape.default_queries()))?;
    if threads == 0 || queries == 0 {
        return Err("--threads and --queries must be positive".into());
    }
    let min_vertices = if matches!(shape, Shape::S1 | Shape::S2) {
        100
    } else {
        4
    };
    if vertices < min_vertices || vertices > u64::from(u32::MAX) {
        return Err(format!("--vertices must be in {min_vertices}..=2^32-1"));
    }
    let warmup = (queries / 100).max(1);

    let mut inst = Instance::generate(shape, vertices, seed);
    let mut fp = Fnv1a64::default();
    fp.bytes(b"query-shape-probe/shape/");
    fp.bytes(shape.name().as_bytes());
    fp.graph(inst.vertices, &inst.edges);
    let mut streams: Vec<Vec<Query>> = (0..threads)
        .map(|t| inst.queries(seed, t as u64, warmup + queries))
        .collect();
    for (t, s) in streams.iter().enumerate() {
        fp.queries(t as u64, s);
    }
    let construction_mismatch = streams
        .iter()
        .flatten()
        .filter(|q| q.expected != shape.expected_answer())
        .count();
    if construction_mismatch > 0 {
        return Err(format!(
            "generator bug: {construction_mismatch} queries contradict the shape's answer"
        ));
    }
    corrupt_for_test(&mut streams);
    let tb = Instant::now();
    let (graph, edges_added) = build_graph(inst.vertices, &inst.edges)?;
    let build_ns = tb.elapsed().as_nanos() as u64;
    eprintln!(
        "query-shape-probe: shape {} built ({} vertices, {} edges added) in {:.3} s; {} threads x ({} warmup + {} timed)",
        shape.name(),
        vertices,
        edges_added,
        build_ns as f64 / 1e9,
        threads,
        warmup,
        queries
    );

    let barrier = Barrier::new(threads);
    let tq = Instant::now();
    let results: Vec<ShapeThread> = std::thread::scope(|sc| {
        let handles: Vec<_> = streams
            .iter()
            .map(|stream| {
                let (g, barrier) = (&graph, &barrier);
                sc.spawn(move || {
                    let mut latencies = Vec::with_capacity(queries);
                    let mut wrong = 0u64;
                    let (warm, timed) = stream.split_at(warmup);
                    barrier.wait();
                    for q in warm {
                        wrong += u64::from(!check(g, q));
                    }
                    let (a0, b0) = (counting::allocs(), counting::bytes());
                    for q in timed {
                        let s = Instant::now();
                        let ok = check(g, q);
                        let ns = s.elapsed().as_nanos() as u64;
                        latencies.push(ns);
                        wrong += u64::from(!ok);
                    }
                    let (a1, b1) = (counting::allocs(), counting::bytes());
                    ShapeThread {
                        latencies,
                        wrong,
                        allocs: a1 - a0,
                        bytes: b1 - b0,
                    }
                })
            })
            .collect();
        handles
            .into_iter()
            .map(|h| h.join().expect("query thread panicked"))
            .collect()
    });
    let query_phase_ns = tq.elapsed().as_nanos() as u64;

    let mut all: Vec<u64> = Vec::with_capacity(threads * queries);
    let (mut wrong, mut allocs, mut bytes) = (0u64, 0u64, 0u64);
    for r in &results {
        all.extend_from_slice(&r.latencies);
        wrong += r.wrong;
        allocs += r.allocs;
        bytes += r.bytes;
    }
    all.sort_unstable();
    let timed = all.len() as u64;
    let json = JsonObject::new()
        .str("tool", "query-shape-probe")
        .str("tool_version", env!("CARGO_PKG_VERSION"))
        .str("mode", "shape")
        .str("shape", shape.name())
        .num("threads", threads)
        .num("vertices", vertices)
        .num("edges", inst.edges.len())
        .num("edges_added", edges_added)
        .num("seed", seed)
        .num("warmup_per_thread", warmup)
        .num("queries_per_thread", queries)
        .num("queries_timed", timed)
        .raw("expected_answer", shape.expected_answer().to_string())
        .obj("latency_ns", latency_obj(&all))
        .num("wrong_answers", wrong)
        .float("allocations_per_query", allocs as f64 / timed as f64)
        .float("allocated_bytes_per_query", bytes as f64 / timed as f64)
        .num("allocations_timed_total", allocs)
        .str("input_fingerprint_fnv1a64", &fp.hex())
        .num("build_ns", build_ns)
        .num("query_phase_ns", query_phase_ns)
        .num("wall_ns", t0.elapsed().as_nanos() as u64)
        .finish();
    Ok((json, wrong))
}

struct SeqThread {
    latencies: Vec<u64>,
    large_ns: u64,
    wrong: u64,
    retained_after_large: i64,
    retained_after_small: i64,
    allocs_after_grace: u64,
    allocs_small_total: u64,
    last_allocating: u64,
}

fn summary_i64(mut v: Vec<i64>) -> JsonObject {
    v.sort_unstable();
    JsonObject::new()
        .num("median", query_shape_probe::nearest_rank_i64(&v, 50, 100))
        .num("max", v[v.len() - 1])
        .num("min", v[0])
}

fn run_sequence(args: &Args, t0: Instant) -> Result<(String, u64), String> {
    let kind = args.get("kind").ok_or("--kind is required")?;
    if kind != "large-then-small" {
        return Err(format!("unknown --kind {kind:?} (only large-then-small)"));
    }
    let threads: usize = args.num("threads", None)?;
    let chain_vertices: u64 = args.num("chain-vertices", Some(DEFAULT_CHAIN_VERTICES))?;
    let vertices: u64 = args.num("vertices", Some(DEFAULT_VERTICES))?;
    let small_queries: usize = args.num("small-queries", Some(DEFAULT_SMALL_QUERIES))?;
    let seed: u64 = args.num("seed", Some(DEFAULT_SEED))?;
    if threads == 0 || small_queries == 0 {
        return Err("--threads and --small-queries must be positive".into());
    }
    if !(100..=u64::from(u32::MAX)).contains(&vertices)
        || !(4..=u64::from(u32::MAX)).contains(&chain_vertices)
    {
        return Err("--vertices must be >= 100 and --chain-vertices >= 4 (and < 2^32)".into());
    }

    let chain = Instance::generate(Shape::L1, chain_vertices, seed);
    let mut small = Instance::generate(Shape::S1, vertices, seed);
    let large_q = Query {
        a: 0,
        b: chain_vertices - 1,
        expected: true,
    };
    let mut streams: Vec<Vec<Query>> = (0..threads)
        .map(|t| small.queries(seed, t as u64, small_queries))
        .collect();
    let mut fp = Fnv1a64::default();
    fp.bytes(b"query-shape-probe/sequence/large-then-small");
    fp.graph(chain.vertices, &chain.edges);
    fp.graph(small.vertices, &small.edges);
    fp.queries(u64::MAX, &[large_q]);
    for (t, s) in streams.iter().enumerate() {
        fp.queries(t as u64, s);
    }
    corrupt_for_test(&mut streams);
    let tb = Instant::now();
    let (chain_graph, _) = build_graph(chain.vertices, &chain.edges)?;
    let (small_graph, small_added) = build_graph(small.vertices, &small.edges)?;
    let build_ns = tb.elapsed().as_nanos() as u64;
    eprintln!(
        "query-shape-probe: sequence built (chain {} vertices, random {} vertices / {} edges added) in {:.3} s; {} threads x (1 large + {} small)",
        chain_vertices,
        vertices,
        small_added,
        build_ns as f64 / 1e9,
        threads,
        small_queries
    );

    let barrier = Barrier::new(threads);
    let tq = Instant::now();
    let results: Vec<SeqThread> = std::thread::scope(|sc| {
        let handles: Vec<_> = streams
            .iter()
            .map(|stream| {
                let (cg, sg, barrier, large_q) = (&chain_graph, &small_graph, &barrier, &large_q);
                sc.spawn(move || {
                    // Everything the probe allocates on this thread happens
                    // before the first reading and is not freed before the last.
                    let mut latencies = Vec::with_capacity(stream.len());
                    warm_tls_destructors();
                    barrier.wait();
                    let mut wrong = 0u64;
                    let base = counting::net();
                    let s = Instant::now();
                    wrong += u64::from(!check(cg, large_q));
                    let large_ns = s.elapsed().as_nanos() as u64;
                    let after_large = counting::net() - base;
                    let a_start = counting::allocs();
                    let mut a_grace = a_start;
                    // 1-based index of the last short query that allocated (0: none).
                    let mut last_allocating = 0u64;
                    for (i, q) in stream.iter().enumerate() {
                        if i == ALLOC_GRACE {
                            a_grace = counting::allocs();
                        }
                        let a_before = counting::allocs();
                        let s = Instant::now();
                        let ok = check(sg, q);
                        let ns = s.elapsed().as_nanos() as u64;
                        if counting::allocs() != a_before {
                            last_allocating = i as u64 + 1;
                        }
                        latencies.push(ns);
                        wrong += u64::from(!ok);
                    }
                    let a_end = counting::allocs();
                    let after_small = counting::net() - base;
                    SeqThread {
                        latencies,
                        large_ns,
                        wrong,
                        retained_after_large: after_large,
                        retained_after_small: after_small,
                        allocs_after_grace: if stream.len() > ALLOC_GRACE {
                            a_end - a_grace
                        } else {
                            0
                        },
                        allocs_small_total: a_end - a_start,
                        last_allocating,
                    }
                })
            })
            .collect();
        handles
            .into_iter()
            .map(|h| h.join().expect("query thread panicked"))
            .collect()
    });
    let query_phase_ns = tq.elapsed().as_nanos() as u64;

    let mut all: Vec<u64> = Vec::with_capacity(threads * small_queries);
    let mut large: Vec<u64> = Vec::with_capacity(threads);
    let mut wrong = 0u64;
    for r in &results {
        all.extend_from_slice(&r.latencies);
        large.push(r.large_ns);
        wrong += r.wrong;
    }
    all.sort_unstable();
    large.sort_unstable();
    let after_grace: Vec<u64> = results.iter().map(|r| r.allocs_after_grace).collect();
    let after_grace_total: u64 = after_grace.iter().sum();
    let counted = (small_queries.saturating_sub(ALLOC_GRACE) * threads) as f64;
    let json = JsonObject::new()
        .str("tool", "query-shape-probe")
        .str("tool_version", env!("CARGO_PKG_VERSION"))
        .str("mode", "sequence")
        .str("kind", kind)
        .num("threads", threads)
        .num("chain_vertices", chain_vertices)
        .num("vertices", vertices)
        .num("edges", small.edges.len())
        .num("edges_added", small_added)
        .num("seed", seed)
        .num("small_queries_per_thread", small_queries)
        .num("allocation_grace_queries", ALLOC_GRACE)
        .obj(
            "retained_after_large_bytes",
            summary_i64(results.iter().map(|r| r.retained_after_large).collect()),
        )
        .obj(
            "retained_after_small_bytes",
            summary_i64(results.iter().map(|r| r.retained_after_small).collect()),
        )
        .obj(
            "small_allocations_after_100",
            JsonObject::new()
                .num("max", after_grace.iter().copied().max().unwrap_or(0))
                .num("total", after_grace_total)
                .float(
                    "per_query",
                    if counted > 0.0 {
                        after_grace_total as f64 / counted
                    } else {
                        0.0
                    },
                ),
        )
        .num(
            "small_allocations_total",
            results.iter().map(|r| r.allocs_small_total).sum::<u64>(),
        )
        .num(
            "small_last_allocating_query_max",
            results.iter().map(|r| r.last_allocating).max().unwrap_or(0),
        )
        .obj("small_latency_ns", latency_obj(&all))
        .obj("large_latency_ns", latency_obj(&large))
        .num("wrong_answers", wrong)
        .str("input_fingerprint_fnv1a64", &fp.hex())
        .num("build_ns", build_ns)
        .num("query_phase_ns", query_phase_ns)
        .num("wall_ns", t0.elapsed().as_nanos() as u64)
        .finish();
    Ok((json, wrong))
}

fn main() -> ExitCode {
    let t0 = Instant::now();
    let argv: Vec<String> = std::env::args().collect();
    let Some(mode) = argv.get(1) else {
        eprintln!("{}", usage());
        return ExitCode::from(1);
    };
    let rest = &argv[2..];
    let result = match mode.as_str() {
        "shape" => Args::parse(rest, &["shape", "threads", "vertices", "seed", "queries"])
            .and_then(|a| run_shape(&a, t0)),
        "sequence" => Args::parse(
            rest,
            &[
                "kind",
                "threads",
                "chain-vertices",
                "vertices",
                "small-queries",
                "seed",
            ],
        )
        .and_then(|a| run_sequence(&a, t0)),
        "-h" | "--help" | "help" => {
            eprintln!("{}", usage());
            return ExitCode::SUCCESS;
        }
        other => Err(format!("unknown mode {other:?}")),
    };
    match result {
        Ok((json, wrong)) => {
            println!("{json}");
            if wrong > 0 {
                eprintln!("query-shape-probe: {wrong} wrong answers");
                ExitCode::from(2)
            } else {
                ExitCode::SUCCESS
            }
        }
        Err(e) => {
            eprintln!("query-shape-probe: {e}\n{}", usage());
            ExitCode::from(1)
        }
    }
}
