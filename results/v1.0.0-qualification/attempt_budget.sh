#!/bin/sh
# Attempt budget of the v1.0.0 qualification (PROTOCOL.md sections 5 and 7; plan section 5.5).
# series_budget.sh (the amendment-2 helper, byte-identical to the frozen v0.9.0 copy) applies
# first, unchanged; then this wrapper adds the v1.0 failure rule: a FAILED attempt allows a
# second attempt only if every cause recorded in its logs/failures.jsonl
# (part1_failures_v100q.py, written by the runner) is classified infrastructure or conformance.
# A product failure is a result and is never rerun; a FAILED attempt without that record, or
# with an unknown classification, is refused (fail closed: the maintainer decides).
#
# Usage: attempt_budget.sh attempt N CAP DIR...   (the arguments of series_budget.sh)
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
[ "${1:-}" = attempt ] || { echo "attempt_budget.sh: KIND must be attempt" >&2; exit 2; }
sh "$HERE/series_budget.sh" "$@" || exit 1
shift 3
python3 - "$@" <<'PY'
import json, os, sys
errors = []
for d in sorted(x for x in sys.argv[1:] if os.path.isdir(x)):
    with open(os.path.join(d, "logs", "CONFORMANCE.txt")) as handle:
        status = handle.readline().split(":", 1)[0].strip()
    if status != "FAILED":
        continue
    path = os.path.join(d, "logs", "failures.jsonl")
    try:
        records = [json.loads(line) for line in open(path) if line.strip()]
    except (OSError, ValueError) as error:
        errors.append(f"{d} ended FAILED without a readable logs/failures.jsonl ({error}): the maintainer decides")
        continue
    if not records:
        errors.append(f"{d} ended FAILED with no recorded cause: the maintainer decides")
    for r in records:
        c = r.get("classification")
        if c not in ("infrastructure", "conformance"):
            errors.append(f"{d} ended FAILED on a {c} failure ({r.get('step') or r.get('kind')}: "
                          f"{'; '.join(r.get('why', []) or r.get('evidence', []))[:200]}): never rerun (plan section 5.5)")
for e in errors:
    print(e, file=sys.stderr)
sys.exit(1 if errors else 0)
PY
