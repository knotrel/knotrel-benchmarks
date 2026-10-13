# Phase 0 independent replication protocol

Declared before collection in response to the renewed 2026-10-12 request.
The [previous attempt](../2026-10-12-initialization-phase0/README.md) failed its
calibration gate and remains intact. This is one complete independent
replication, not replacement of its adverse pair or a retry-until-pass loop.
Do not pool attempts or describe a new pass as invalidating the prior failure.

The validated Rust inputs and all three collector/helper scripts are identical
to the previous attempt. Existing algorithms, public core APIs, workloads,
initialization boundaries and the normal replay runner are unchanged.

Use the [existing fixed collector](../../scripts/run_initialization.py):

1. `calibration`: six adjacent whole/phases pairs per BFS, ETT, HDT on the
   512-vertex dense bridge, three AB/three BA, seeded order; 36 fresh processes.
2. Only if calibration passes, `baseline`: six independent process trials per
   backend on 100k path, 100k cycle, 100k two-component paths, and the 512-vertex
   dense bridge; 72 processes.
3. Only after a successful baseline, `limits`: six default/configured-facade
   pairs per backend on the 100k path; 36 processes.

All runs use seed 42, one generated round, one repetition, no deliberate
warmup, no dynamic replay, one locked release executable per stage, and no
concurrent assistant builds, tests, or analysis during collection. The host is
shared, not exclusive; record load and qualify conclusions accordingly.
Peak RSS is the fresh build-only whole child process, not engine heap.

The unchanged calibration gate requires:

- Absolute median paired setup change <=5% for every backend.
- Each exploratory paired bootstrap 95% interval within [-10%, +10%].
- Maximum setup accounting residual <1%.

Every run must satisfy exact timing accounting and trace identity. Preserve
raw outputs, errors, environment, commands, hashes, and every adverse result.
Stop if calibration fails; do not change thresholds, add repetitions, or run
the broader matrix after failure. No optimization is authorized by this protocol.

Even a pass certifies only coarse phase attribution, not stability for detecting
sub-percent gains. Allocation, root traversal, classification, and AVL work
remain inseparable inside the initial edge interval; state this limitation.
