"""D2c summary: C3 (30 cycles), B5, peaks, events, and the declared ring-drift
classification over 6,000 cycles (DIAGNOSTICS-PLAN-3.md). Early mean = mean of cycles 1-10."""
import json, math, os, sys
D = sys.argv[1]; MiB = 1048576
POLICIES = ("frozen", "T1", "T2")
T_975 = {148: 1.9761}  # t(0.975, 148) for 150 intervals
def recs(p): return [json.loads(l) for l in open(p)]
def cps(p): return [r for r in recs(p) if r.get("kind") == "checkpoint"]
def events(p): return next((r["events"] for r in recs(p) if r.get("kind") == "d2c_events"), [])
def slope(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    res = [y - (my + b * (x - mx)) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(r * r for r in res) / (n - 2) / sxx)
    return b, se
def c3(T, B):
    h = {c["cycle"]: c["net_heap_bytes"] for c in cps(f"{D}/{T}-30-{B}.jsonl")}
    early = [h[c] for c in range(1, 11)]
    lo = max(h[c] for c in range(21, 31)) / max(early)
    b, _ = slope(list(range(1, 31)), [h[c] for c in range(1, 31)])
    g = b * 30 / (sum(early) / 10)
    return lo, g, "PASS" if lo <= 1.25 and g <= 0.10 else "FAIL"
print("C3 over 30 cycles (late/early <= 1.25, growth <= 0.10)")
for T in ("sparse", "ring", "hub"):
    print("  " + " | ".join(f"{T} {B}: {c3(T, B)[0]:.3f} {c3(T, B)[1]:+.3f} {c3(T, B)[2]}" for B in POLICIES))
print("B5 at 100k (lifecycle/plain <= 3.0)")
for T in ("sparse", "hub"):
    plain = cps(f"{D}/B5-plain-{T}.jsonl")[0]["net_heap_bytes"]
    print("  " + " | ".join(f"{T} {B}: {cps(f'{D}/B5-lifecycle-{T}-{B}.jsonl')[0]['net_heap_bytes'] / plain:.4f}" for B in POLICIES))
if not os.path.exists(f"{D}/ring-6000-T2.jsonl"):
    sys.exit(0)
print("6,000 cycles: peaks, transient, steady state, events, ring-drift classification")
for T in ("sparse", "ring", "hub"):
    for B in POLICIES:
        p = f"{D}/{T}-6000-{B}.jsonl"
        if not os.path.exists(p):
            continue
        cs = cps(p); h = {c["cycle"]: c["net_heap_bytes"] for c in cs}
        mx = {c["cycle"]: c["net_max_heap_bytes"] for c in cs}
        r = {c["cycle"]: c["counts"]["retired_vertices"] for c in cs}
        comp = [c for c in range(1, 6001) if r[c] == 0 and r[c - 1] > 0]
        bounds = [1] + [c + 1 for c in comp]
        iv = [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)] + [(bounds[-1], 6000)]
        imax = [max(h[c] for c in range(lo, hi + 1)) for lo, hi in iv if hi >= lo]
        first = imax[0]; rest = imax[1:]
        def classify(lo_i, hi_i):
            ys = imax[lo_i - 1:hi_i]; b, se = slope(list(range(len(ys))), ys)
            t = 1.9761 if len(ys) == 150 else 1.9763
            lo, hi = b - t * se, b + t * se
            return b, lo, hi, ("interval above 0" if lo > 0 else "interval below 0" if hi < 0 else "interval includes 0")  # labels only (addendum 4): no bound is inferred
        b2, l2, h2, k2 = classify(151, 300) if len(imax) >= 300 else (0, 0, 0, "n/a")
        b1, l1, h1, k1 = classify(2, 150)
        ev = events(p)
        def stat(kind):
            v = sorted(e[1] for e in ev if e[0] == kind)
            return f"{kind} n={len(v)} median {v[len(v)//2]/1e3:.0f} us max {v[-1]/1e3:.0f} us" if v else f"{kind} n=0"
        mism = sum(1 for c in cs if c["counts"]["logical"] != c["expected"])
        print(f"  {T:6s} {B:6s} intervals {len(imax)} | running-max peak {max(mx.values())/MiB:.3f} MiB, checkpoint peak {max(h.values())/MiB:.3f} MiB @{max(h, key=h.get)} | first-interval max {first/MiB:.3f}, later interval max {max(rest)/MiB:.3f}, mean of later maxima {sum(rest)/len(rest)/MiB:.3f} MiB | last 100 cycles mean {sum(h[c] for c in range(5901, 6001))/100/MiB:.3f} MiB | mismatches {mism}")
        print(f"         slope of interval maxima: 2-150 {b1:+.1f} B/interval [{l1:+.1f}, {h1:+.1f}] {k1}; 151-300 {b2:+.1f} [{l2:+.1f}, {h2:+.1f}] {k2}")
        last = cs[-1]["counts"]
        print(f"         final counts: catalog_node_capacity {last['catalog_node_capacity']}, incident_capacity {last['incident_capacity']}, incident_entries {last['incident_entries']}")
        if ev:
            print("         events (count build; timing in summary-latency.txt): " + "; ".join(stat(k) for k in ("catalog_rebuild_on_grow", "catalog_rebuild_after_compaction", "engine_compaction")))
