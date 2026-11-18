#!/bin/sh
# Amendment 2: budget of soaks or attempts, as MATRIX states it ("NOT STARTED, no attempt consumed").
#
# Usage: series_budget.sh KIND N CAP DIR...
#   KIND  soak | attempt
#   N     the number the new directory would get
#   CAP   max_soaks or attempts_cap
#   DIR   every existing directory of this budget (soaks of every amendment, or the attempts of
#         the series for this candidate)
#
# Exit 1, saying why, unless:
#   - N is the number of existing directories plus one (numbers are never reused);
#   - every existing directory was launched (it has logs/CONFORMANCE.txt);
#   - for attempts, no earlier attempt is CONFORMING (the first CONFORMING attempt is final);
#   - the consumed ones (CONFORMANCE.txt not starting "NOT STARTED" / "SOAK NOT STARTED") are
#     fewer than CAP.
KIND=$1
N=$2
CAP=$3
shift 3
python3 - "$KIND" "$N" "$CAP" "$@" <<'PY'
import os, sys
kind, n, cap, dirs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), [d for d in sys.argv[4:] if os.path.isdir(d)]
prefix = "SOAK NOT STARTED" if kind == "soak" else "NOT STARTED"
errors, consumed = [], []
if n != len(dirs) + 1:
    errors.append(f"{kind} number must be {len(dirs) + 1}: {len(dirs)} {kind} directories exist")
for d in sorted(dirs):
    f = os.path.join(d, "logs", "CONFORMANCE.txt")
    if not os.path.exists(f):
        errors.append(f"{d} was prepared but never launched: launch it or the maintainer decides")
        continue
    first = (open(f).readline().strip())
    if first.startswith(prefix):
        continue
    consumed.append(d)
    if kind == "attempt" and first.startswith("CONFORMING"):
        errors.append(f"{d} is CONFORMING: the first CONFORMING attempt is final")
if len(consumed) >= cap:
    errors.append(f"{len(consumed)} {kind}(s) consumed, cap {cap}: the maintainer decides")
for e in errors:
    print(e, file=sys.stderr)
print(f"{kind} budget: {len(consumed)} consumed of {cap}; next number {len(dirs) + 1}")
sys.exit(1 if errors else 0)
PY
