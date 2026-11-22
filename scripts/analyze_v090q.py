#!/usr/bin/env python3
"""Analysis of R, Rmem, M_desc and M_reg for the v0.9.0 qualification.

``analyze_v070q3.py`` (the amendment-4 validity rule of ``analyze_v070r_a4.py``) unchanged,
bound to ``results/v0.9.0-qualification/MATRIX.json``. Also used for the descriptive M_reg
of Part 2 (reference v0.8.0); its classification is then reported without a verdict.

    analyze_v090q.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v090q.py mdesc|mreg DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v070r_a4 as a4  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.9.0-qualification" / "MATRIX.json"


def main() -> int:
    with a4.installed() as requalification:
        requalification.first.MATRIX = MATRIX
        requalification.first.frozen.MATRIX = MATRIX
        return requalification.first.main()


if __name__ == "__main__":
    sys.exit(main())
