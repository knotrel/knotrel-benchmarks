#!/usr/bin/env python3
"""Amendment 4 analysis of M_desc and M_reg (future collections, probe revision 3).

``analyze_v070r_qualification.py`` unchanged, with one addition to the validity
rule of ``analyze_v060_m_supplement.py``: a configuration with a background
import must carry the probe-revision-3 ``background.imports`` accounting, and
is invalid when it shows import starvation: ``import_starved`` not false, or
counters that imply it (a failed or exhausted ETag refresh, a 412 after a
refresh, or fewer imports completed than attempted). Every reason of the
frozen rule still applies.

The amended rule is installed only while this script's command runs
(``installed()``); importing the module changes nothing, so other users of the
frozen supplement in the same process are unaffected. Records of attempt a3-3
(probe revision 2) are analyzed by ``analyze_v070r_qualification.py``, not by
this script.

    analyze_v070r_a4.py r|rmem DIR --ref-rev SHA --cand-rev SHA
    analyze_v070r_a4.py mdesc|mreg DIR
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v060_m_supplement as supplement  # noqa: E402

FROZEN_VALIDITY = supplement.validity


def _starvation(imports: Dict[str, Any]) -> List[str]:
    """Why the import accounting shows starvation (empty when it does not)."""
    why = []
    if imports.get("import_starved") is not False:
        why.append(f"import_starved={imports.get('import_starved')}")
    for key in ("refresh_exhausted", "refresh_failed_status", "precondition_after_refresh"):
        value = imports.get(key)
        if not isinstance(value, int) or value != 0:
            why.append(f"{key}={value}")
    attempted, completed = imports.get("imports_attempted"), imports.get("imports_completed")
    if not (isinstance(attempted, int) and isinstance(completed, int)) or completed < attempted:
        why.append(f"attempted={attempted} completed={completed}")
    return why


def validity(record: Dict[str, Any]) -> List[str]:
    """The frozen reasons, plus the amendment 4 import-starvation rule."""
    reasons = FROZEN_VALIDITY(record)
    background = record.get("background")
    if background and background.get("kind") == "import":
        imports = background.get("imports")
        if not isinstance(imports, dict):
            reasons.append("missing background imports (probe revision < 3)")
        else:
            why = _starvation(imports)
            if why:
                reasons.append("import starvation: " + " ".join(why))
    return reasons


@contextlib.contextmanager
def installed() -> Iterator[None]:
    """Installs the amended rule (and the re-qualification matrix binding of
    ``analyze_v070r_qualification``) for the duration of the block."""
    import analyze_v060_qualification as frozen
    saved_frozen = frozen.MATRIX
    first = sys.modules.get("analyze_v070_qualification")
    saved_first = first.MATRIX if first else None
    saved_validity = supplement.validity
    import analyze_v070r_qualification as requalification
    requalification.first.MATRIX = requalification.MATRIX  # rebound on every use, not only at first import
    frozen.MATRIX = requalification.MATRIX
    supplement.validity = validity
    try:
        yield requalification
    finally:
        supplement.validity = saved_validity
        frozen.MATRIX = saved_frozen
        import analyze_v070_qualification as first_now
        first_now.MATRIX = saved_first if first else Path(first_now.__file__).resolve().parent.parent / "results" / "v0.7.0-qualification" / "MATRIX.json"


def main() -> int:
    with installed() as requalification:
        return requalification.first.main()


if __name__ == "__main__":
    sys.exit(main())
