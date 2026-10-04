//! End-to-end checks of benchmark output and input validation.

use serde_json::Value;
use std::process::Command;

#[test]
fn smoke_run_emits_machine_readable_measurements_and_configuration() {
    let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
        .args(["--nodes", "16", "--rounds", "4", "--seed", "7"])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).expect("benchmark must emit JSON");
    assert_eq!(report["schema_version"], 2);
    assert!(report.get("query_percent").is_none());
    assert_eq!(report["config"]["nodes"], 16);
    assert_eq!(report["config"]["rounds"], 4);
    assert_eq!(report["config"]["seed"], 7);
    assert_eq!(report["repetitions"][0]["measurements"]["cut"]["count"], 4);
    assert_eq!(report["repetitions"][0]["measurements"]["link"]["count"], 4);
    assert_eq!(
        report["repetitions"][0]["measurements"]["connected"]["count"],
        8
    );
    assert!(
        report["compiler"]
            .as_str()
            .unwrap()
            .contains("rustc 1.98.1")
    );
    for op in ["cut", "link", "connected"] {
        let samples = &report["repetitions"][0]["measurements"][op];
        let values: Vec<u64> = ["min_ns", "p50_ns", "p95_ns", "p99_ns", "max_ns"]
            .into_iter()
            .map(|key| samples[key].as_u64().unwrap())
            .collect();
        assert!(values.windows(2).all(|pair| pair[0] <= pair[1]));
    }
}

