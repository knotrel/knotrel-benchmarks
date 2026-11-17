#!/usr/bin/env python3
"""Analysis of the knotrel v0.7.0 experiments R, Rmem, M_desc and M_reg.

R and Rmem: the frozen v0.6.0 analysis (``analyze_v060_qualification.py``)
unchanged, bound to ``results/v0.7.0-qualification/MATRIX.json``. M_desc and
M_reg: the frozen analysis plus the probe-revision-2 validity rule of the
v0.6.0 M supplement (``analyze_v060_m_supplement.py``) unchanged; an M_reg
cell with an invalid analyzed observation is INVALID (no verdict).

    analyze_v070_qualification.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v070_qualification.py mdesc|mreg DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v060_qualification as frozen  # noqa: E402
from analyze_v060_m_supplement import analyze_supplement_mdesc, analyze_supplement_mreg  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.7.0-qualification" / "MATRIX.json"
frozen.MATRIX = MATRIX


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] in ("mdesc", "mreg"):
        directory = Path(sys.argv[2])
        matrix = json.loads(MATRIX.read_text())
        try:
            if sys.argv[1] == "mdesc":
                result = analyze_supplement_mdesc(directory)
            else:
                result = analyze_supplement_mreg(directory, {"M_reg_supplement": matrix["experiments"]["M_reg"]})
        except (frozen.AnalysisError, KeyError, StopIteration, ValueError) as error:
            print(f"analysis rejected: {error!r}", file=sys.stderr)
            return 2
        (directory / "analysis.json").write_text(json.dumps({"result": result}, indent=1))
        print(json.dumps(result, indent=1)[:4000])
        return 0
    return frozen.main()


if __name__ == "__main__":
    sys.exit(main())
