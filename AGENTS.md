# Development requirements

- Use Rust 1.100.0, edition 2024, and this Cargo workspace. The sibling
  `knotrel-core` maintains its separate Rust 1.98.1 MSRV.
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

## Release performance evidence and website

- Maintain the performance website in `docs/`, publishable by GitHub Pages from
  the repository's `/docs` folder. Generate release pages from versioned data;
  never hand-copy measurements into HTML. Run `python3 scripts/build_site.py`
  and `python3 scripts/build_site.py --check` after changing site inputs.
- Start the public release series at **1.0.0**, compared with the latest released
  **0.9.x patch available at campaign freeze**. Record its exact tag and SHA;
  `0.9.x` is a planning placeholder, never a measured binary identity.
- For later releases, select the previous patch in the same minor, the latest
  patch of the previous available minor, the latest patch of the previous major,
  and 1.0.0 for a stable longitudinal workload subset. Resolve references at
  freeze, deduplicate them, and explain missing or incompatible references.
  Historical pages must not silently follow a moving `latest` reference.
- Rerun comparison arms in the same campaign with comparable hardware, resource
  budgets, toolchains/build settings and workload contracts. Historical timings
  from different environments are descriptive, not direct regression estimates.
- Freeze candidate/reference SHAs, binary and trace hashes, backend, protocol,
  environment, seeds, run order, warmup, repetition counts, exclusions, rerun
  rules and analysis before formal measurement. Keep profiling/tuning separate.
- Verify identical graph, query, lifecycle, visibility and atomicity semantics
  with an independent oracle. Classify mismatches as NOT_EQUIVALENT; never hide
  setup, validation, planner or synchronization work needed by only one arm.
- Measure latency p50/p95/p99, successful throughput and offered load, failures,
  timeouts, steady/peak RAM, and CPU time/utilization. Distinguish heap from RSS,
  process from stack totals, CPU percentage conventions and CPU per successful
  operation. Include feeder freshness and backlog recovery where applicable.
- Use independent process runs and balanced/randomized ordering. Declare the
  estimand and confidence-interval method (normally 95%); preserve pairing and
  resample independent runs/blocks, not correlated requests as independent trials.
  A latency percentile is not a confidence interval. Report sample sizes, method,
  uncertainty on absolute estimates and relative differences where supported.
  Missing/unsupported intervals must be explained, never manufactured or zeroed.
- Deterministic allocation counts do not need artificial confidence intervals.
  Tail estimates need adequate observations; label inadequate precision honestly.
  Handle multiple comparisons according to a predeclared policy; an interval
  excluding zero alone is not a practical regression threshold.
- Keep frozen thresholds and analyzer verdicts intact. Show FAIL, REGRESSION,
  INCONCLUSIVE, INVALID, NOT_EQUIVALENT, missing coverage and accepted exceptions
  separately. Acceptance does not turn a failed measurement into PASS. Do not
  infer a release-wide PASS from a subset or silently omit unfavorable cells.
- Publish units, metric direction, absolute values, deltas, confidence intervals,
  run counts, provenance and evidence links. Correct reports through explicit
  revisions that retain previous evidence. Never add fabricated example results
  to the public dataset; planned releases must visibly say no results published.
- Keep competitor campaigns separate from release qualification. Start Neo4j and
  PostgreSQL comparisons after 1.1.0 and any selected profiling optimizations
  (issue #15). Plan a refresh for relevant minor releases or quarterly review,
  without automatically launching expensive benchmarks. Pin competitor versions,
  review queries/configuration, account for durability and freshness differences,
  and report full-stack costs. Do not claim superiority beyond measured scope.
- Website changes require generator/data validation, local-link checks, and
  responsive/accessibility checks. No Rust rebuild is needed for site-only work.
  Do not run performance campaigns or publish/deploy as a side effect of a build.