#[test]
fn invalid_arguments_fail_without_printing_measurements() {
    for args in [
        vec!["--nodes", "1"],
        vec!["--rounds", "0"],
        vec!["--seed"],
        vec!["--workload", "invalid"],
        vec!["--workload", "cycle-alternatives-v1", "--nodes", "5"],
        vec!["--repetitions", "0"],
        vec!["--warmup", "-1"],
        vec!["--unknown", "1"],
        vec!["--query-percent", "0"],
        vec!["--query-percent", "100"],
        vec!["--query-percent", "10"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args(args)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
        assert!(!output.stderr.is_empty());
    }
}

#[test]
fn reusable_traces_match_an_independent_matrix_oracle() {
    // A wrong topology answer, duplicate initial edge, or ineffective update
    // must fail even when the measured engine agrees with the generator.
    for name in [
        "chain-split-rejoin-v1",
        "cycle-alternatives-v1",
        "components-join-split-v1",
        "hub-alternatives-v1",
    ] {
        for nodes in [6, 7, 12] {
            for seed in [0, 42, u64::MAX] {
                let path = std::env::temp_dir().join(format!(
                    "knotrel-trace-{}-{name}-{nodes}-{seed}.json",
                    std::process::id()
                ));
                let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
                    .args([
                        "--workload",
                        name,
                        "--nodes",
                        &nodes.to_string(),
                        "--rounds",
                        "9",
                        "--seed",
                        &seed.to_string(),
                        "--warmup",
                        "1",
                        "--repetitions",
                        "2",
                        "--trace-out",
                        path.to_str().unwrap(),
                    ])
                    .output()
                    .unwrap();
                assert!(
                    output.status.success(),
                    "{}",
                    String::from_utf8_lossy(&output.stderr)
                );
                let report: Value = serde_json::from_slice(&output.stdout).unwrap();
                assert_eq!(report["repetitions"].as_array().unwrap().len(), 2);
                assert_eq!(report["warmup"], 1);
                let bytes = std::fs::read(&path).unwrap();
                let trace: Value = serde_json::from_slice(&bytes).unwrap();
                std::fs::remove_file(path).unwrap();
                let mut adjacency = vec![vec![false; nodes]; nodes];
                for edge in trace["trace"]["initial_edges"].as_array().unwrap() {
                    let a = edge[0].as_u64().unwrap() as usize;
                    let b = edge[1].as_u64().unwrap() as usize;
                    assert!(a != b && !adjacency[a][b]);
                    adjacency[a][b] = true;
                    adjacency[b][a] = true;
                }
                for operation in trace["trace"]["operations"].as_array().unwrap() {
                    let a = operation["source"].as_u64().unwrap() as usize;
                    let b = operation["target"].as_u64().unwrap() as usize;
                    match operation["op"].as_str().unwrap() {
                        "link" | "cut" => {
                            let inserted = operation["op"] == "link";
                            assert_ne!(adjacency[a][b], inserted);
                            adjacency[a][b] = inserted;
                            adjacency[b][a] = inserted;
                        }
                        "connected" => {
                            let mut reach = adjacency.clone();
                            for (i, row) in reach.iter_mut().enumerate() {
                                row[i] = true;
                            }
                            for k in 0..nodes {
                                for i in 0..nodes {
                                    for j in 0..nodes {
                                        reach[i][j] |= reach[i][k] && reach[k][j];
                                    }
                                }
                            }
                            assert_eq!(
                                reach[a][b],
                                operation["expected"].as_bool().unwrap(),
                                "{name}, n={nodes}, seed={seed}"
                            );
                        }
                        _ => panic!("unknown trace operation"),
                    }
                }
                let queries = trace["trace"]["operations"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .filter(|op| op["op"] == "connected")
                    .count();
                for run in report["repetitions"].as_array().unwrap() {
                    assert_eq!(run["measurements"]["connected"]["count"], queries);
                }
            }
        }
    }
}

#[test]
fn export_is_stable_across_sampling_options_and_never_overwrites_files() {
    let path = std::env::temp_dir().join(format!("knotrel-export-{}.json", std::process::id()));
    let mut fingerprints = Vec::new();
    let mut traces = Vec::new();
    for warmup in ["0", "2"] {
        let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args([
                "--nodes",
                "8",
                "--rounds",
                "2",
                "--warmup",
                warmup,
                "--trace-out",
                path.to_str().unwrap(),
            ])
            .output()
            .unwrap();
        assert!(output.status.success());
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        fingerprints.push(report["trace_fingerprint_fnv1a64"].clone());
        traces.push(std::fs::read(&path).unwrap());
        let rejected = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args([
                "--nodes",
                "6",
                "--rounds",
                "1",
                "--trace-out",
                path.to_str().unwrap(),
            ])
            .output()
            .unwrap();
        assert!(!rejected.status.success());
        assert_eq!(std::fs::read(&path).unwrap(), *traces.last().unwrap());
        std::fs::remove_file(&path).unwrap();
    }
    assert_eq!(fingerprints[0], fingerprints[1]);
    assert_eq!(traces[0], traces[1]);
}

#[test]
fn all_engines_share_trace_and_keep_repeat_queries_separate() {
    let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
        .args([
            "--nodes",
            "16",
            "--rounds",
            "4",
            "--engine",
            "all",
            "--query-repeats",
            "2",
            "--warmup",
            "0",
        ])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    let comparisons = report["comparisons"].as_array().unwrap();
    assert_eq!(comparisons.len(), 10);
    for backend in comparisons {
        assert_eq!(
            backend["trace_fingerprint_fnv1a64"],
            comparisons[0]["trace_fingerprint_fnv1a64"]
        );
        let run = &backend["repetitions"][0];
        assert_eq!(run["measurements"]["connected"]["count"], 8);
        assert_eq!(run["repeated_queries"]["count"], 16);
        assert_eq!(run["query_true"]["count"], 4);
        assert_eq!(run["query_false"]["count"], 4);
        assert!(run["setup_ns"].as_u64().is_some());
        if backend["engine"] == "knotrel-core/ett-scan-v1"
            || backend["engine"] == "knotrel-core/ett-pruned-v2"
        {
            assert_eq!(run["forest_stats"]["tree_cuts"], 4);
            assert_eq!(run["forest_stats"]["replacements"], 0);
        } else {
            assert!(run.get("forest_stats").is_none());
        }
    }
}

#[test]
fn sustained_ratios_exports_repeats_and_fingerprints_are_consistent() {
    for name in ["sustained-churn-path-v1", "sustained-churn-blocks-v1"] {
        let mut fingerprints = Vec::new();
        for percent in [10_u64, 50, 90, 99] {
            let mut ratio_fingerprints = Vec::new();
            for repeats in [0_u64, 2] {
                let path = std::env::temp_dir().join(format!(
                    "knotrel-sustained-{}-{name}-{percent}-{repeats}.json",
                    std::process::id()
                ));
                let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
                    .args([
                        "--workload",
                        name,
                        "--nodes",
                        "33",
                        "--rounds",
                        "1",
                        "--query-percent",
                        &percent.to_string(),
                        "--query-repeats",
                        &repeats.to_string(),
                        "--warmup",
                        "0",
                        "--trace-out",
                        path.to_str().unwrap(),
                    ])
                    .output()
                    .unwrap();
                assert!(
                    output.status.success(),
                    "{}",
                    String::from_utf8_lossy(&output.stderr)
                );
                let report: Value = serde_json::from_slice(&output.stdout).unwrap();
                let bytes = std::fs::read(&path).unwrap();
                std::fs::remove_file(path).unwrap();
                let trace: Value = serde_json::from_slice(&bytes).unwrap();
                assert_eq!(trace["query_percent"], percent);
                assert_eq!(report["query_percent"], percent);
                assert_eq!(trace["trace"]["operations"].as_array().unwrap().len(), 100);
                let run = &report["repetitions"][0];
                assert_eq!(run["measurements"]["connected"]["count"], percent);
                assert_eq!(
                    run["measurements"]["cut"]["count"].as_u64().unwrap_or(0)
                        + run["measurements"]["link"]["count"].as_u64().unwrap_or(0),
                    100 - percent
                );
                assert_eq!(
                    run["repeated_queries"]["count"].as_u64().unwrap_or(0),
                    repeats * percent
                );
                let hash = bytes.iter().fold(0xcbf29ce484222325_u64, |hash, byte| {
                    (hash ^ u64::from(*byte)).wrapping_mul(0x100000001b3)
                });
                assert_eq!(report["trace_fingerprint_fnv1a64"], format!("{hash:016x}"));
                ratio_fingerprints.push(report["trace_fingerprint_fnv1a64"].clone());
            }
            assert_eq!(ratio_fingerprints[0], ratio_fingerprints[1]);
            assert!(!fingerprints.contains(&ratio_fingerprints[0]));
            fingerprints.push(ratio_fingerprints.remove(0));
        }
    }
}

#[test]
fn hdt_dense_replays_validate_oracle_and_report_level_work() {
    for workload in ["dense-bridge-churn-v1", "redundant-bridge-churn-v1"] {
        let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args([
                "--engine",
                "hdt",
                "--nodes",
                "16",
                "--rounds",
                "4",
                "--workload",
                workload,
                "--query-percent",
                "50",
                "--query-repeats",
                "1",
            ])
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        let run = &report["repetitions"][0];
        assert_eq!(report["engine"], "knotrel-core/hdt-sparse-levels-v3");
        assert_eq!(run["measurements"]["connected"]["count"], 200);
        assert_eq!(run["repeated_queries"]["count"], 200);
        assert!(run.get("forest_stats").is_none());
        assert!(run["hdt_stats"]["tree_cuts"].as_u64().unwrap() > 0);
        assert!(run["hdt_stats"]["non_tree_promotions"].as_u64().unwrap() > 0);
    }
}
