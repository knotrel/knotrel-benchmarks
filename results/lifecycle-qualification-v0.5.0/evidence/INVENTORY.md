# v0.5.0 qualification evidence — inventory and preservation

Covers the raw evidence cited by `results/lifecycle-qualification-v0.5.0/`
and by the knotrel v0.5.0 release notes. The raw data itself is not stored in
this public repository.

## Durable storage

- **Where:** private GitHub repository `knotrel/knotrel-qualification-evidence`,
  owned by the `knotrel` organization, directory `v0.5.0/`.
- **Package commit:** `83ec5474b62d9506352e93a95cf54069826052d7`; storage and
  verification record (`v0.5.0/STORAGE.md`) added in
  `28bb09707e7ad34d25508ad565cd3111325ccff6`.
- **Access:** private; request read access from a `knotrel` organization owner.
  The archives contain host-specific paths and are not to be republished.
- **Verified 2026-11-16:** the package commit was fetched from the remote into
  a new directory; both archive digests equal the table below and all 8,693
  manifest entries verify after extraction.

| Archive | Size | SHA-256 |
|---|---|---|
| `knotrel-v0.5.0-evidence.tar.gz` (raw evidence + manifest + inventory) | 27,398,770 B | `13e136056d20ee96fcfb534819e1ac10fc85238a54b56b5e8af2dcd0e4c5dce7` |
| `knotrel-v0.5.0-measured-executables.tar.gz` (30 executables) | 24,016,232 B | `b717703c9abaf9d7bff1392e1c8435bee345db316f65953e57d0ad2d2ddbce53` |

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
- `inventory.json` (this directory): counts, bytes, per-directory listing
  digests (69 directories), executable hashes and the excluded trees.

## Not preserved (regenerable, excluded from the archives)

18 trees, about 9 GB: A-campaign `targets/` (build trees; the final measured
executables are preserved separately), `sources/` (git clones of recorded
commits), validation `pkg-checkout/` and `checkout/` (clones of recorded
commits) and `cargo-home/` (downloaded crates.io dependencies, reproducible
from the lockfiles). Earlier probe binaries of run 3 were overwritten (see
`PRESERVATION-INCIDENT-run3-binaries.md`); their hashes remain the record.

## Report links

All `evidence/v0.5.0-*` paths cited in the benchmarks result reports, the
remediation reports and the knotrel release notes resolve to files or
directories inside the archived evidence (21 distinct paths; the only unmatched
string is the `D1-<label>` naming template in `D1-PLAN.md`).

## Sensitive-data check

Before transfer, an automated scan of all evidence files and executables found
no credentials, tokens, private keys or e-mail addresses. The files do contain
absolute paths of the qualification host, which is why the archives are kept
private.
