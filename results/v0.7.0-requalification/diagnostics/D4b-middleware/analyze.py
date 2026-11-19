"""D4b declared re-measurement: per variant, 200 pairs (two runs of 100) of the frozen
metrics-ops scenario; per-pair log ratio ln(metrics on / metrics off); median and the
distribution-free 95% order-statistic interval [r(86), r(115)] (binomial, p = 0.5)."""
import json, math, statistics, sys
from math import comb
D = sys.argv[1]
def ranks(n):
    cdf = lambda k: sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    lo = max(l for l in range(1, n) if cdf(l - 1) <= 0.025)
    return lo, n + 1 - lo
pct = lambda x: (math.exp(x) - 1) * 100
runs = {"V0": ["run1-V0", "run4-V0"], "V1": ["run2-V1", "run3-V1"], "V2": ["run5-V2", "run6-V2"]}
res = {}
for v, names in runs.items():
    pairs = []
    for name in names:
        recs = [json.loads(l) for l in open(f"{D}/{name}.jsonl")]
        p = [r for r in recs if r.get("kind") == "pair"]
        assert all(r["answers_agree"] for r in p), name
        assert all(r["candidate_requests"] == r["reference_requests"] == 37 for r in p), name
        pairs += p
    r = sorted(math.log(p["candidate_ns"] / p["reference_ns"]) for p in pairs)
    n = len(r); lo, hi = ranks(n)
    med = statistics.median(r)
    on = statistics.median(p["candidate_ns"] for p in pairs) / 1e3; off = statistics.median(p["reference_ns"] for p in pairs) / 1e3
    per_run = [statistics.median(math.log(p["candidate_ns"] / p["reference_ns"]) for p in [json.loads(l) for l in open(f"{D}/{nm}.jsonl")] if p.get("kind") == "pair") for nm in names]
    res[v] = (pct(med), pct(r[lo - 1]), pct(r[hi - 1]))
    print(f"{v}: n={n} ranks [r({lo}), r({hi})]; median overhead {pct(med):+.2f}% [{pct(r[lo-1]):+.2f}, {pct(r[hi-1]):+.2f}]; median window on {on:.1f} us, off {off:.1f} us; per-run medians {', '.join(f'{pct(x):+.2f}%' for x in per_run)}")
for a, b in (("V0", "V1"), ("V0", "V2")):
    d = res[a][0] - res[b][0]
    overlap = not (res[a][1] > res[b][2] or res[b][1] > res[a][2])
    print(f"{a} - {b} median overhead: {d:+.2f} points; intervals {'overlap: no difference claimed (declared rule)' if overlap else 'do not overlap'}")
