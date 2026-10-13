//! Initialization timing accounting, constructor parity, and CLI compatibility.

use knotrel_benchmarks::engines::{Engine, EngineKind};
use serde_json::Value;
use std::process::Command;

#[test]
fn observed_constructor_preserves_validation_and_dynamic_semantics() {
    for kind in EngineKind::ALL {
        for nodes in [&[][..], &[1, 1][..]] {
            assert_eq!(
                Engine::new(kind, nodes).err(),
                Engine::new_with_timings(kind, nodes).err()
            );
        }
        let nodes = [0, 3, 99, u64::MAX];
        let mut ordinary = Engine::new(kind, &nodes).unwrap();
        let (mut observed, timing) = Engine::new_with_timings(kind, &nodes).unwrap();
        assert_eq!(
            timing.total_ns,
            timing.validation_ns + timing.vertex_registration_ns + timing.other_ns
        );
        for _ in 0..4 {
            for (a, b) in [(0, 3), (3, 99), (99, 0), (0, 3)] {
                assert_eq!(ordinary.link(a, b), observed.link(a, b));
            }
            for (a, b) in [(0, 3), (3, 99), (99, 0), (0, 3)] {
                assert_eq!(ordinary.cut(a, b), observed.cut(a, b));
                for &x in &nodes {
                    for &y in &nodes {
                        assert_eq!(ordinary.connected(x, y), observed.connected(x, y));
                    }
                }
            }
        }
    }
}

fn run(args: &[&str]) -> Value {
    let output = Command::new(env!("CARGO_BIN_EXE_initialization-profile"))
        .args(args)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn phases_partition_total_and_match_legacy_trace_identity() {
    for workload in [
        "chain-split-rejoin-v1",
        "cycle-alternatives-v1",
        "dense-bridge-churn-v1",
        "components-join-split-v1",
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args([
                "--nodes",
                "16",
                "--rounds",
                "2",
                "--workload",
                workload,
                "--engine",
                "compact-bfs",
                "--warmup",
                "0",
            ])
            .output()
            .unwrap();
        assert!(output.status.success());
        let legacy: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(legacy["schema_version"], 2);
        assert!(legacy["repetitions"][0].get("phases").is_none());
        for engine in ["compact-bfs", "ett-scan", "hdt"] {
            for surface in ["adapter", "facade", "facade-limited"] {
                let report = run(&[
                    "--nodes",
                    "16",
                    "--rounds",
                    "2",
                    "--workload",
                    workload,
                    "--engine",
                    engine,
                    "--surface",
                    surface,
                    "--validate",
                    "--warmup",
                    "1",
                    "--repetitions",
                    "2",
                ]);
                assert_eq!(report["repetitions"].as_array().unwrap().len(), 2);
                assert_eq!(report["validated_dynamic_continuation"], true);
                for measured in report["repetitions"].as_array().unwrap() {
                    assert_eq!(
                        measured["trace_fingerprint_fnv1a64"],
                        legacy["trace_fingerprint_fnv1a64"]
                    );
                    assert_eq!(measured["initial_edges"], legacy["initial_edges"]);
                    let p = &measured["phases"];
                    let setup: u64 = [
                        "node_vector_ns",
                        "adapter_validation_ns",
                        "vertex_registration_ns",
                        "constructor_other_ns",
                        "initial_edges_ns",
                        "setup_other_ns",
                    ]
                    .iter()
                    .map(|key| p[key].as_u64().unwrap_or(0))
                    .sum();
                    assert_eq!(measured["setup_ns"], setup);
                    assert_eq!(
                        measured["total_initialization_ns"],
                        setup
                            + p["input_generation_ns"].as_u64().unwrap()
                            + p["trace_encoding_fingerprint_ns"].as_u64().unwrap()
                    );
                    assert_eq!(p["adapter_validation_ns"].is_null(), surface != "adapter");
                }
            }
        }
    }
}

#[test]
fn whole_timer_control_and_invalid_arguments_are_explicit() {
    let report = run(&["--nodes", "16", "--timing", "whole"]);
    let run = &report["repetitions"][0];
    assert!(run.get("phases").is_none());
    assert!(run["total_initialization_ns"].as_u64().unwrap() >= run["setup_ns"].as_u64().unwrap());
    for args in [
        vec!["--engine", "reference-bfs"],
        vec!["--surface", "unknown"],
        vec!["--timing", "unknown"],
        vec!["--repetitions", "0"],
        vec!["--nodes", "1"],
        vec!["--unknown", "1"],
        vec!["--nodes"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_initialization-profile"))
            .args(args)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
        assert!(!output.stderr.is_empty());
    }
}
