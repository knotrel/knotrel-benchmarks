# Paired resource diagnosis of the packed-token regression

Exact flagged trace: path1M,query50,rounds10,seed42,zero warmups,one replay/process.
Reconstruct both saved forest variants with identical phase-marker instrumentation
from the prior scheduling/memory diagnostic. No page preparation or repetitions.
Instrumented binaries differ from original measured binaries; results are separate
and cannot overwrite the original +119.85% regression.

Eight adjacent before/after pairs, balanced4/4 order, pair shuffle42; sixteen
full-size processes plus one small smoke per variant. Read proc_pidinfo task
counters at setup/replay boundaries and empty brackets; calibrate Mach CPU units
and SDK ABI. Preserve all raw counters,timing,mode,compiler/source/binary hashes.

Original workload timer excludes marker handshakes; external wall/CPU/counters
include them. Context switches include voluntary handshake switches. Faults do
not imply disk I/O; pageins separate. RSS is boundary sampled,not peak or token
payload. Sample-vector allocation and teardown are outside these phases.

Report all pairs and phase counters. No causal assertion from correlation,no
outlier removal,no automatic integration. The goal is to see whether the slowdown
reproduces under observation and whether counters suggest memory/CPU waiting costs.
Phase-marker effects and changed code layout remain limitations. No additional
candidate changes,staging or commits.
