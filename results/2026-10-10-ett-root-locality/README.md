# ETT root access locality and query code diagnosis

**No changed root access pattern was found on the million-vertex path.** All eight
runs have identical logical token sequences and page-relative parent-field address
sequences: before/after, fresh/warmed, two repeats each. This rules out a change in
this measured access pattern; it does not establish equal hardware cache behavior.
Production code remains unchanged and the root-reuse candidate remains isolated.

## Access tracing

| Root-parent metric | Every run |
|---|---:|
| Reads, including terminal root reads | 32,739 |
| Distinct tokens | 23,267 |
| Distinct virtual 128-byte lines | 21,899 |
| Distinct virtual 16-KiB pages | 5,683 |
| Line transitions in complete sequence | 32,737 |
| Page transitions in complete sequence | 19,910 |

The spread across thousands of pages makes memory locality worth investigating,
but is not a cache/TLB miss measurement. The same footprint occurs in both variants.
Root accesses are only part of the operation: this probe does not trace hash-map
lookups, AVL mutation accesses, physical pages, residency, prefetching or CPU placement.
Transitions include boundaries between separate root calls. No instrumented time
is used to assess performance.

[Comparison](comparison.json), [protocol](protocol.md), [raw traces and checks](manifest.json).
The recorder starts after graph construction and stops after the original replay
loop. It saves no absolute arena address, only page-relative positions. Its own
allocations and instrumentation perturb the process; conclusions are structural.
Host page and line sizes were read with sysctl, not assumed from product branding.

## Original uninstrumented query disassembly

The [assembly audit](assembly-audit.json) uses the hash-verified original pilot
binaries, not the traced builds. Relative branch destinations are normalized;
other operands are retained. Saved raw disassembly makes the comparison reviewable.

- `ForestGraph::connected`: 91 instructions, identical after normalization.
- `GenericForest<bool>::connected`: 51 instructions; the prefix through the normal
  return is identical. Two later immediate operands differ in bounds-panic metadata
  address construction; the corresponding panic-call symbols are unchanged.
- Both functions move by 16 bytes in the candidate binary.

Thus this inspection finds no extra instructions in the normal query paths.
The code-address shift could affect instruction-cache alignment, but it does not
prove that it caused any observed timing difference. Cut and the rest of the
binary are outside this assembly comparison. Bounds-error paths are not the
successful path workload and are not claimed byte-identical.

## Tooling limitation and conclusion

Only CommandLineTools is selected; `xcrun xctrace list templates` fails because
Xcode Instruments is unavailable. See [tool availability](tool-availability.txt).
No hardware counters or CPU-core placement measurements were obtained. Generic
stack sampling was not used as a substitute: setup dominates process lifetime
and the actual replay is only a few milliseconds.

Together with the earlier CPU diagnosis, these results narrow the issue:
abstract root work, its virtual access order and the inspected normal query code
are unchanged; CPU timing still varies. Cache residency, physical placement,
CPU frequency/core placement and instruction alignment remain untested causes.
Do not label the regression fixed or blame a specific one of these mechanisms.

A stronger attribution now needs replay-scoped hardware profiling on a host with
Instruments or an equivalent profiler available. Installing a full development
environment was not part of this experiment. Keep the original regression and
all subsequent measurements; avoid further identical timing reruns or speculative
core changes merely to make the median favorable.

## Validation and reproduction

Eight successful oracle-checked replays; identical answers/counts/forest stats and
trace fingerprints across variants. Logical and page-relative sequences were
compared exactly, not just by aggregate counts. Formatting, Clippy with warnings
denied, core and benchmark package tests/doctests, and Rustdoc checks passed in the
isolated workspaces. Existing server tests were not rerun for this diagnostic.
No new dependencies or unsafe code were introduced.

`run.py` preserves build commands, source snapshots, binaries' hashes and all runs;
`analyze.py` checks frozen artifacts and sequences. `assembly.py` reproduces the
uninstrumented disassembly comparison. The original pilot source audit still passes.
