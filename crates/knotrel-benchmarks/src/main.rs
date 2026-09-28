//! Command-line runner for the local Knotrel reference baseline.

mod metrics;

use knotrel_benchmarks::engines::{Engine, EngineKind};
use knotrel_benchmarks::{Config, Operation, Workload, WorkloadKind, generate_with_query_percent};
use metrics::Latency;
use serde::Serialize;
use std::{
    error::Error,
    hint::black_box,
    io::Write,
    path::Path,
    process::{Command, ExitCode},
    time::{Instant, SystemTime, UNIX_EPOCH},
};

#[derive(Serialize)]
struct Report {
    schema_version: u32,
    engine: &'static str,
    workload: &'static str,
    benchmark_version: &'static str,
    compiler: &'static str,
    os: &'static str,
    arch: &'static str,
    debug_assertions: bool,
    timestamp_unix_seconds: u64,
    config: Config,
    checkouts_at_run_time: Checkouts,
    warmup: usize,
    query_repeats: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    query_percent: Option<u8>,
    trace_fingerprint_fnv1a64: String,
    initial_edges: usize,
    initial_density: f64,
    initial_max_degree: usize,
    repetitions: Vec<Run>,
}

#[derive(Clone, Serialize)]
struct Checkouts {
    core: GitState,
    benchmarks: GitState,
}
#[derive(Clone, Serialize)]
struct GitState {
    revision: Option<String>,
    dirty: Option<bool>,
}
#[derive(Serialize)]
struct Run {
    setup_ns: u128,
    #[serde(skip_serializing_if = "Option::is_none")]
    forest_stats: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    hdt_stats: Option<serde_json::Value>,
    query_true: Option<Latency>,
    query_false: Option<Latency>,
    repeated_queries: Option<Latency>,
    measurements: Measurements,
    workload_wall_ns: u128,
}
#[derive(Serialize)]
struct Measurements {
    cut: Option<Latency>,
    link: Option<Latency>,
    connected: Latency,
}
#[derive(Serialize)]
struct TraceExport<'a> {
    schema_version: u32,
    workload: &'static str,
    config: Config,
    #[serde(skip_serializing_if = "Option::is_none")]
    query_percent: Option<u8>,
    trace: &'a Workload,
}
struct Options {
    config: Config,
    kind: WorkloadKind,
    warmup: usize,
    repetitions: usize,
    trace_out: Option<String>,
    engines: Vec<EngineKind>,
    query_repeats: usize,
    query_percent: u8,
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("knotrel-benchmarks: {error}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let Some(options) = parse_args()? else {
        println!(
            "Usage: knotrel-benchmarks [--nodes N] [--rounds N] [--seed N] [--workload NAME] [--warmup N] [--repetitions N] [--trace-out PATH] [--engine NAME|all|COMMA_LIST] [--query-repeats N] [--query-percent 1..99]\nEngines: reference-bfs (default), compact-bfs, dense-bfs, petgraph-dfs, outils-hdt, ett-scan (pruned v2), ett-scan-v1 (frozen baseline), hdt (sparse HDT v3), hdt-v2 (frozen HDT v2); query repeats default 0.\nDefaults: --nodes 10000 --rounds 1000 --seed 42 --warmup 1 --repetitions 1\nWorkloads: chain-split-rejoin-v1 (default), cycle-alternatives-v1, components-join-split-v1, hub-alternatives-v1, sustained-churn-path-v1, sustained-churn-blocks-v1, dense-bridge-churn-v1, redundant-bridge-churn-v1\nSustained workloads use 100 operations per round; --query-percent defaults to 50.\nUse --release --locked for measurements. Warmup counts complete unreported replays on fresh graphs."
        );
        return Ok(());
    };
    let config = options.config;
    let workload = generate_with_query_percent(options.kind, config, options.query_percent)?;
    let query_percent = options.kind.is_sustained().then_some(options.query_percent);
    let export = TraceExport {
        schema_version: 1,
        workload: options.kind.name(),
        config,
        query_percent,
        trace: &workload,
    };
    let bytes = serde_json::to_vec(&export)?;
    // Stable fingerprint of exact compact JSON bytes; not a cryptographic hash.
    let fingerprint = bytes.iter().fold(0xcbf29ce484222325_u64, |hash, byte| {
        (hash ^ u64::from(*byte)).wrapping_mul(0x100000001b3)
    });
    if let Some(path) = &options.trace_out {
        // Never overwrite user files, including source files or prior traces.
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)?;
        file.write_all(&bytes)?;
    }
    drop(bytes);
    let mut degree = vec![0_usize; usize::try_from(config.nodes)?];
    for &(a, b) in &workload.initial_edges {
        degree[a as usize] += 1;
        degree[b as usize] += 1;
    }
    let initial_max_degree = degree.into_iter().max().unwrap_or(0);
    let timestamp_unix_seconds = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    let benchmark_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let core_root = benchmark_root.join("../knotrel");
    let checkouts_at_run_time = Checkouts {
        core: git_state(&core_root),
        benchmarks: git_state(&benchmark_root),
    };
    let mut reports = Vec::new();
    for &engine in &options.engines {
        for _ in 0..options.warmup {
            replay(config, &workload, engine, options.query_repeats)?;
        }
        let mut repetitions = Vec::new();
        repetitions.try_reserve_exact(options.repetitions)?;
        for _ in 0..options.repetitions {
            repetitions.push(replay(config, &workload, engine, options.query_repeats)?);
        }
        let report = Report {
            schema_version: 2,
            engine: engine.name(),
            workload: options.kind.name(),
            benchmark_version: env!("CARGO_PKG_VERSION"),
            compiler: env!("KNOTREL_BUILD_COMPILER"),
            os: std::env::consts::OS,
            arch: std::env::consts::ARCH,
            debug_assertions: cfg!(debug_assertions),
            timestamp_unix_seconds,
            config,
            checkouts_at_run_time: checkouts_at_run_time.clone(),
            warmup: options.warmup,
            query_repeats: options.query_repeats,
            query_percent,
            trace_fingerprint_fnv1a64: format!("{fingerprint:016x}"),
            initial_edges: workload.initial_edges.len(),
            initial_density: 2.0 * workload.initial_edges.len() as f64
                / (config.nodes as f64 * (config.nodes - 1) as f64),
            initial_max_degree,
            repetitions,
        };
        reports.push(report);
    }
    if reports.len() == 1 {
        println!("{}", serde_json::to_string_pretty(&reports[0])?);
    } else {
        println!(
            "{}",
            serde_json::to_string_pretty(
                &serde_json::json!({"schema_version": 3, "comparisons": reports})
            )?
        );
    }
    Ok(())
}

