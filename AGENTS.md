# Development requirements

- Use Rust 1.98.1, edition 2024, and this Cargo workspace.
- Write code, comments, docs and reports in English.
- Document every public item; explain nontrivial algorithms, invariants and time/space bounds.
- Inherit workspace lints; missing Rustdoc is an error. Do not introduce unsafe code.
- Keep the sibling `knotrel` checkout for the local core path dependency. Record both revisions and dirty state with results.
- Preserve Cargo.lock and the existing Apache-2.0 license.
- Use deterministic workloads and independent expected answers. Keep setup and correctness checks outside timed operation intervals.
- Never infer GraphScope performance from this harness: a comparison needs an implemented adapter and identical graph/query/visibility semantics.
- Verify formatting, Clippy with warnings denied, tests/doctests and Rustdoc with warnings denied.
- Do not commit or push unless the user explicitly asks for it.

## Git & Naming Rulesets

- **Branch Naming**: All branches must follow the pattern:
  `^(feature|bugfix|fix|hotfix|docs|chore|refactor|test|ci|dependabot)/.+$`
  Allowed prefixes: `feature/`, `bugfix/`, `fix/`, `hotfix/`, `docs/`, `chore/`, `refactor/`, `test/`, `ci/`, `dependabot/`.
- **Commit Messages**: All commits and PR titles must follow Conventional Commits matching:
  `^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9_./-]+\))?!?: .+$`
  Examples: `feat(bench): add HDT profile`, `fix(adapter): handle disconnected components`, `chore: update dependencies`.
