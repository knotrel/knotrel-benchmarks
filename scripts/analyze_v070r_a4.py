#!/usr/bin/env python3
"""Amendment 4 analysis of M_desc and M_reg (future collections, probe revision 3).

``analyze_v070r_qualification.py`` unchanged, with one addition to the validity
rule of ``analyze_v060_m_supplement.py``: a configuration with a background
import must carry the probe-revision-3 ``background.imports`` accounting, and
is invalid when ``import_starved`` is true (an exhausted ETag refresh, a 412
after a refresh, or fewer imports completed than attempted). Every reason of
the frozen rule still applies. Records of attempt a3-3 (probe revision 2) are
analyzed by ``analyze_v070r_qualification.py``, not by this script.

    analyze_v070r_a4.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v070r_a4.py mdesc|mreg DIR
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v060_m_supplement as supplement  # noqa: E402
import analyze_v070r_qualification as requalification  # noqa: E402

FROZEN_VALIDITY = supplement.validity


def validity(record: Dict[str, Any]) -> List[str]:
    """The frozen reasons, plus the amendment 4 import-starvation rule."""
    reasons = FROZEN_VALIDITY(record)
    background = record.get("background")
    if background and background.get("kind") == "import":
        imports = background.get("imports")
        if not isinstance(imports, dict):
            reasons.append("missing background imports (probe revision < 3)")
        elif imports.get("import_starved") is not False:
            reasons.append(
                "import_starved: "
                f"attempted={imports.get('imports_attempted')} completed={imports.get('imports_completed')} "
                f"refresh_exhausted={imports.get('refresh_exhausted')} "
                f"precondition_after_refresh={imports.get('precondition_after_refresh')}"
            )
    return reasons


supplement.validity = validity

if __name__ == "__main__":
    sys.exit(requalification.first.main())
