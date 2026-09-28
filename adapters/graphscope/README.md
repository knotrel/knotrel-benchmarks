# Deferred GraphScope experiment

This work was paused at the user's request before running a GraphScope engine.
The Docker image `knotrel-graphscope-probe:0.29.0` was built locally on 2026-09-26
for linux/amd64 on an ARM64 Mac. No container service was launched and there are
no GraphScope timings or equivalence results. Python oracle/helper tests passing
does not validate the live adapter. The Dockerfile resolves transitive Python
packages at build time and is not a complete locked environment.

The prepared probe is experimental and excluded from current competitor results.
It maps u64 IDs to strings and proposes flushing buffered mutations using an edge
count before querying the explicit analytical has_path builtin. Those runtime
assumptions remain unverified. Do not publish or compare its timings until tested.
See the active competitive-landscape document in docs/research for priorities.
