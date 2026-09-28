//! Cache-perturbed HDT structural diagnostics, separate from normal benchmarks.
#[path = "../metrics.rs"]
mod metrics;
use knotrel_benchmarks::{
    Config, Operation, WorkloadKind,
    engines::{Engine, EngineKind},
    generate_with_query_percent,
};
use knotrel_core::{HdtStats, HdtStorageStats};
use serde_json::{Value, json};
use std::{error::Error, hint::black_box, path::Path, process::Command, time::Instant};

fn storage(s: HdtStorageStats) -> Value {
    let levels: Vec<_> = s.levels.into_iter().map(|l| json!({
        "level": l.level, "vertices": l.vertices, "tree_edges": l.tree_edges,
        "tree_incidences": l.tree_incidences, "non_tree_incidences": l.non_tree_incidences,
        "token_capacity_bytes": l.token_capacity_bytes, "vertex_index_capacity_bytes": l.vertex_index_capacity_bytes,
        "free_list_capacity_bytes": l.free_list_capacity_bytes, "adjacency_capacity_bytes": l.adjacency_capacity_bytes,
        "mapping_capacity_bytes": l.mapping_capacity_bytes, "mapping_payload_bytes": l.mapping_payload_bytes,
    })).collect();
    json!({"vertex_count": s.vertex_count, "edge_count": s.edge_count, "available_levels": s.available_levels,
        "vector_capacity_bytes": s.vector_capacity_bytes, "ordered_payload_bytes": s.ordered_payload_bytes,
        "edge_arc_capacity_bytes": s.edge_arc_capacity_bytes, "level_capacity_bytes": s.level_capacity_bytes, "levels": levels})
}
fn counters(s: HdtStats) -> Value {
    json!({"tree_cuts": s.tree_cuts, "candidate_edges": s.candidate_edges, "replacements": s.replacements,
        "tree_promotions": s.tree_promotions, "non_tree_promotions": s.non_tree_promotions, "levels_visited": s.levels_visited})
}
fn git(path: &Path) -> Value {
    let read = |args: &[&str]| {
        Command::new("git")
            .arg("-C")
            .arg(path)
            .args(args)
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_owned())
    };
    json!({"revision": read(&["rev-parse", "HEAD"]), "dirty": read(&["status", "--porcelain"]).map(|s| !s.is_empty())})
}
fn run() -> Result<(), Box<dyn Error>> {
    let mut config = Config {
        nodes: 1000,
        rounds: 10,
        seed: 42,
    };
    let mut kind = WorkloadKind::Chain;
    let mut engine = EngineKind::Hdt;
    let mut query_percent = 50;
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        if flag == "--help" || flag == "-h" {
            println!(
                "Usage: hdt-profile [--engine hdt|hdt-v2] [--nodes N] [--rounds N] [--seed N] [--workload NAME] [--query-percent 1..99]\nDiagnostic timings are cache-perturbed and not comparable to normal benchmark timings."
            );
            return Ok(());
        }
        let value = args.next().ok_or("flag requires a value")?;
        match flag.as_str() {
            "--nodes" => config.nodes = value.parse()?,
            "--rounds" => config.rounds = value.parse()?,
            "--seed" => config.seed = value.parse()?,
            "--workload" => kind = WorkloadKind::parse(&value)?,
            "--engine" => engine = EngineKind::parse(&value)?,
            "--query-percent" => query_percent = value.parse()?,
            _ => return Err(format!("unknown argument: {flag}").into()),
        }
    }
    if !matches!(engine, EngineKind::Hdt | EngineKind::HdtV2) {
        return Err("profiling requires hdt or hdt-v2".into());
    }
    let workload = generate_with_query_percent(kind, config, query_percent)?;
    // Match the normal runner's exact serialization field order and optional field.
    #[derive(serde::Serialize)]
    struct Trace<'a> {
        schema_version: u32,
        workload: &'static str,
        config: Config,
        #[serde(skip_serializing_if = "Option::is_none")]
        query_percent: Option<u8>,
        trace: &'a knotrel_benchmarks::Workload,
    }
    let bytes = serde_json::to_vec(&Trace {
        schema_version: 1,
        workload: kind.name(),
        config,
        query_percent: kind.is_sustained().then_some(query_percent),
        trace: &workload,
    })?;
    let fingerprint = bytes.iter().fold(0xcbf29ce484222325_u64, |h, b| {
        (h ^ u64::from(*b)).wrapping_mul(0x100000001b3)
    });
    let nodes: Vec<_> = (0..config.nodes).collect();
    let registration_start = Instant::now();
    let mut graph = Engine::new(engine, &nodes)?;
    let registration_ns = registration_start.elapsed().as_nanos();
    let registered = storage(graph.hdt_storage_stats().ok_or("missing storage")?);
    let initial_edges_start = Instant::now();
    for &(a, b) in &workload.initial_edges {
        if !graph.link(a, b)? {
            return Err("initial edge failed oracle".into());
        }
    }
    let initial_edges_ns = initial_edges_start.elapsed().as_nanos();
    let initial = storage(graph.hdt_storage_stats().ok_or("missing storage")?);
    graph.reset_stats();
    let mut samples: [Vec<u128>; 5] = std::array::from_fn(|_| Vec::new());
    for &op in &workload.operations {
        let before = graph.hdt_stats().ok_or("missing counters")?;
        let (group, elapsed) = match op {
            Operation::Link { source, target } => {
                let start = Instant::now();
                let result = black_box(graph.link(source, target));
                let elapsed = start.elapsed().as_nanos();
                if !result? {
                    return Err("link failed oracle".into());
                }
                (0, elapsed)
            }
            Operation::Connected {
                source,
                target,
                expected,
            } => {
                let start = Instant::now();
                let result = black_box(graph.connected(source, target));
                let elapsed = start.elapsed().as_nanos();
                if result? != expected {
                    return Err("query failed independent oracle".into());
                }
                (1, elapsed)
            }
            Operation::Cut { source, target } => {
                let start = Instant::now();
                let result = black_box(graph.cut(source, target));
                let elapsed = start.elapsed().as_nanos();
                if !result? {
                    return Err("cut failed oracle".into());
                }
                let after = graph.hdt_stats().ok_or("missing counters")?;
                let group = if after.tree_cuts == before.tree_cuts {
                    4
                } else if after.tree_promotions > before.tree_promotions
                    || after.non_tree_promotions > before.non_tree_promotions
                {
                    2
                } else {
                    3
                };
                (group, elapsed)
            }
        };
        samples[group].push(elapsed);
    }
    let replay = storage(graph.hdt_storage_stats().ok_or("missing storage")?);
    let names = [
        "links",
        "queries",
        "tree_cuts_with_promotions",
        "tree_cuts_without_promotions",
        "non_tree_cuts",
    ];
    let timing: serde_json::Map<_, _> = names
        .into_iter()
        .zip(samples)
        .map(|(name, s)| {
            (
                name.to_owned(),
                if s.is_empty() {
                    Value::Null
                } else {
                    serde_json::to_value(metrics::Latency::from_samples(s))
                        .expect("latency serialization")
                },
            )
        })
        .collect();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"schema_version":1, "engine":engine.name(), "workload":kind.name(), "config":config, "query_percent":kind.is_sustained().then_some(query_percent), "trace_fingerprint_fnv1a64":format!("{fingerprint:016x}"), "timing_note":"Diagnostic timings are cache-perturbed and not comparable to normal benchmark timings", "checkouts_at_run_time":{"benchmarks":git(&root),"core":git(&root.join("../knotrel"))}, "snapshots":{"after_node_registration":registered,"after_initial_edges":initial,"after_replay":replay},"counters":counters(graph.hdt_stats().ok_or("missing counters")?),"diagnostic_timings":timing, "diagnostic_stage_timings": {"registration_ns":registration_ns,"initial_edges_ns":initial_edges_ns}})
        )?
    );
    Ok(())
}
fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("hdt-profile: {e}");
            std::process::ExitCode::FAILURE
        }
    }
}
