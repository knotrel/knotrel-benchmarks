//! Captures the actual build compiler for reproducible benchmark reports.

use std::{env, process::Command};

fn main() {
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-env-changed=RUSTC");
    let compiler = Command::new(env::var_os("RUSTC").expect("Cargo provides RUSTC"))
        .arg("--version")
        .output()
        .expect("compiler version is available");
    assert!(
        compiler.status.success(),
        "could not query compiler version"
    );
    let compiler = String::from_utf8(compiler.stdout).expect("compiler version is UTF-8");
    println!(
        "cargo::rustc-env=KNOTREL_BUILD_COMPILER={}",
        compiler.trim()
    );
}
