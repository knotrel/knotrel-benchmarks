"""D2b long run (1,500 cycles): declared boundedness on halves and ring-drift criterion on
per-compaction-interval maxima (DIAGNOSTICS-PLAN-2.md)."""
import json, sys
D = sys.argv[1]; MiB = 1048576
def slope(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
for T in ("sparse", "ring", "hub"):
    for B in ("frozen", "cat"):
        cps = [json.loads(l) for l in open(f"{D}/{T}-1500-{B}.jsonl") if '"checkpoint"' in l]
        h = {c["cycle"]: c["net_heap_bytes"] for c in cps}
        retired = {c["cycle"]: c["counts"]["retired_vertices"] for c in cps}
        a = max(h[c] for c in range(31, 751)); b = max(h[c] for c in range(751, 1501))
        em = sum(h[c] for c in range(1, 11)) / 10
        s = slope(list(range(751, 1501)), [h[c] for c in range(751, 1501)]) * 750 / em
        bounded = b <= a and abs(s) <= 0.01
        # compaction intervals: a compaction is a cycle whose retired count drops to 0 from >0
        comp = [c for c in range(1, 1501) if retired[c] == 0 and retired[c - 1] > 0]
        bounds = [1] + [c + 1 for c in comp]  # interval i starts after a compaction
        ivals = [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)] + [(bounds[-1], 1500)]
        imax = [max(h[c] for c in range(lo, hi + 1)) for lo, hi in ivals if hi >= lo]
        k = len(imax)
        settled = max(imax[-25:]) <= max(imax[25:50]) if k >= 75 else None
        mism = sum(1 for c in cps if c["counts"]["logical"] != c["expected"])
        print(f"{T:6s} {B:6s} compactions {len(comp)} intervals {k} | max31-750 {a} max751-1500 {b} ({b-a:+d} B) slope751-1500 {s*100:+.3f}% -> {'bounded' if bounded else 'NOT bounded'} | interval maxima: first {imax[0]/MiB:.3f}, 2nd {imax[1]/MiB:.4f}, min(2..) {min(imax[1:])/MiB:.4f}, max(2..) {max(imax[1:])/MiB:.4f} MiB; max(26-50) {max(imax[25:50])} max(last25) {max(imax[-25:])} -> drift {'settled' if settled else 'NOT settled'} | peak {max(h.values())/MiB:.2f} MiB @ {max(h, key=h.get)} | mismatches {mism}")
        if T == "ring" and B == "frozen":
            print("  ring frozen interval maxima (B):", " ".join(str(x) for x in imax))
print("least-squares slope of per-interval maxima over intervals 2-75 (bytes per interval; per 1,000 cycles)")
for T in ("sparse", "ring", "hub"):
    cps = [json.loads(l) for l in open(f"{D}/{T}-1500-frozen.jsonl") if '"checkpoint"' in l]
    h = {c["cycle"]: c["net_heap_bytes"] for c in cps}; r = {c["cycle"]: c["counts"]["retired_vertices"] for c in cps}
    comp = [c for c in range(1, 1501) if r[c] == 0 and r[c - 1] > 0]; bounds = [1] + [c + 1 for c in comp]
    iv = [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)] + [(bounds[-1], 1500)]
    imax = [max(h[c] for c in range(lo, hi + 1)) for lo, hi in iv if hi >= lo][1:]
    s = slope(list(range(len(imax))), imax)
    imin = [min(h[c] for c in range(lo, hi + 1)) for lo, hi in iv if hi >= lo][1:]
    print(f"  {T:6s} maxima slope {s:+.1f} B/interval ({s*50/1024:+.1f} KiB per 1,000 cycles, {s*50/imax[0]*100:+.3f}%); minima slope {slope(list(range(len(imin))), imin):+.1f} B/interval")
