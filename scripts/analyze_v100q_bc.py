#!/usr/bin/env python3
"""B4 and C analysis of the v1.0.0 qualification (the ``--only B4,C`` run).

``analyze_lifecycle_qualification.py`` unchanged in every rule (B4 paired timing, timer
limit, atomicity records, C1-C4) and every per-cell check (build revisions, verify records,
2 warmup and 12 balanced pairs, checkpoints). Only its run-level completeness check differs,
because the frozen ``validate`` refuses any ``--only`` run ("not a complete final run"):

- with ``--expect-only B4,C`` (the v1.0 perimeter, plan section 4.1), the run must be the
  final profile with exactly ``only == "B4,C"``, and its plan must hold exactly the B4 and C
  cells of the frozen matrix (37 B4 cells, 60 C cells with the equivalent references and the
  compact-bfs scope); every other check of ``validate`` applies unchanged (scope,
  equivalent references, window-multiplier hash, a run-log record with exit 0 and AC power,
  a raw file for every cell);
- with ``--expect-only full`` (the core rule triggered, plan section 4.3), the frozen
  ``validate`` runs unchanged.

The installed check is restored when the command ends, so importing this module changes
nothing.

    analyze_v100q_bc.py RUN_DIR --expect-only B4,C|full --expect-knotrel-rev SHA \\
        --expect-multipliers-sha256 SHA --expect-probes-rev SHA \\
        --expect-lifecycle-engines compact-bfs --expect-equivalent-references [--json OUT] [--markdown OUT]
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_lifecycle_qualification as frozen  # noqa: E402

ONLY = "B4,C"
FROZEN_VALIDATE = frozen.validate


def validate_only(run: Path, cells: Dict[str, Dict[str, Any]], rev: str, multipliers_sha: str,
                  lifecycle_engines: str = "compact-bfs,ett,hdt", equivalent_references: bool = False,
                  only: str = ONLY, atomic_references: bool = False) -> Dict[str, Any]:
    """``frozen.validate`` for a final run restricted to ``only`` (comma-separated experiments)."""
    provenance = json.loads((run / "provenance.json").read_text())
    if provenance["profile"] != "final" or provenance.get("only") != only:
        raise frozen.Invalid(f"not a final run restricted to --only {only}")
    if provenance.get("lifecycle_engines", "compact-bfs,ett,hdt") != lifecycle_engines:
        raise frozen.Invalid("lifecycle-engine scope differs from the expected scope")
    if provenance.get("equivalent_references", False) != equivalent_references:
        raise frozen.Invalid("equivalent-reference cells differ from the expected matrix")
    if provenance.get("atomic_references", False) != atomic_references:
        raise frozen.Invalid("atomic-reference cells differ from the expected matrix")
    runner = frozen._runner()
    if atomic_references:
        plan = runner.matrix("final", lifecycle_engines, equivalent_references, True)
    else:
        plan = (runner.matrix("final", lifecycle_engines, True) if equivalent_references
                else runner.matrix("final", lifecycle_engines))
    wanted = set(only.split(","))
    expected = {c["id"] for c in plan if c["experiment"] in wanted}
    if set(cells) != expected:
        raise frozen.Invalid(f"plan matrix differs from the {lifecycle_engines} --only {only} scope "
                             f"(missing {sorted(expected - set(cells))[:3]}, extra {sorted(set(cells) - expected)[:3]})")
    if provenance.get("window_multipliers_sha256") != multipliers_sha:
        raise frozen.Invalid("window multipliers differ from the frozen file")
    log = {r["id"]: r for r in frozen.lines(run / "run-log.jsonl")}
    for cell_id in cells:
        record = log.get(cell_id)
        if record is None or record["exit"] != 0:
            raise frozen.Invalid(f"{cell_id}: missing or failed run")
        if "AC Power" not in record["host_before"]["power"]:
            raise frozen.Invalid(f"{cell_id}: not on AC power")
        if not frozen.contained_file(run / "raw", f"{cell_id}.jsonl", "raw record").exists():
            raise frozen.Invalid(f"{cell_id}: missing raw output")
    return provenance


@contextlib.contextmanager
def installed(expect_only: str) -> Iterator[None]:
    """Installs the completeness check of ``expect_only`` for the duration of the block."""
    if expect_only == "full":
        frozen.validate = FROZEN_VALIDATE
    elif expect_only == ONLY:
        frozen.validate = validate_only
    else:
        raise SystemExit(f"--expect-only must be {ONLY} or full, not {expect_only!r}")
    try:
        yield
    finally:
        frozen.validate = FROZEN_VALIDATE


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--expect-only" not in argv or argv.index("--expect-only") + 1 >= len(argv):
        print(__doc__, file=sys.stderr)
        return 2
    i = argv.index("--expect-only")
    expect_only = argv[i + 1]
    del argv[i:i + 2]
    saved = sys.argv
    sys.argv = ["analyze_lifecycle_qualification.py", *argv]
    try:
        with installed(expect_only):
            return frozen.main()
    finally:
        sys.argv = saved


if __name__ == "__main__":
    sys.exit(main())
