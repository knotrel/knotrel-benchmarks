# GraphScope equivalence and cache-aware measurements

> Implement in this chat, preserving the user's working changes. No commits or pushes.

Goal: establish what a pinned GraphScope configuration can actually execute before
investing in HDT. The user approved a small reproducible comparison and explicitly
asked to account for caches. Core/server behavior remains unchanged.

## Design

Use a separate, isolated GraphScope installation and its explicit analytical
`has_path` function over an undirected dynamic graph. Check source and runtime;
do not claim this path uses Ingress. Use existing trace JSON, independent small
matrix oracle, explicit mutation completion, and repeated same-pair queries that
change answer after deletions/reinsertions. Record installation, version and
architecture; emulated GraphScope is not performance-comparable to native Knotrel.
If the environment or semantics prevents fair timing, deliver the executable
probe and concrete limitation, without fabricating comparative results.

Caches are separate concerns: warm query repeats, invalidation after mutation,
fresh graph, fresh process, and uncontrolled CPU/OS caches. Never label a fresh
process as hardware-cache cold. Do not drop system caches or disable maintained
connectivity state. Timing includes required synchronization. Keep first queries
separate from immediate repeated queries and exclude oracle checks from timers.

## Steps

- [ ] Inspect pinned upstream code and establish isolated executable runtime.
- [ ] Write independent trace/probe tests; implement a small Python adapter with
      JSON reports, cache-invalidation scenarios, and explicit timing boundaries.
- [ ] Execute real GraphScope bridge, cycle, split/rejoin, isolated-node and
      repeated-query probes. Preserve failures and exact environment metadata.
- [ ] Add fresh-process/no-warmup and warmed sampling to the local collection
      script; validate process count, order and metadata without claiming cache flush.
- [ ] Run feasible traces; document supported semantics, Ingress distinction and
      timing comparability, then run Rust/Python checks and review changes.

## Review focus

- Buffered updates charged to the mutation, not silently to the next query.
- Identical query endpoints returning changed answers after a mutation.
- No silent NetworkX fallback or unsupported-width ID conversion.
- No stale executable or interpretation of emulation as native performance.
- Preserve earlier raw measurements; new experiments use new output paths.