/// Rebuild before every replay. Warmups execute identical timers and checks,
/// then discard summaries. Graph state never carries across repetitions, but
/// allocator/process caches can remain warm. Setup and sorting are untimed.
fn replay(
    config: Config,
    workload: &Workload,
    engine: EngineKind,
    query_repeats: usize,
) -> Result<Run, Box<dyn Error>> {
    let setup_start = Instant::now();
    let nodes: Vec<u64> = (0..config.nodes).collect();
    let mut graph = Engine::new(engine, &nodes)?;
    for &(source, target) in &workload.initial_edges {
        graph.link(source, target)?;
    }
    let setup_ns = setup_start.elapsed().as_nanos();
    graph.reset_stats();
    let mut counts = [0_usize; 4];
    for operation in &workload.operations {
        counts[match operation {
            Operation::Cut { .. } => 0,
            Operation::Link { .. } => 1,
            Operation::Connected { expected: true, .. } => 2,
            Operation::Connected {
                expected: false, ..
            } => 3,
        }] += 1;
    }
    let allocate = |count| -> Result<Vec<u128>, Box<dyn Error>> {
        let mut samples = Vec::new();
        samples.try_reserve_exact(count)?;
        Ok(samples)
    };
    let mut cuts = allocate(counts[0])?;
    let mut links = allocate(counts[1])?;
    let mut queries = allocate(counts[2] + counts[3])?;
    let mut true_queries = allocate(counts[2])?;
    let mut false_queries = allocate(counts[3])?;
    let mut repeats = allocate(
        (counts[2] + counts[3])
            .checked_mul(query_repeats)
            .ok_or("too many query repeats")?,
    )?;
    // Each interval includes the call, a compiler barrier and clock overhead.
    // Checking and sample insertion follow the interval. Wall time additionally
    // includes dispatch, checking and sampling; it is not operation throughput.
    let wall_start = Instant::now();
    for &operation in &workload.operations {
        match operation {
            Operation::Cut { source, target } => {
                let start = Instant::now();
                let changed = black_box(graph.cut(source, target));
                let elapsed = start.elapsed().as_nanos();
                if !changed? {
                    return Err("cut failed the workload oracle".into());
                }
                cuts.push(elapsed);
            }
            Operation::Link { source, target } => {
                let start = Instant::now();
                let changed = black_box(graph.link(source, target));
                let elapsed = start.elapsed().as_nanos();
                if !changed? {
                    return Err("link failed the workload oracle".into());
                }
                links.push(elapsed);
            }
            Operation::Connected {
                source,
                target,
                expected,
            } => {
                let start = Instant::now();
                let actual = black_box(graph.connected(source, target));
                let elapsed = start.elapsed().as_nanos();
                if actual? != expected {
                    return Err("connectivity failed the workload oracle".into());
                }
                queries.push(elapsed);
                if expected {
                    true_queries.push(elapsed);
                } else {
                    false_queries.push(elapsed);
                }
                for _ in 0..query_repeats {
                    let start = Instant::now();
                    let repeated = black_box(graph.connected(source, target));
                    let elapsed = start.elapsed().as_nanos();
                    if repeated? != expected {
                        return Err("repeated query failed the workload oracle".into());
                    }
                    repeats.push(elapsed);
                }
            }
        }
    }
    let workload_wall_ns = wall_start.elapsed().as_nanos();
    let forest_stats = graph.forest_stats().map(|stats| {
        serde_json::json!({
            "tree_cuts": stats.tree_cuts,
            "scanned_vertices": stats.scanned_vertices,
            "candidate_edges": stats.candidate_edges,
            "replacements": stats.replacements,
        })
    });
    let hdt_stats = graph.hdt_stats().map(|stats| {
        serde_json::json!({
            "tree_cuts": stats.tree_cuts,
            "candidate_edges": stats.candidate_edges,
            "replacements": stats.replacements,
            "tree_promotions": stats.tree_promotions,
            "non_tree_promotions": stats.non_tree_promotions,
            "levels_visited": stats.levels_visited,
        })
    });
    let optional = |samples: Vec<u128>| {
        if samples.is_empty() {
            None
        } else {
            Some(Latency::from_samples(samples))
        }
    };
    Ok(Run {
        setup_ns,
        forest_stats,
        hdt_stats,
        query_true: optional(true_queries),
        query_false: optional(false_queries),
        repeated_queries: optional(repeats),
        measurements: Measurements {
            cut: optional(cuts),
            link: optional(links),
            connected: Latency::from_samples(queries),
        },
        workload_wall_ns,
    })
}

