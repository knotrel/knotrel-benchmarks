//! Command-line runner for the local Knotrel reference baseline.

mod metrics;

use knotrel_benchmarks::{Config, Operation, chain_workload};
use knotrel_core::Graph;
use metrics::Latency;
use serde::Serialize;
use std::{
    error::Error,
    hint::black_box,
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
    measurements: Measurements,
    workload_wall_ns: u128,
}

#[derive(Serialize)]
struct Checkouts {
    core: GitState,
    benchmarks: GitState,
}

#[derive(Serialize)]
struct GitState {
    revision: Option<String>,
    dirty: Option<bool>,
}

#[derive(Serialize)]
struct Measurements {
    cut: Latency,
    link: Latency,
    connected: Latency,
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
    let Some(config) = parse_args()? else {
        println!(
            "Usage: knotrel-benchmarks [--nodes N] [--rounds N] [--seed N]\nDefaults: --nodes 10000 --rounds 1000 --seed 42\nRun with cargo run --release --locked for measurements."
        );
        return Ok(());
    };
    let workload = chain_workload(config)?;
    let mut graph = Graph::new();
    for (source, target) in workload.initial_edges {
        graph.link(source, target)?;
    }
    let mut cuts = Vec::with_capacity(config.rounds);
    let mut links = Vec::with_capacity(config.rounds);
    let mut queries = Vec::with_capacity(config.rounds * 2);
    let timestamp_unix_seconds = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();

    // Setup and trace allocation finish before this wall timer. Each operation
    // interval includes the call and a compiler barrier; result checking and
    // sample storage follow the interval. The wall interval additionally includes
    // checks, loop dispatch and sampling overhead. It is not operation throughput.
    let wall_start = Instant::now();
    for operation in workload.operations {
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
            }
        }
    }
    let workload_wall_ns = wall_start.elapsed().as_nanos();
    let benchmark_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let core_root = benchmark_root.join("../knotrel");
    let report = Report {
        schema_version: 1,
        engine: "knotrel-core/reference-bfs",
        workload: "chain-split-rejoin-v1",
        benchmark_version: env!("CARGO_PKG_VERSION"),
        compiler: env!("KNOTREL_BUILD_COMPILER"),
        os: std::env::consts::OS,
        arch: std::env::consts::ARCH,
        debug_assertions: cfg!(debug_assertions),
        timestamp_unix_seconds,
        config,
        checkouts_at_run_time: Checkouts {
            core: git_state(&core_root),
            benchmarks: git_state(&benchmark_root),
        },
        measurements: Measurements {
            cut: Latency::from_samples(cuts),
            link: Latency::from_samples(links),
            connected: Latency::from_samples(queries),
        },
        workload_wall_ns,
    };
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}

/// Parses explicit numeric flags; malformed input fails before graph allocation.
fn parse_args() -> Result<Option<Config>, Box<dyn Error>> {
    let mut config = Config {
        nodes: 10_000,
        rounds: 1_000,
        seed: 42,
    };
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        if flag == "--help" || flag == "-h" {
            return Ok(None);
        }
        match flag.as_str() {
            "--nodes" => config.nodes = args.next().ok_or("--nodes needs a value")?.parse()?,
            "--rounds" => config.rounds = args.next().ok_or("--rounds needs a value")?.parse()?,
            "--seed" => config.seed = args.next().ok_or("--seed needs a value")?.parse()?,
            _ => return Err(format!("unknown argument: {flag}").into()),
        }
    }
    Ok(Some(config))
}

/// Records checkout provenance at run time, not a claim about binary provenance.
/// Missing Git or moved source checkouts produce null metadata, never invented IDs.
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
