//! Imported traces are checked before measurements, independently of the backend.
use serde_json::{Value, json};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

fn fixture() -> Value {
    json!({
        "schema_version": 1, "kind": "connectivity-import", "workload": "fixture-outages-v1",
        "node_ids": ["A", "B", "isolated"],
        "provenance": {"source_url": "https://example.org/fixture", "source_revision": "fixture-v1",
          "source_sha256": "a".repeat(64), "license": "CC0-1.0", "citation": "Synthetic test fixture",
          "retrieved_date": "2026-10-03"},
        "transform": {"generator": "fixture-v1"},
        "batches": [{"time": 0, "start": 0, "end": 2}, {"time": 1, "start": 2, "end": 4}],
        "trace": {"initial_edges": [[0,1]], "operations": [
          {"op":"cut", "source":0, "target":1},
          {"op":"connected", "source":0, "target":1, "expected":false},
          {"op":"link", "source":0, "target":1},
          {"op":"connected", "source":0, "target":2, "expected":false}]}
    })
}
fn run(value: &Value, extra: &[&str]) -> Output {
    run_bytes(&serde_json::to_vec(value).unwrap(), extra)
}
fn run_bytes(bytes: &[u8], extra: &[&str]) -> Output {
    static NEXT: AtomicUsize = AtomicUsize::new(0);
    let path = std::env::temp_dir().join(format!(
        "knotrel-import-{}-{}.json",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::write(&path, bytes).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
        .arg("--trace-in")
        .arg(&path)
        .args(["--warmup", "0"])
        .args(extra)
        .output()
        .unwrap();
    std::fs::remove_file(path).unwrap();
    output
}
#[test]
fn imported_trace_replays_across_engines_with_separate_repeat_queries() {
    let output = run(
        &fixture(),
        &[
            "--engine",
            "compact-bfs,ett-scan,hdt,petgraph-dfs",
            "--query-repeats",
            "2",
        ],
    );
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    for item in report["comparisons"].as_array().unwrap() {
        assert_eq!(item["schema_version"], 4);
        assert!(item.get("config").is_none());
        assert_eq!(item["import"]["node_count"], 3);
        assert_eq!(item["import"]["validated_queries"], 2);
        assert_eq!(
            item["repetitions"][0]["measurements"]["connected"]["count"],
            2
        );
        assert_eq!(item["repetitions"][0]["repeated_queries"]["count"], 4);
    }
}
#[test]
fn rejects_corrupt_traces_before_output() {
    let mut cases = vec![];
    let mut v = fixture();
    v["trace"]["operations"][1]["expected"] = json!(true);
    cases.push(v);
    let mut v = fixture();
    v["trace"]["operations"][0]["op"] = json!("link");
    cases.push(v);
    let mut v = fixture();
    v["trace"]["initial_edges"] = json!([[0, 1], [0, 1]]);
    cases.push(v);
    let mut v = fixture();
    v["trace"]["operations"][0]["source"] = json!(99);
    cases.push(v);
    let mut v = fixture();
    v["batches"][0]["end"] = json!(1);
    cases.push(v);
    let mut v = fixture();
    v["batches"][1]["time"] = json!(0);
    cases.push(v);
    let mut v = fixture();
    v["node_ids"] = json!(["A", "A", "B"]);
    cases.push(v);
    let mut v = fixture();
    v["provenance"]["source_sha256"] = json!("invalid");
    cases.push(v);
    let mut v = fixture();
    v["schema_version"] = json!(2);
    cases.push(v);
    let mut v = fixture();
    v["surprise"] = json!(1);
    cases.push(v);
    for case in cases {
        let output = run(&case, &[]);
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
        assert!(!output.stderr.is_empty());
    }
}
#[test]
fn generation_flags_cannot_silently_override_imports() {
    for flag in [
        "--nodes",
        "--rounds",
        "--seed",
        "--workload",
        "--query-percent",
    ] {
        let value = if flag == "--workload" {
            "chain-split-rejoin-v1"
        } else {
            "50"
        };
        let output = run(&fixture(), &[flag, value]);
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
    }
}

#[test]
fn rejects_transient_cut_and_relink_inside_one_source_batch() {
    let mut value = fixture();
    value["trace"]["operations"] = json!([
        {"op":"cut","source":0,"target":1},
        {"op":"link","source":0,"target":1},
        {"op":"connected","source":0,"target":1,"expected":true}
    ]);
    value["batches"] = json!([{"time":0,"start":0,"end":3}]);
    let output = run(&value, &[]);
    assert!(
        !output.status.success(),
        "net-zero source changes must not emit kernel mutations"
    );
}

#[test]
fn importing_and_exporting_preserves_exact_bytes() {
    let path =
        std::env::temp_dir().join(format!("knotrel-import-export-{}.json", std::process::id()));
    let bytes = format!(
        " \n{}\n ",
        serde_json::to_string_pretty(&fixture()).unwrap()
    )
    .into_bytes();
    let output = run_bytes(
        &bytes,
        &[
            "--trace-out",
            path.to_str().unwrap(),
            "--query-repeats",
            "1",
            "--warmup",
            "1",
            "--repetitions",
            "2",
        ],
    );
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(std::fs::read(&path).unwrap(), bytes);
    let first: Value = serde_json::from_slice(&output.stdout).unwrap();
    let different = run_bytes(&bytes, &[]);
    assert!(different.status.success());
    let second: Value = serde_json::from_slice(&different.stdout).unwrap();
    assert_eq!(
        first["trace_fingerprint_fnv1a64"],
        second["trace_fingerprint_fnv1a64"]
    );
    assert_eq!(
        first["import"]["provenance"],
        second["import"]["provenance"]
    );
    let again = run_bytes(&bytes, &["--trace-out", path.to_str().unwrap()]);
    assert!(!again.status.success());
    std::fs::remove_file(path).unwrap();
}