/// Parses flags before allocating graphs. Repeated flags use their last value.
fn parse_args() -> Result<Option<Options>, Box<dyn Error>> {
    let mut config = Config {
        nodes: 10_000,
        rounds: 1_000,
        seed: 42,
    };
    let mut kind = WorkloadKind::Chain;
    let mut warmup = 1;
    let mut repetitions = 1;
    let mut trace_out = None;
    let mut engines = vec![EngineKind::Reference];
    let mut query_repeats = 0;
    let mut query_percent = 50;
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        if flag == "--help" || flag == "-h" {
            return Ok(None);
        }
        match flag.as_str() {
            "--nodes" => config.nodes = args.next().ok_or("--nodes needs a value")?.parse()?,
            "--rounds" => config.rounds = args.next().ok_or("--rounds needs a value")?.parse()?,
            "--seed" => config.seed = args.next().ok_or("--seed needs a value")?.parse()?,
            "--workload" => {
                kind = WorkloadKind::parse(&args.next().ok_or("--workload needs a value")?)?
            }
            "--warmup" => warmup = args.next().ok_or("--warmup needs a value")?.parse()?,
            "--repetitions" => {
                repetitions = args.next().ok_or("--repetitions needs a value")?.parse()?
            }
            "--engine" => {
                let value = args.next().ok_or("--engine needs a value")?;
                engines = if value == "all" {
                    EngineKind::ALL.to_vec()
                } else {
                    value
                        .split(',')
                        .map(EngineKind::parse)
                        .collect::<Result<Vec<_>, _>>()?
                };
                for (i, kind) in engines.iter().enumerate() {
                    if engines[..i].contains(kind) {
                        return Err("duplicate engine".into());
                    }
                }
            }
            "--query-percent" => {
                query_percent = args
                    .next()
                    .ok_or("--query-percent needs a value")?
                    .parse()?;
            }
            "--query-repeats" => {
                query_repeats = args
                    .next()
                    .ok_or("--query-repeats needs a value")?
                    .parse()?
            }
            "--trace-out" => trace_out = Some(args.next().ok_or("--trace-out needs a value")?),
            _ => return Err(format!("unknown argument: {flag}").into()),
        }
    }
    if repetitions == 0 {
        return Err("repetitions must be at least 1".into());
    }
    Ok(Some(Options {
        config,
        kind,
        warmup,
        repetitions,
        trace_out,
        engines,
        query_repeats,
        query_percent,
    }))
}

/// Runtime checkout provenance, not binary attestation. Missing metadata is null.
fn git_state(directory: &Path) -> GitState {
    let command = |args: &[&str]| -> Option<String> {
        let output = Command::new("git")
            .arg("-C")
            .arg(directory)
            .args(args)
            .output()
            .ok()?;
        output
            .status
            .success()
            .then(|| String::from_utf8_lossy(&output.stdout).trim().to_owned())
    };
    GitState {
        revision: command(&["rev-parse", "HEAD"]),
        dirty: command(&["status", "--porcelain"]).map(|status| !status.is_empty()),
    }
}
