# v0.5.0 qualification evidence — inventory and preservation

Generated 2026-11-16. Covers the raw evidence cited by
`results/lifecycle-qualification-v0.5.0/` (knotrel-benchmarks) and by the knotrel
v0.5.0 release notes.

## What is preserved

- **Raw evidence:** every regular file under `evidence/v0.5.0-dev/`,
  `evidence/v0.5.0-qualification/` and `evidence/v0.5.0-remediation/`, except
  the regenerable trees listed below: **8,663 files, 45.7 MiB**. Includes the
  raw JSONL of every run (B/C runs 1-4, pilots 1-6, D1-D5), experiment-A raw
  pairs, plans, identities, analyses, logs, validation logs and summaries,
  startup-test reproduction logs, protocols' working copies and reports.
- **Measured executables (30):** the A-campaign B/C servers, harnesses and
  `measure_e2e` of every campaign, and the probe executables of runs 3-4 and
  D4/D5, each with its SHA-256 (all equal the hashes recorded in
  `identities.json` files and in the protocol amendments).
- `MANIFEST.sha256`: SHA-256 and relative path of all 8,663 files and the 30
  executables (sha256 `4c30bf09aa93d98c6a50eaab04a86111015306ae600d61db7f875925537e3adb`).
- `inventory.json`: counts, bytes, per-directory listing digests (69
  directories), executable hashes and the excluded trees.

## Not preserved (regenerable, excluded from the archives)

18 trees, about 9 GB: A-campaign `targets/` (build trees; the final measured
executables are preserved separately), `sources/` (git clones of recorded
commits), validation `pkg-checkout/` and `checkout/` (clones of recorded
commits) and `cargo-home/` (downloaded crates.io dependencies, reproducible
from the lockfiles). Earlier probe binaries of run 3 in
`tools/lifecycle-probes/target/release/` were overwritten (see
`PRESERVATION-INCIDENT-run3-binaries.md`); their hashes remain the record.

## Archives prepared locally (not yet in durable storage)

| Archive | Size | SHA-256 |
|---|---|---|
| `knotrel-v0.5.0-evidence.tar.gz` (raw evidence + manifest + inventory) | 27,398,770 B | `13e136056d20ee96fcfb534819e1ac10fc85238a54b56b5e8af2dcd0e4c5dce7` |
| `knotrel-v0.5.0-measured-executables.tar.gz` (30 executables) | 24,016,232 B | `b717703c9abaf9d7bff1392e1c8435bee345db316f65953e57d0ad2d2ddbce53` |

Location: `/Users/rt/workspace/knotrel/evidence/v0.5.0-MANIFEST/` on the
qualification host only.

## Report links

All `evidence/v0.5.0-*` paths cited in the benchmarks result reports, the
remediation reports and the knotrel release notes resolve to existing files or
directories (21 distinct paths; the only unmatched string is the `D1-<label>`
naming template in `D1-PLAN.md`).

## Sensitive-data check (before any transfer)

An automated scan of all 8,663 evidence files and the 30 executables found no
credentials: no GitHub, AWS, crates.io or Slack tokens, private keys, bearer
headers, password assignments or e-mail addresses (the only e-mail-shaped
match, `h@i.Bm`, is byte noise inside a binary). Files contain absolute paths
of the qualification host, including the local user name `rt`
(`/Users/rt/workspace/knotrel/...`, 1,783 files); this is not a credential and
the originals were not modified. Keep the archives private.

## Durable destination — OPEN (authorization needed before merge)

No project-owned storage is configured: the `knotrel` GitHub organization
(free plan) has only the two public repositories, and no storage bucket,
archive service or release-asset convention is documented in either
repository.

**Proposal (not created):** a dedicated **private** repository
`knotrel/knotrel-qualification-evidence`, owned by the `knotrel` organization
(the session's account is an organization admin; members may create private
repositories), holding:

- `v0.5.0/knotrel-v0.5.0-evidence.tar.gz` and
  `v0.5.0/knotrel-v0.5.0-measured-executables.tar.gz` (each below GitHub's
  100 MB file limit, so no Git LFS is needed);
- `v0.5.0/MANIFEST.sha256`, `v0.5.0/inventory.json`, `v0.5.0/INVENTORY.md`
  and `v0.5.0/VERIFY.md`.

Access would be limited to organization members with explicit repository
access; the archives would not be public. After an authorized upload, both
archives are to be downloaded again and their SHA-256 compared with the table
above, and this section updated with the repository URL, commit and access
instructions. Until then the evidence exists only on the qualification host
(`/Users/rt/workspace/knotrel/evidence/`, with the archives in
`v0.5.0-MANIFEST/`).
