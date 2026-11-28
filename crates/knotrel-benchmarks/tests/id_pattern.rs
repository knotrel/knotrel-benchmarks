//! `--id-pattern`: default output unchanged, mapped traces replay on the K4
//! engines against the oracle, and the fingerprint covers the mapped IDs.

use knotrel_benchmarks::IdPattern;
use serde_json::Value;
use std::collections::BTreeSet;
use std::process::{Command, Output};

/// The engines whose ID maps knotrel#210 changed (plan section 14.6).
const K4_ENGINES: &str = "connectivity-compact-bfs,compact-workspace,connectivity-ett,connectivity-hdt,connectivity-cluster-forest";

fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_knotrel-benchmarks"))
        .args(args)
        .output()
        .unwrap()
}

fn report(args: &[&str]) -> Value {
    let output = run(args);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

fn fnv1a64(bytes: &[u8]) -> String {
    let hash = bytes.iter().fold(0xcbf29ce484222325_u64, |hash, byte| {
        (hash ^ u64::from(*byte)).wrapping_mul(0x100000001b3)
    });
    format!("{hash:016x}")
}

#[test]
fn default_and_explicit_sequential_keep_pre_option_fingerprints_and_fields() {
    // Fingerprints recorded with the harness before --id-pattern existed
    // (knotrel-benchmarks a5d10a88). The first case is the K1/K4 sustained trace.
    let cases: [(&[&str], &str); 3] = [
        (
            &[
                "--workload",
                "sustained-churn-blocks-v1",
                "--nodes",
                "10000",
                "--rounds",
                "20",
                "--seed",
                "42",
            ],
            "949e4d2f696e64e7",
        ),
        (
            &[
                "--workload",
                "sustained-churn-blocks-v1",
                "--nodes",
                "64",
                "--rounds",
                "4",
                "--seed",
                "42",
            ],
            "af64cc018791a004",
        ),
        (
            &["--nodes", "64", "--rounds", "4", "--seed", "42"],
            "b433ea4f48d14f0d",
        ),
    ];
    let legacy_keys: BTreeSet<&str> = [
        "arch",
        "benchmark_version",
        "checkouts_at_run_time",
        "compiler",
        "config",
        "debug_assertions",
        "engine",
        "initial_density",
        "initial_edges",
        "initial_max_degree",
        "os",
        "query_percent",
        "query_repeats",
        "repetitions",
        "schema_version",
        "timestamp_unix_seconds",
        "trace_fingerprint_fnv1a64",
        "warmup",
        "workload",
    ]
    .into();
    for (generation, fingerprint) in cases {
        for explicit in [false, true] {
            let mut args = generation.to_vec();
            args.extend([
                "--engine",
                "connectivity-compact-bfs",
                "--warmup",
                "0",
                "--repetitions",
                "1",
            ]);
            if explicit {
                args.extend(["--id-pattern", "sequential"]);
            }
            let report = report(&args);
            assert_eq!(report["trace_fingerprint_fnv1a64"], fingerprint);
            let keys: BTreeSet<&str> = report
                .as_object()
                .unwrap()
                .keys()
                .map(String::as_str)
                .collect();
            assert!(keys.is_subset(&legacy_keys), "{keys:?}");
            assert!(report.get("id_pattern").is_none());
        }
    }
}

#[test]
fn every_pattern_replays_on_every_k4_engine_with_distinct_fingerprints() {
    let mut fingerprints = BTreeSet::new();
    let mut counts = None;
    for pattern in IdPattern::ALL {
        let report = report(&[
            "--workload",
            "sustained-churn-blocks-v1",
            "--nodes",
            "200",
            "--rounds",
            "6",
            "--seed",
            "42",
            "--warmup",
            "1",
            "--repetitions",
            "1",
            "--engine",
            K4_ENGINES,
            "--id-pattern",
            pattern.name(),
        ]);
        let comparisons = report["comparisons"].as_array().unwrap();
        assert_eq!(comparisons.len(), 5);
        let fingerprint = &comparisons[0]["trace_fingerprint_fnv1a64"];
        for comparison in comparisons {
            // A failed oracle check aborts the run, so success means every
            // link, cut and query answer matched with the mapped IDs.
            assert_eq!(&comparison["trace_fingerprint_fnv1a64"], fingerprint);
            if pattern == IdPattern::Sequential {
                assert!(comparison.get("id_pattern").is_none());
            } else {
                assert_eq!(comparison["id_pattern"], pattern.name());
            }
            // Degrees are counted on vertex indices, before mapping.
            assert_eq!(comparison["initial_max_degree"], 3);
            let run = &comparison["repetitions"][0]["measurements"];
            let these = (
                run["cut"]["count"].clone(),
                run["link"]["count"].clone(),
                run["connected"]["count"].clone(),
            );
            assert_eq!(counts.get_or_insert_with(|| these.clone()), &these);
        }
        assert!(fingerprints.insert(fingerprint.as_str().unwrap().to_owned()));
    }
    assert_eq!(fingerprints.len(), 4);
}

#[test]
fn exported_trace_holds_mapped_ids_and_is_the_fingerprint_input() {
    let directory = std::env::temp_dir().join(format!("knotrel-idp-{}", std::process::id()));
    std::fs::create_dir_all(&directory).unwrap();
    for pattern in [IdPattern::Random, IdPattern::Shl16, IdPattern::Shl32] {
        let path = directory.join(format!("{}.json", pattern.name()));
        let _ = std::fs::remove_file(&path);
        let report = report(&[
            "--workload",
            "sustained-churn-blocks-v1",
            "--nodes",
            "100",
            "--rounds",
            "3",
            "--engine",
            "connectivity-hdt",
            "--warmup",
            "0",
            "--id-pattern",
            pattern.name(),
            "--trace-out",
            path.to_str().unwrap(),
        ]);
        let bytes = std::fs::read(&path).unwrap();
        assert_eq!(report["trace_fingerprint_fnv1a64"], fnv1a64(&bytes));
        let trace: Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(trace["id_pattern"], pattern.name());
        let allowed: BTreeSet<u64> = (0..100).map(|i| pattern.id(i)).collect();
        assert_eq!(allowed.len(), 100);
        let mut seen = BTreeSet::new();
        for edge in trace["trace"]["initial_edges"].as_array().unwrap() {
            seen.insert(edge[0].as_u64().unwrap());
            seen.insert(edge[1].as_u64().unwrap());
        }
        for operation in trace["trace"]["operations"].as_array().unwrap() {
            seen.insert(operation["source"].as_u64().unwrap());
            seen.insert(operation["target"].as_u64().unwrap());
        }
        assert!(seen.is_subset(&allowed));
        // The initial path touches every vertex.
        assert_eq!(seen.len(), 100);
        std::fs::remove_file(&path).unwrap();
    }
    std::fs::remove_dir(&directory).unwrap();
}

#[test]
fn random_pattern_is_the_fixed_splitmix64_bijection() {
    // splitmix64's first output for state 0 (Vigna's reference generator).
    assert_eq!(IdPattern::Random.id(0), 0xe220a8397b1dcdaf);
    let ids: BTreeSet<u64> = (0..100_000).map(|i| IdPattern::Random.id(i)).collect();
    assert_eq!(ids.len(), 100_000);
    assert_eq!(IdPattern::Shl16.id(3), 3 << 16);
    assert_eq!(IdPattern::Shl32.id(3), 3 << 32);
    assert_eq!(IdPattern::Sequential.id(3), 3);
}

#[test]
fn overflowing_unknown_and_imported_patterns_are_rejected_before_output() {
    assert!(IdPattern::Shl32.check_nodes(1 << 32).is_ok());
    assert!(IdPattern::Shl32.check_nodes((1 << 32) + 1).is_err());
    assert!(IdPattern::Shl16.check_nodes(1 << 48).is_ok());
    assert!(IdPattern::Shl16.check_nodes((1 << 48) + 1).is_err());
    assert!(IdPattern::Random.check_nodes(u64::MAX).is_ok());
    for (args, message) in [
        (
            &[
                "--workload",
                "sustained-churn-blocks-v1",
                "--nodes",
                "4294967297",
                "--id-pattern",
                "shl32",
            ][..],
            "overflows",
        ),
        (
            &["--nodes", "281474976710657", "--id-pattern", "shl16"][..],
            "overflows",
        ),
        (&["--id-pattern", "shl8"][..], "unknown id pattern"),
        (&["--id-pattern"][..], "needs a value"),
        (
            &["--trace-in", "unused.json", "--id-pattern", "shl32"][..],
            "--trace-in accepts only",
        ),
    ] {
        let output = run(args);
        assert!(!output.status.success(), "{args:?}");
        assert!(output.stdout.is_empty());
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(stderr.contains(message), "{args:?}: {stderr}");
    }
}
