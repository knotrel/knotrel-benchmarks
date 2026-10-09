# Scheduling and memory phase diagnosis

Isolated baseline-only diagnostic build, from the frozen source snapshot. Do not
change the algorithm. Add synchronous markers at setup/replay boundaries; external
Python reads proc_pidinfo(PROC_PIDTASKINFO) for its owned child, then acknowledges.
No unsafe Rust, new crate dependency, affinity change or system setting change.

Four processes (two nominal A/A pairs, alternating labels), path1M,q90, seed42,
10 rounds, zero initial warmup, eight fresh-graph repetitions/process. This is a
resource investigation, not an A/B performance ranking. Match trace fingerprint,
expected results and HDT counters with the frozen reference. Run an empty marker
interval before each setup and after each replay to quantify handshake activity.
Snapshots bound setup and replay separately. Store all raw counters and times.

Parent-observed elapsed intervals and task CPU deltas include communication and
scheduling at boundaries; original workload_wall_ns excludes the marker handshake.
Do not subtract empty-interval medians to invent unperturbed timings or exact CPU
waiting percentages. Context-switch count includes voluntary and involuntary
switches; the handshake creates switches itself. Page faults include faults that
do not require disk I/O; pageins are distinct. RSS is at boundaries, not peak or
allocator payload. No cache-miss or core-migration counters are available here.

Check native ABI size using installed SDK, and validate CPU time units against a
CPU-work calibration. Preserve source patch and binary/compiler hashes. Phase
correlations are descriptive with nested replay observations, not causal proof.
Stop after this bounded collection; do not tune measurements to force stability.
