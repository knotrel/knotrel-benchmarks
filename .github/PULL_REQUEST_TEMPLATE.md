## Summary

<!-- Brief summary of what this PR does and why. -->

Fixes # <!-- Issue number if applicable -->

## Type of Change

- [ ] `feat`: New benchmark scenario, adapter, or harness capability
- [ ] `fix`: Bug fix in harness, generator, or adapter logic
- [ ] `perf`: Harness execution optimization or memory reduction
- [ ] `docs`: Documentation updates or benchmark methodology notes
- [ ] `test`: New test cases or test refactoring
- [ ] `refactor`: Code reorganization without behavior change
- [ ] `ci`: CI/CD workflows, build scripts, or tooling

## Affected Components

- [ ] `crates/knotrel-benchmarks` (Core benchmark harness and CLI)
- [ ] `adapters` (Engine adapters / comparison harnesses)
- [ ] `scripts` (Execution and analysis scripts)
- [ ] `results` (Benchmark outputs, charts, or summaries)
- [ ] Workflows / Documentation

## Benchmark Rigor & Invariants

<!-- If modifying benchmarks or adding workloads:
- Are workloads deterministic with explicit seeds?
- Are setup and verification steps strictly excluded from timed intervals?
- Does this maintain identical graph/query/visibility semantics across compared engines?
-->

## Verification Checklist

- [ ] Pinned toolchain: Built and tested with Rust `1.98.1`
- [ ] Tests pass: `cargo test --workspace --locked`
- [ ] Formatted: `cargo fmt --all -- --check`
- [ ] Clippy clean: `cargo clippy --workspace --all-targets --locked -- -D warnings`
- [ ] Documentation updated: Exported items documented and `cargo doc --workspace --no-deps --locked` clean
- [ ] Release smoke test: `cargo run --release --locked -- --nodes 128 --rounds 10 --seed 42`
