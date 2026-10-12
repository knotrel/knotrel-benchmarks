# Hardware profiling handoff: blocked on Instruments availability

The read-only [preflight](preflight.py) checks xctrace in the selected developer
location and Xcode installations under /Applications and ~/Applications, without
changing the system developer selection. It also verifies the original frozen
before/after binary hashes. [Current readiness](readiness.json).

On this host, only CommandLineTools is selected and xctrace is unavailable.
Spotlight also returned no installed Xcode application. Frozen binaries are ready;
no hardware recording has been made. The earlier regression remains unresolved.

## Prerequisite

Install a macOS-compatible full Xcode from Apple's
[official downloads](https://developer.apple.com/xcode/resources/), open it and
complete its first-run setup. Instruments is part of Xcode. No paid Developer
Program membership is required to download Xcode. Account authentication or
license acceptance, if presented by Apple, belongs to the user.

Then run `python3 preflight.py` from this directory. An Xcode installation can be
selected for these subprocesses with DEVELOPER_DIR without a global xcode-select
change. Actual template names and recording options must be checked against the
installed xctrace version; do not assume a template exists from its marketing name.

## Collection plan once ready

1. Preserve the original hashes, trace and oracle semantics. Use the fresh/warmed
   million-vertex path and dense positive control. Declare a fixed paired budget
   before collecting; separate diagnostic recordings from acceptance benchmarks.
2. Establish replay boundaries in a separately built diagnostic harness using a
   profiler-supported marker. Validate that graph setup and destruction lie outside
   the selected interval. Do not interpret a whole-process profile as a replay
   profile, or enlarge rounds silently to make sampling easier.
3. Discover available hardware counters and core/frequency tracks. Capture the
   supported subset and document unavailable events. Do not call virtual-page
   counts hardware cache misses. A millisecond-scale interval may have insufficient
   samples: report that limitation rather than infer a cause from zero samples.
4. Use process-scoped sleep inhibition, inspect power events, retain all failures
   and adverse pairs. Verify trace answers and compare marked-region measurements.
5. Diagnose memory stalls, core placement/frequency or instruction alignment only
   where collected evidence supports it. No automatic core integration follows.

Current evidence: the dense benefit is repeatable; path root access sequences and
inspected normal query code agree, but CPU time varies. Previous reports remain
unchanged. No new timing campaign is useful until the missing profiler is available.
