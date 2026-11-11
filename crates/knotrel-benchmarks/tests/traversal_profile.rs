//! Diagnostic trace identity must match the uninstrumented timing runner.
use std::process::Command;

#[test]
fn legacy_and_sustained_profiles_match_timing_fingerprints() {
    for workload in ["chain-split-rejoin-v1", "sustained-churn-blocks-v1"] {
        let diagnostic = Command::new(env!("CARGO_BIN_EXE_traversal-profile"))
            .args(["16", workload, "50"])
            .output()
            .unwrap();
        assert!(diagnostic.status.success());
        let timed = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args([
                "--nodes",
                "16",
                "--rounds",
                "10",
                "--workload",
                workload,
                "--engine",
                "traversal-bfs",
                "--warmup",
                "0",
                "--repetitions",
                "1",
            ])
            .output()
            .unwrap();
        assert!(timed.status.success());
        let diagnostic: serde_json::Value = serde_json::from_slice(&diagnostic.stdout).unwrap();
        let timed: serde_json::Value = serde_json::from_slice(&timed.stdout).unwrap();
        assert_eq!(
            diagnostic["trace_fingerprint_fnv1a64"],
            timed["trace_fingerprint_fnv1a64"]
        );
    }
}

#[test]
fn scratch_ledger_replays_explicit_rounds_with_exact_counts_and_no_timings() {
    for (workload, percent, connected) in [
        ("chain-split-rejoin-v1", "50", 6),
        ("sustained-churn-blocks-v1", "90", 270),
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_traversal-profile"))
            .args(["16", workload, percent, "3", "--scratch-ledger"])
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["schema_version"], 2);
        assert_eq!(report["config"]["rounds"], 3);
        assert_eq!(report["config"]["seed"], 42);
        assert_eq!(report["counts"]["connected"], connected);
        assert_eq!(
            report["variants"],
            serde_json::json!([
                "fresh-epoch",
                "reused-epoch",
                "fresh-packed",
                "reused-packed"
            ])
        );
        let queries = report["queries"].as_array().unwrap();
        assert_eq!(queries.len() as u64, connected);
        assert_eq!(queries[0]["scratch"].as_array().unwrap().len(), 4);
        assert!(
            queries[1]["scratch"][0]["mark_initialized_elements"]
                .as_u64()
                .unwrap()
                > 0
        );
        assert_eq!(queries[1]["scratch"][1]["mark_initialized_elements"], 0);
        assert_eq!(queries[1]["scratch"][2]["mark_cleared_elements"], 1);
        assert_eq!(queries[1]["scratch"][3]["mark_cleared_elements"], 1);
        assert!(report.get("workload_wall_ns").is_none());
        assert!(report.get("timings").is_none());
        let legacy = Command::new(env!("CARGO_BIN_EXE_traversal-profile"))
            .args(["16", workload, percent, "3"])
            .output()
            .unwrap();
        assert!(legacy.status.success());
        let legacy: serde_json::Value = serde_json::from_slice(&legacy.stdout).unwrap();
        assert_eq!(
            report["trace_fingerprint_fnv1a64"],
            legacy["trace_fingerprint_fnv1a64"]
        );
        assert_eq!(queries[0]["graph"], legacy["queries"][0]["bfs"]);
    }
}

#[test]
fn malformed_diagnostic_arguments_fail_visibly() {
    for args in [
        vec!["16", "chain-split-rejoin-v1", "50", "0", "--scratch-ledger"],
        vec!["16", "chain-split-rejoin-v1", "90", "3", "--scratch-ledger"],
        vec!["16", "sustained-churn-blocks-v1", "90", "3", "--unknown"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_traversal-profile"))
            .args(args)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(!output.stderr.is_empty());
    }
}

#[test]
fn fifo_diagnostic_preserves_legacy_identity_and_compares_matched_regimes() {
    for (workload, percent, connected) in [
        ("chain-split-rejoin-v1", "50", 6),
        ("sustained-churn-blocks-v1", "90", 270),
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_traversal-profile"))
            .args(["16", workload, percent, "3", "--fifo-ledger"])
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["schema_version"], 3);
        assert_eq!(report["counts"]["connected"], connected);
        assert_eq!(report["exact_order_checked_per_query"], true);
        assert_eq!(
            report["variants"],
            serde_json::json!(["fresh-vec", "reused-vec", "fresh-deque", "reused-deque"])
        );
        assert!(report.get("timings").is_none());
        let legacy = Command::new(env!("CARGO_BIN_EXE_traversal-profile"))
            .args(["16", workload, percent, "3", "--scratch-ledger"])
            .output()
            .unwrap();
        assert!(legacy.status.success());
        let legacy: serde_json::Value = serde_json::from_slice(&legacy.stdout).unwrap();
        assert_eq!(
            report["trace_fingerprint_fnv1a64"],
            legacy["trace_fingerprint_fnv1a64"]
        );
        assert_eq!(report["counts"], legacy["counts"]);
        for (index, query) in report["queries"].as_array().unwrap().iter().enumerate() {
            assert_eq!(
                query["work"]["expanded_vertices"],
                legacy["queries"][index]["graph"]["expanded_vertices"]
            );
            assert_eq!(
                query["work"]["examined_arcs"],
                legacy["queries"][index]["graph"]["examined_arcs"]
            );
            for (baseline, candidate) in [(0, 2), (1, 3)] {
                for field in [
                    "mark_initialized_elements",
                    "mark_cleared_elements",
                    "mark_capacity_bytes",
                ] {
                    assert_eq!(
                        query["queues"][baseline][field],
                        query["queues"][candidate][field]
                    );
                }
            }
            assert_eq!(
                query["queues"][2]["peak_logical_len"],
                query["work"]["peak_pending_frontier"]
            );
        }
    }
}
