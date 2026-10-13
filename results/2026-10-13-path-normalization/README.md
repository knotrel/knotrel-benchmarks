# Local-path normalization of archived evidence (2026-10-13)

Several archived experiment records contained machine-local absolute paths (the
author's home directory, an agent session folder, the cargo registry and a
download location). Those paths carry no meaning outside the machine that
produced them. They were replaced by placeholders, and every hash that depended
on the rewritten text was recomputed. **Measurements, statistics and conclusions
are unchanged.**

## What was changed

109 files in these result directories (30 were already tracked, 79 were new):

- `2026-10-12-ett-hardware-profile-m4`, `-signposted`, `-manual-counters`
- `2026-10-12-ett-manual-counter-mapping-m4`, `-probe-m4`, `2026-10-12-ett-signpost-validation-m4`
- `2026-10-12-initialization-aa`, `-phase0`, `-phase0-replication`

2,512 occurrences were replaced:

| Placeholder | Replaces | Count |
| --- | --- | ---: |
| `$WORKSPACE` | directory holding the sibling `knotrel` and `knotrel-benchmarks` checkouts | 1,311 |
| `$SESSION_STATE` | agent session-state directory, where raw Instruments traces were kept | 938 |
| `$CARGO_HOME` | cargo home (registry paths in build logs) | 160 |
| `$HOME` | any other home-directory path (an Instruments template under Downloads) | 103 |

`$SESSION_STATE` counts 932 ordinary plus 6 occurrences in Python sources that
split the path across adjacent string literals; the result is still valid Python.
`$NAME` was chosen over `<name>` because Markdown would hide the latter as a tag.

## Hashes

- **`arguments_sha256` (288 values).** Each original value was first reproduced
  from its original argument list; the tool aborts otherwise. It was then
  recomputed over the normalized list.
- **File-hash citations (89 values).** Manifests citing a changed file's SHA-256
  (`artifact_sha256`, `schedule_sha256`, build logs, and `validation_analysis_sha256`
  in the twelve ETT batch files) now cite the new hash. The initialization-aa
  README cites the new manifest hash and also keeps the as-collected value.
- **Left untouched on purpose.** `environment_sha256` (its preimage was never
  stored, so it cannot be recomputed) and hashes of external artifacts: binaries,
  Instruments traces and templates, and protocol/plan files.
- **Unchanged evidence.** Raw reports, stderr, analysis results, executables and
  every file that contained no local path are byte-identical to before.

[receipt.json](receipt.json) lists, for each changed file, its original and new
SHA-256 and the number of replacements and recomputed hashes. The original home
directory is deliberately not recorded here or in the receipt.

## Consequences

- The paths are provenance records, not inputs. The archived collectors and probe
  scripts of the ETT experiments now contain placeholders, so they are readable
  records and no longer run as archived. The closed A/A and Phase 0 collectors
  would refuse to start for the same reason; rerunning them requires resolving
  the placeholders and is not authorized by this change.
- A manifest hash quoted from before 2026-10-13 differs from the current file.
  The old and new values for each file are in the receipt.
- The original files were kept outside the repository by the operator.

## Verifying

The following checks were run on the normalized files. `normalize_paths.py`
(standard library only) takes the original home directory as an argument, so a
holder of the originals can reproduce the output and compare it with the receipt.

- No home-directory path or user name remains in any repository file.
- All 95 JSON documents differ from their originals only in path strings and
  hash values: 53,952 values identical, 2,496 paths, 377 hashes, no other change.
- All artifact hashes verify in the three manifests (82, 82 and 375 entries).
- initialization-aa: 144 `arguments_sha256` values recompute; the 72 pair files
  equal the manifest's observations; `schedule_sha256` matches.
- Twelve ETT batch files cite the new hash of the validation `analysis.json`.

## Not changed

Older result directories also contain local paths of other forms: user directory
paths of another environment in the 2026-09 manifests, and macOS temporary
directories in the 2026-10-06 to 2026-10-10 results. They were outside the
requested scope and were not modified.
