//! End-to-end checks of the binary on small inputs: one JSON object on
//! stdout, correct answers, stable fingerprints, and the field set the
//! analyzers read.

use std::process::Command;

fn run(args: &[&str]) -> (i32, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_query-shape-probe"))
        .args(args)
        .output()
        .expect("run query-shape-probe");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8(out.stdout).expect("utf-8 stdout"),
    )
}

/// The raw JSON text of `key`'s value (scalars and flat objects only).
fn field<'a>(json: &'a str, key: &str) -> &'a str {
    let pat = format!("\"{key}\":");
    let start = json
        .find(&pat)
        .unwrap_or_else(|| panic!("no {key} in {json}"))
        + pat.len();
    let rest = &json[start..];
    let end = if rest.starts_with('{') {
        rest.find('}').expect("object end") + 1
    } else {
        rest.find([',', '}']).expect("value end")
    };
    &rest[..end]
}

#[test]
fn shapes_answer_correctly_with_stable_fingerprints() {
    for shape in ["s1", "s2", "l1", "l2", "l3"] {
        let args = [
            "shape",
            "--shape",
            shape,
            "--threads",
            "3",
            "--vertices",
            "2000",
            "--queries",
            "50",
        ];
        let (code, out) = run(&args);
        assert_eq!(code, 0, "{shape}: {out}");
        assert_eq!(out.trim().lines().count(), 1, "{out}");
        assert!(out.trim().starts_with('{') && out.trim().ends_with('}'));
        for key in [
            "tool",
            "mode",
            "shape",
            "threads",
            "vertices",
            "queries_per_thread",
            "queries_timed",
            "latency_ns",
            "wrong_answers",
            "allocations_per_query",
            "input_fingerprint_fnv1a64",
        ] {
            field(&out, key);
        }
        assert_eq!(field(&out, "wrong_answers"), "0");
        assert_eq!(field(&out, "queries_timed"), "150");
        assert!(field(&out, "latency_ns").contains("\"p99\":"));
        let (_, again) = run(&args);
        assert_eq!(
            field(&out, "input_fingerprint_fnv1a64"),
            field(&again, "input_fingerprint_fnv1a64")
        );
        let mut other = args;
        other[4] = "4";
        let (_, more) = run(&other);
        assert_ne!(
            field(&out, "input_fingerprint_fnv1a64"),
            field(&more, "input_fingerprint_fnv1a64")
        );
    }
}

#[test]
fn sequence_reports_retained_bytes_and_allocations() {
    let args = [
        "sequence",
        "--kind",
        "large-then-small",
        "--threads",
        "2",
        "--chain-vertices",
        "20000",
        "--vertices",
        "2000",
        "--small-queries",
        "300",
    ];
    let (code, out) = run(&args);
    assert_eq!(code, 0, "{out}");
    assert_eq!(field(&out, "wrong_answers"), "0");
    for key in [
        "retained_after_large_bytes",
        "retained_after_small_bytes",
        "small_allocations_after_100",
        "small_latency_ns",
    ] {
        let v = field(&out, key);
        assert!(v.starts_with('{'), "{key}: {v}");
    }
    assert!(field(&out, "retained_after_small_bytes").contains("\"median\":"));
    assert!(field(&out, "small_allocations_after_100").contains("\"total\":"));
    let (_, again) = run(&args);
    assert_eq!(
        field(&out, "input_fingerprint_fnv1a64"),
        field(&again, "input_fingerprint_fnv1a64")
    );
}

#[test]
fn usage_errors_exit_1_without_stdout() {
    for args in [
        &["shape", "--shape", "s9", "--threads", "1"][..],
        &["shape", "--threads", "1"][..],
        &["sequence", "--kind", "other", "--threads", "1"][..],
        &["bogus"][..],
    ] {
        let (code, out) = run(args);
        assert_eq!(code, 1, "{args:?}");
        assert!(out.is_empty(), "{args:?}: {out}");
    }
}

#[test]
fn wrong_answers_print_json_and_exit_2() {
    for args in [
        &[
            "shape",
            "--shape",
            "l3",
            "--threads",
            "2",
            "--vertices",
            "500",
            "--queries",
            "10",
        ][..],
        &[
            "sequence",
            "--kind",
            "large-then-small",
            "--threads",
            "2",
            "--chain-vertices",
            "1000",
            "--vertices",
            "500",
            "--small-queries",
            "20",
        ][..],
    ] {
        let out = Command::new(env!("CARGO_BIN_EXE_query-shape-probe"))
            .args(args)
            .env("QSP_TEST_CORRUPT_EXPECTED", "1")
            .output()
            .expect("run query-shape-probe");
        let stdout = String::from_utf8(out.stdout).expect("utf-8");
        assert_eq!(out.status.code(), Some(2), "{args:?}: {stdout}");
        assert_eq!(field(&stdout, "wrong_answers"), "1", "{stdout}");
    }
}
