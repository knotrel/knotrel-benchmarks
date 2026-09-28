# Published benchmark results and local traces

Git retains the per-run measurement JSON, stderr logs (including process RSS),
summary CSVs, reports, original manifests/audits, collector snapshots, patches
and captured Rust sources. These are evidence, not disposable caches.

Large `*.trace.json` exports are ignored and removed from the index, but remain
unchanged on the collecting machine. [Trace inventory](local-traces.json)
records their paths, original byte sizes and SHA-256 hashes. No external archive
has been published; a fresh clone does not contain these exports.

Original manifests and audit records are preserved without rewriting their
historical hashes. An audit that checks **every** manifest artifact requires the
local trace exports as well as the committed files. The recorded successful
full audits describe the original collection, not a claim that a fresh clone
contains every artifact. Timing summaries can be recalculated from committed
per-run JSON without the traces. Retained stderr logs support RSS checks.

To reconstruct a trace, use the matching captured source version and the
workload/configuration/seed recorded in that collection's manifest and per-run
JSON. Use the runner's `--trace-out` option with a new output path; it refuses to
overwrite an existing file. Adjust original absolute checkout/output paths for
your machine. Compare the resulting bytes with the SHA-256 in local-traces.json
(and the original manifest when present). Do not assume the current generator
matches every historical version. Reconstruction replays the workload; it does
not reproduce historical timing values or machine state. Older collection
metadata may require manual reconstruction of the captured dirty checkout.

Publication policy: keep compact measurements and provenance in Git; preserve
bulky trace exports locally or distribute them as separately managed artifacts.
Never add trace exports with `git add -f` as part of routine result publication.
Python caches are ignored throughout both repositories.

`.gitattributes` disables line-ending conversion for result artifacts to preserve
the recorded hashes. Patch context spaces and CSV CRLF terminators are retained
intentionally; targeted whitespace rules keep Git checks meaningful elsewhere.
