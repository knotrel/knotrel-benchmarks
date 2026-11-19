#!/usr/bin/env python3
"""Analysis of R, Rmem, M_desc and M_reg for v0.7.0 qualification 3.

``analyze_v070r_a4.py`` (``analyze_v070r_qualification.py`` with the amendment 4
validity rule, installed only while the command runs), bound to
``results/v0.7.0-qualification-3/MATRIX.json``. The two matrices differ in
conformance settings and the B/C collector flag, which these analyzers do
not read.

    analyze_v070q3.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v070q3.py mdesc|mreg DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v070r_a4 as a4  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.7.0-qualification-3" / "MATRIX.json"


def main() -> int:
    with a4.installed() as requalification:
        requalification.first.MATRIX = MATRIX
        requalification.first.frozen.MATRIX = MATRIX
        return requalification.first.main()


if __name__ == "__main__":
    sys.exit(main())
