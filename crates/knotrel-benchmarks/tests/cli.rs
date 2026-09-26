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
    assert_eq!(report["schema_version"], 1);
    assert_eq!(report["config"]["nodes"], 16);
    assert_eq!(report["config"]["rounds"], 4);
    assert_eq!(report["config"]["seed"], 7);
    assert_eq!(report["measurements"]["cut"]["count"], 4);
    assert_eq!(report["measurements"]["link"]["count"], 4);
    assert_eq!(report["measurements"]["connected"]["count"], 8);
    assert!(
        report["compiler"]
            .as_str()
            .unwrap()
            .contains("rustc 1.98.1")
    );
    for op in ["cut", "link", "connected"] {
        let samples = &report["measurements"][op];
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
        vec!["--unknown", "1"],
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
