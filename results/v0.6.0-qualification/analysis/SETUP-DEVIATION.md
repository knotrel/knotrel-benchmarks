# Setup deviation (before any measurement)

`prepare_campaign.sh` (frozen at tooling 54dcfc5) stopped at the experiment A
plan step: `prepare_bc_qualification.py` reads its default source manifest from
the harness repository's sibling `evidence/` directory
(`<repo>/../evidence/p0-coverage-increment-1-plan-20261030/manifest.json`), and
the campaign clone at `src/cand/knotrel-benchmarks` had no such sibling.

Fix, applied by hand: symlink `src/cand/evidence` ->
`/Users/rt/workspace/knotrel/evidence` (the documented layout), then run the
script's remaining steps (A plan, A dry-run, binary checksums) with the same
commands. No frozen file, binary or measurement was affected; all builds and
smoke tests had completed before the stop.
