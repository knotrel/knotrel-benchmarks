#!/bin/sh
# Amendment 2: budget of soaks or attempts. Every directory counts, whatever its result (the
# amendment-1 rule: soak N at most max_soaks, attempt N at most attempts_cap).
#
# Usage: series_budget.sh KIND N CAP DIR...
#   KIND  soak | attempt
#   N     the number the new directory would get
#   CAP   max_soaks or attempts_cap
#   DIR   every existing directory of this budget (soaks of every amendment, or the attempts of
#         the series for this candidate); patterns that match nothing are ignored
#
# Exit 1, saying why, unless:
#   - N is the number of existing directories plus one (numbers are never reused or skipped);
#   - N is at most CAP;
#   - every existing directory has logs/CONFORMANCE.txt (it was launched and its trap ran);
#   - for attempts, no earlier attempt is CONFORMING (the first CONFORMING attempt is final).
KIND=$1
N=$2
CAP=$3
shift 3
python3 - "$KIND" "$N" "$CAP" "$@" <<'PY'
import os, sys
kind, n, cap, dirs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), [d for d in sys.argv[4:] if os.path.isdir(d)]
errors = []
if n != len(dirs) + 1:
    errors.append(f"{kind} number must be {len(dirs) + 1}: {len(dirs)} {kind} directories exist")
if n > cap:
    errors.append(f"{kind} {n} exceeds the cap {cap}: the maintainer decides")
for d in sorted(dirs):
    f = os.path.join(d, "logs", "CONFORMANCE.txt")
    if not os.path.exists(f):
        errors.append(f"{d} has no logs/CONFORMANCE.txt (never launched, or killed without its trap): the maintainer decides")
        continue
    if kind == "attempt" and open(f).readline().startswith("CONFORMING"):
        errors.append(f"{d} is CONFORMING: the first CONFORMING attempt is final")
for e in errors:
    print(e, file=sys.stderr)
print(f"{kind} budget: {len(dirs)} used of {cap}; next number {len(dirs) + 1}")
sys.exit(1 if errors else 0)
PY
