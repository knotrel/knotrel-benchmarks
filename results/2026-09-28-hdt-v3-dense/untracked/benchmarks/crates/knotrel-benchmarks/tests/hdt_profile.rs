//! Structural diagnostics exercise both frozen and current HDT adapters.
use serde_json::Value;
use std::process::Command;

#[test]
fn profiler_matches_normal_fingerprint_and_accounts_for_every_operation() {
    for (engine, identity) in [
        ("hdt", "knotrel-core/hdt-sparse-levels-v3"),
        ("hdt-v2", "knotrel-core/hdt-levels-v2"),
    ] {
        let args = [
            "--engine",
            engine,
            "--nodes",
            "16",
            "--rounds",
            "2",
            "--workload",
            "dense-bridge-churn-v1",
            "--query-percent",
            "50",
        ];
        let output = Command::new(env!("CARGO_BIN_EXE_hdt-profile"))
            .args(args)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let profile: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(profile["engine"], identity);
        let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
            .args(args)
            .args(["--warmup", "0"])
            .output()
            .unwrap();
        assert!(output.status.success());
        let normal: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            profile["trace_fingerprint_fnv1a64"],
            normal["trace_fingerprint_fnv1a64"]
        );
        let snapshots = &profile["snapshots"];
        assert_eq!(snapshots["after_node_registration"]["edge_count"], 0);
        assert_eq!(
            snapshots["after_initial_edges"]["edge_count"],
            normal["initial_edges"]
        );
        assert_eq!(snapshots["after_replay"]["vertex_count"], 16);
        assert_eq!(profile["counters"], normal["repetitions"][0]["hdt_stats"]);
        let total: u64 = profile["diagnostic_timings"]
            .as_object()
            .unwrap()
            .values()
            .map(|v| v["count"].as_u64().unwrap_or(0))
            .sum();
        assert_eq!(total, 200);
        assert!(
            profile["timing_note"]
                .as_str()
                .unwrap()
                .contains("cache-perturbed")
        );
    }
}
#[test]
fn profiler_rejects_non_hdt_engines() {
    assert!(
        !Command::new(env!("CARGO_BIN_EXE_hdt-profile"))
            .args(["--engine", "compact-bfs"])
            .output()
            .unwrap()
            .status
            .success()
    );
}
