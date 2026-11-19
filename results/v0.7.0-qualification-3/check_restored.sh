#!/bin/sh
# Amendment 1: exit 1 (listing them) if any evidence/*/logs/quiesce-restore.json has no
# quiesce-restore-result.json with "ok": true next to it (same rule as launcher_audit.py pending).
python3 - <<'PY'
import glob, json, os, sys
bad = []
for m in sorted(glob.glob("/Users/rt/workspace/knotrel/evidence/*/logs/quiesce-restore.json")):
    r = os.path.join(os.path.dirname(m), "quiesce-restore-result.json")
    try:
        ok = bool(json.load(open(r)).get("ok"))
    except (OSError, ValueError):
        ok = False
    if not ok:
        bad.append(m)
for b in bad:
    print(f"unrestored quiesce: {b}", file=sys.stderr)
sys.exit(1 if bad else 0)
PY
