#!/usr/bin/env python3
"""B4/C decision view of the v1.0.0 qualification: ``report_v070q3_bc.py`` unchanged, bound to
``results/v1.0.0-qualification/MATRIX.json`` (same deciding, descriptive and not-equivalent B4
cells, same unqualified requirements, same disclosure categories).

The v1.0 perimeter runs ``--only B4,C`` (plan section 4.1), so no T5 analysis exists unless
the core rule triggered (plan section 4.3). The T5 argument is therefore required exactly when
the freeze record says so: ``--core-rule identical`` takes no T5 file; ``--core-rule different``
requires one and adds its six deciding rows, as in v0.9.0. Statuses are copied unchanged;
nothing is recomputed.

    report_v100q_bc.py BC-analysis.json --core-rule identical
    report_v100q_bc.py BC-analysis.json --core-rule different T5-analysis.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_v070q3_bc as frozen  # noqa: E402
from cli_paths import confined  # noqa: E402

frozen.MATRIX = Path(__file__).resolve().parent.parent / "results" / "v1.0.0-qualification" / "MATRIX.json"


def report(analysis: dict, matrix: dict, t5: dict = None) -> dict:
    """The frozen decision view; T5 rows only when a T5 analysis is given."""
    rows = frozen.label(analysis, matrix) + (frozen.t5_rows(t5) if t5 is not None else [])
    disclosures = [r for r in rows if r["status"] in frozen.DISCLOSURE.get(r["kind"], set())]
    eq = matrix["experiments"]["B_C"]["equivalent_references"]
    unqualified = eq["unqualified_requirements"]
    if len(unqualified) < len(eq["not_equivalent"]["cells"]):
        raise SystemExit("fewer unqualified requirements than not-equivalent cells")
    return {"rows": rows, "deciding_non_pass": frozen.non_pass(rows), "disclosures": disclosures,
            "unqualified_requirements": unqualified,
            "qualification_scope": frozen.scope(unqualified),
            "overall": frozen.overall(rows, unqualified),
            "not_equivalent_inconsistencies": frozen.inconsistencies(rows),
            "core_rule": "different" if t5 is not None else "identical"}


def main(argv: List[str]) -> int:
    args = argv[1:]
    if len(args) < 3 or args[1] != "--core-rule" or args[2] not in ("identical", "different") \
            or (args[2] == "identical" and len(args) != 3) or (args[2] == "different" and len(args) != 4):
        print(__doc__, file=sys.stderr)
        return 2
    analysis = json.loads(confined(args[0], "BC-analysis").read_text())
    matrix = json.loads(frozen.MATRIX.read_text())
    t5 = json.loads(confined(args[3], "T5-analysis").read_text()) if args[2] == "different" else None
    print(json.dumps(report(analysis, matrix, t5), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
