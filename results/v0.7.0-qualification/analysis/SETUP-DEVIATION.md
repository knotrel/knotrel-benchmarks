# Setup deviation (before any measurement)

`prepare_campaign.sh` (frozen at tooling 82123ae3, freeze 4c03cf7b) stopped at
the experiment A plan step for the reason already recorded in v0.6.0
(`results/v0.6.0-qualification/analysis/SETUP-DEVIATION.md`):
`prepare_bc_qualification.py` reads its default source manifest from the
harness repository's sibling `evidence/` directory, and the campaign clone at
`src/cand/knotrel-benchmarks` has no such sibling. The v0.7.0 script was
copied from v0.6.0 without that fix.

Fix, applied by hand exactly as in v0.6.0: symlink `src/cand/evidence` ->
`/Users/rt/workspace/knotrel/evidence`, then run the script's remaining steps
(A plan, A dry-run, binary checksums) with the same commands. The failed
attempt's log is kept as `A-plan-attempt1-failed.log`. No frozen file, binary
or measurement was affected; all builds and both release-binary smoke tests
had completed before the stop.
