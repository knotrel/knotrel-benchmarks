# Controlled token-arena preparation diagnostic

Keep the same baseline algorithm and path1M,q90 trace as the phase diagnosis.
Isolated diagnostic only. Touch the initialized HDT forest token arena, not all
process memory or unused vector capacity. Three modes in one binary: none;
read every token's candidate byte through black_box; write back its unchanged
candidate byte through black_box. Token stride is far smaller than a memory page;
this traverses the allocated initialized arena pages while preserving graph state.
Read mode helps distinguish warming from additional writable-page preparation,
but does not perfectly isolate cache effects. Do not claim full graph prefaulting.

Keep external resource snapshots and empty handshake brackets. Add a separately
timed preparation phase after sample-vector allocation and before replay. Record
prepared token count and per-process mode. Setup, preparation, replay all separate;
preparation is not a free optimization. No unsafe Rust or dependency changes.

Three blocks of mode order: none/read/write, read/write/none, write/none/read.
Nine sequential processes, eight fresh-graph replays each, no initial warmup;
small smoke for all modes first. Processes remain independent units; internal
replays are nested. Compare process-mean medians and all process observations,
including preparation+replay cost. No significance or performance gate claims.

Use CPU Mach-time conversion and proc_pidinfo field/ABI validation from the prior
study. Keep original trace/oracle/HDT counters equal for every repetition. Test
state preservation and token recycling directly. Inspect generated code to ensure
write preparation emits a store. Stop after this bounded experiment. No changes
to production core, historical measurements, staging or commits.
