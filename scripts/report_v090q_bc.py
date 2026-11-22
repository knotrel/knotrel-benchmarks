#!/usr/bin/env python3
"""B/C and T5 report of the v0.9.0 qualification: ``report_v070q3_bc.py`` unchanged, bound to
``results/v0.9.0-qualification/MATRIX.json`` (same deciding, descriptive and not-equivalent
cells, same unqualified requirements).

    report_v090q_bc.py BC-analysis.json T5-analysis.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_v070q3_bc as frozen  # noqa: E402

frozen.MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.9.0-qualification" / "MATRIX.json"

if __name__ == "__main__":
    sys.exit(frozen.main())
