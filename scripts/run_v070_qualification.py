#!/usr/bin/env python3
"""Collector for the knotrel v0.7.0 qualification experiments R, Rmem, M_desc and M_reg.

The frozen v0.6.0 collector (``run_v060_qualification.py``) unchanged, bound
to ``results/v0.7.0-qualification/MATRIX.json`` (and its ``FREEZE.json``),
with the host-activity gate (``host_activity_monitor.py --check``) before
every child in addition to the frozen AC-power and thermal checks.

    run_v070_qualification.py r|rmem|mdesc|mreg ...   (arguments as run_v060_qualification.py)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_v060_qualification as frozen  # noqa: E402

frozen.MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.7.0-qualification" / "MATRIX.json"
MONITOR = Path(__file__).resolve().parent / "host_activity_monitor.py"
_run = frozen.Recorder.run


def gated_run(self, label, argv):
    proc = subprocess.run([sys.executable, str(MONITOR), "--check"], capture_output=True, text=True)
    if proc.returncode != 0:
        self.log["stopped"] = f"activity gate before {label}: {proc.stdout.strip()[:500]}"
        self.flush()
        raise SystemExit(self.log["stopped"])
    return _run(self, label, argv)


frozen.Recorder.run = gated_run

if __name__ == "__main__":
    sys.exit(frozen.main())
