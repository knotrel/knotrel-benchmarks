# Copilot Instructions for Knotrel-Benchmarks

When modifying or generating code for `knotrel-benchmarks`, strictly adhere to the following principles and project requirements:

## 1. Environment & Architecture
- Rust edition 2024 with pinned toolchain `1.98.1` (`rust-toolchain.toml`).
- Keep the sibling `knotrel` checkout for the local core path dependency (`../knotrel/crates/knotrel-core`). Record both revisions and dirty state with results.
- Respect workspace lints: `missing_docs = "deny"`, `unsafe_code = "forbid"`, `clippy::all = "warn"`, and `rustdoc::broken_intra_doc_links = "deny"`.

## 2. Benchmark Rigor & Invariants
- Use deterministic workloads and independent expected answers.
- Keep setup, verification, and correctness checks strictly outside timed operation intervals.
- Never infer external engine performance (e.g. GraphScope) without an implemented adapter and identical graph/query/visibility semantics.
- Preserve reproducible random seeds and explicit parameterizations (`--nodes`, `--rounds`, `--seed`).

## 3. Quality Assurance
- Ensure the following checks pass cleanly without warnings:
  - `cargo fmt --all -- --check`
  - `cargo clippy --workspace --all-targets --locked -- -D warnings`
  - `cargo test --workspace --locked`
  - `cargo doc --workspace --no-deps --locked` (with `RUSTDOCFLAGS="-D warnings"`)
- Document all public items with docstrings explaining invariants, benchmark configurations, and time/space complexity bounds.

## 4. Git & Rulesets Conventions
- **Branches**: Must match `^(feature|bugfix|fix|hotfix|docs|chore|refactor|test|ci|dependabot)/.+$`
- **Commits**: Must follow Conventional Commits: `^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9_./-]+\))?!?: .+$`
