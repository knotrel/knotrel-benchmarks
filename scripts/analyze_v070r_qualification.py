#!/usr/bin/env python3
"""Analysis of the v0.7.0 re-qualification experiments R, Rmem, M_desc and M_reg.

``analyze_v070_qualification.py`` (the first campaign's analysis, which
wraps the frozen v0.6.0 analyzers and the probe-revision-2 validity rule)
unchanged, bound to ``results/v0.7.0-requalification/MATRIX.json``. The two
matrices differ only in seeds and conformance settings, which no analyzer
reads. A and B/C use ``analyze_bc_qualification.py --rules v0.4.0`` and
``analyze_lifecycle_qualification.py`` unchanged.

    analyze_v070r_qualification.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v070r_qualification.py mdesc|mreg DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v070_qualification as first  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.7.0-requalification" / "MATRIX.json"
first.MATRIX = MATRIX
first.frozen.MATRIX = MATRIX

if __name__ == "__main__":
    sys.exit(first.main())
