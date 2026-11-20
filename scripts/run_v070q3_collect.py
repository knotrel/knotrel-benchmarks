#!/usr/bin/env python3
"""Collectors of v0.7.0 qualification 3: ``run_v070r_collect.py`` unchanged, bound to
``results/v0.7.0-qualification-3/MATRIX.json`` (R, Rmem, M_desc and M_reg read their
cells from the matrix; A and B/C take their arguments from the chain).

    run_v070q3_collect.py a|bc|r|rmem|mdesc|mreg ARGS...

Revision 3: when ``KNOTREL_INTERFERENCE_DIR`` is set (the autonomous runner), the collectors
run under the proportional interference policy (``interference_collect.py``) instead of the
allow-list gate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import run_v070r_collect as base  # noqa: E402

base.MATRIX = SCRIPTS.parent / "results" / "v0.7.0-qualification-3" / "MATRIX.json"

if __name__ == "__main__":
    if os.environ.get("KNOTREL_INTERFERENCE_DIR"):
        import interference_collect
        sys.exit(interference_collect.main())
    sys.exit(base.main())
