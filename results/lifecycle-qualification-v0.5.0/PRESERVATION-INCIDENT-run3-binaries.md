# Preservation incident: run-3 probe binaries overwritten

On 2026-11-16 at about 10:00 local time, a `cargo test --release` of the probes
(after adding the D4 tool) rebuilt `tools/lifecycle-probes/target/release/core-lifecycle`
and `target/release/http-lifecycle`, overwriting the run-3 binaries recorded in
amendment 2 (`b18b551e…` and `b0c55f5b…`). The files now present have different
hashes (`bd21925f…`, `117a4e72…`) and must not be used as run-3 artifacts.

Run-3 raw data, provenance and analysis are unaffected and remain available
(`evidence/v0.5.0-qualification/BC-final-a1d9577/`). The amendment-2 hashes stay
the identity record. A future rebuild from probes `444806d3` and knotrel `a1d9577`
is not a recovery of the same binaries unless its hashes equal those values.
The count-alloc binary (`target-count`, `53497c21…`) was not overwritten.
