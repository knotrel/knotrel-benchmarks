#!/usr/bin/env python3
"""Analysis of R, Rmem and M_reg for the v1.0.0 qualification.

``analyze_v070q3.py`` (the amendment-4 validity rule of ``analyze_v070r_a4.py``) unchanged,
bound to ``results/v1.0.0-qualification/MATRIX.json``, as ``analyze_v090q.py`` binds the v0.9.0
matrix. M_desc is outside the v1.0 perimeter and is refused.

    analyze_v100q.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v100q.py mreg DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v070r_a4 as a4  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v1.0.0-qualification" / "MATRIX.json"
EXPERIMENTS = ("r", "rmem", "mreg")


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in EXPERIMENTS:
        print(__doc__, file=sys.stderr)
        return 2
    with a4.installed() as requalification:
        requalification.first.MATRIX = MATRIX
        requalification.first.frozen.MATRIX = MATRIX
        return requalification.first.main()


if __name__ == "__main__":
    sys.exit(main())
