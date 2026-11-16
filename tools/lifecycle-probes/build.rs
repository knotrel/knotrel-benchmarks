//! Embeds the linked knotrel checkout's revision and dirty state, so every
//! probe run reports the exact source it measured.

use std::process::Command;

fn git(args: &[&str]) -> String {
    Command::new("git")
        .args(["-C", "../../../knotrel"])
        .args(args)
        .output()
        .ok()
        .filter(|output| output.status.success())
        .map(|output| String::from_utf8_lossy(&output.stdout).trim().to_owned())
        .unwrap_or_else(|| "unknown".to_owned())
}

fn bench_git(args: &[&str]) -> String {
    Command::new("git")
        .args(["-C", "../.."])
        .args(args)
        .output()
        .ok()
        .filter(|output| output.status.success())
        .map(|output| String::from_utf8_lossy(&output.stdout).trim().to_owned())
        .unwrap_or_else(|| "unknown".to_owned())
}

fn main() {
    println!("cargo:rerun-if-changed=src");
    println!(
        "cargo:rustc-env=PROBES_REV={}",
        bench_git(&["rev-parse", "HEAD"])
    );
    let probes_dirty = bench_git(&["status", "--porcelain", "--", "tools/lifecycle-probes"]);
    println!("cargo:rustc-env=PROBES_DIRTY={}", !probes_dirty.is_empty());
    for path in [
        "HEAD".to_owned(),
        bench_git(&["symbolic-ref", "-q", "HEAD"]),
    ] {
        let resolved = bench_git(&["rev-parse", "--path-format=absolute", "--git-path", &path]);
        if resolved != "unknown" {
            println!("cargo:rerun-if-changed={resolved}");
        }
    }
    println!("cargo:rerun-if-changed=../../../knotrel/crates");
    println!("cargo:rerun-if-changed=../../../knotrel/Cargo.lock");
    // Re-run when HEAD or the checked-out branch moves (also for commits that
    // change no source file); the collector additionally checks the revision.
    for path in ["HEAD".to_owned(), git(&["symbolic-ref", "-q", "HEAD"])] {
        let resolved = git(&["rev-parse", "--path-format=absolute", "--git-path", &path]);
        if resolved != "unknown" {
            println!("cargo:rerun-if-changed={resolved}");
        }
    }
    println!(
        "cargo:rustc-env=KNOTREL_REV={}",
        git(&["rev-parse", "HEAD"])
    );
    let dirty = git(&[
        "status",
        "--porcelain",
        "--",
        "crates",
        "Cargo.toml",
        "Cargo.lock",
    ]);
    println!("cargo:rustc-env=KNOTREL_DIRTY={}", !dirty.is_empty());
}
