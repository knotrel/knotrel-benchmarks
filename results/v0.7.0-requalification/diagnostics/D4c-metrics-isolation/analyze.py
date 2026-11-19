"""D4c (DIAGNOSTICS-PLAN-3.md): per variant, 200 pairs (two runs of 100) of the frozen
metrics-ops scenario on one diagnostic binary; median ln(on/off) and the distribution-free
95% interval [r(86), r(115)]; component share = ctl - variant, claimed only without overlap."""
import glob, json, math, os, statistics, sys
from math import comb
D = sys.argv[1]
def ranks(n):
    cdf = lambda k: sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    lo = max(l for l in range(1, n) if cdf(l - 1) <= 0.025)
    return lo, n + 1 - lo
pct = lambda x: (math.exp(x) - 1) * 100
res = {}
for v in ("ctl", "nocount", "noclock", "nogauge", "notrack", "noall"):
    files = sorted(glob.glob(f"{D}/run*-{v}.jsonl")); pairs = []
    for f in files:
        p = [r for r in map(json.loads, open(f)) if r.get("kind") == "pair"]
        assert all(r["answers_agree"] for r in p), f
        pairs += p
    r = sorted(math.log(p["candidate_ns"] / p["reference_ns"]) for p in pairs)
    lo, hi = ranks(len(r))
    res[v] = (pct(statistics.median(r)), pct(r[lo - 1]), pct(r[hi - 1]))
    runs = [statistics.median(math.log(p["candidate_ns"] / p["reference_ns"]) for p in map(json.loads, open(f)) if p.get("kind") == "pair") for f in files]
    print(f"{v:8s} n={len(r)} median {res[v][0]:+.2f}% [{res[v][1]:+.2f}, {res[v][2]:+.2f}] | runs {', '.join(f'{pct(x):+.2f}%' for x in runs)} ({', '.join(os.path.basename(f) for f in files)})")
for v in ("nocount", "noclock", "nogauge", "notrack", "noall"):
    d = res["ctl"][0] - res[v][0]
    overlap = not (res["ctl"][1] > res[v][2] or res[v][1] > res["ctl"][2])
    print(f"ctl - {v:8s}: {d:+.2f} points; {'intervals overlap: not claimed' if overlap else 'CLAIMED (no overlap)'}")
