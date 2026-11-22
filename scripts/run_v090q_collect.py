#!/usr/bin/env python3
"""Collectors of the v0.9.0 qualification: the v0.7.0 qualification-3 collectors unchanged
(``run_v070r_collect.py``, and ``interference_collect.py`` under the autonomous runner),
bound to ``results/v0.9.0-qualification/MATRIX.json`` (R, Rmem, M_desc and M_reg read their
cells from the matrix, whose experiments are q3's unchanged; A and B/C take their arguments
from the runner).

    run_v090q_collect.py a|bc|r|rmem|mdesc|mreg ARGS...
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import run_v070r_collect as base  # noqa: E402

MATRIX = SCRIPTS.parent / "results" / "v0.9.0-qualification" / "MATRIX.json"
base.MATRIX = MATRIX

if __name__ == "__main__":
    # A dry run goes straight to the base collector (interference_collect's own dry-run path
    # would import run_v070q3_collect, which rebinds the q3 matrix).
    if os.environ.get("KNOTREL_INTERFERENCE_DIR") and "--dry-run" not in sys.argv[2:]:
        import interference_collect
        interference_collect.MATRIX = MATRIX
        sys.exit(interference_collect.main())
    sys.exit(base.main())
