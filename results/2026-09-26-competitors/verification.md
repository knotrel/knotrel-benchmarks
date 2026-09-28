# Verification — 2026-09-27

Both workspaces passed formatting, Clippy with warnings denied, locked workspace
tests/doctests, Rustdoc with warnings denied and git diff whitespace checks.
The benchmark workspace passed 12 Rust tests; the core/server workspace passed
13 tests plus one doctest. All eight Python helper/protocol tests passed.

Verified 198 artifact hashes, 25 source hashes, 1152 backend repetitions and 96 summary rows. Collector checksum also matches.
All four backends in every report share a trace fingerprint; immediate-repeat
counts match original query counts. Summary CSV matches recomputation from raw
reports.

Independent code review found no material adapter or timing defect. Its
methodology documentation findings (setup timing, schema 3 and augmented query
ratios) were corrected. Reference setup includes an unused ID-map construction;
setup values include this harness overhead. No production core code was changed.
No commits or pushes were made.
