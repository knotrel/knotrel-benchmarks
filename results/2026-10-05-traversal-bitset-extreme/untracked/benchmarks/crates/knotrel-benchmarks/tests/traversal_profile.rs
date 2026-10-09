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
