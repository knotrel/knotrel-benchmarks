"""D2 summary: C3 rule values, 300-cycle boundedness and B5 memory per build variant."""
import json, sys
D = sys.argv[1]; MiB = 1048576
VARIANTS = ("frozen", "presized-compaction", "presized-start")
def load(p): return [json.loads(l) for l in open(p) if '"checkpoint"' in l]
def slope(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
print("C3 over 30 cycles (rule: late/early <= 1.25 and 30-cycle growth <= 0.10)")
for T in ("sparse", "ring", "hub"):
    for B in VARIANTS:
        h = {c["cycle"]: c["net_heap_bytes"] for c in load(f"{D}/{T}-30-{B}.jsonl")}
        early = [h[c] for c in range(1, 11)]
        lo = max(h[c] for c in range(21, 31)) / max(early)
        g = slope(list(range(1, 31)), [h[c] for c in range(1, 31)]) * 30 / (sum(early) / 10)
        st = "PASS" if lo <= 1.25 and g <= 0.10 else "FAIL"
        print(f"  {T:6s} {B:19s} late/early {lo:.3f} growth {g:+.3f} {st} | cycle0 {h[0]/MiB:.1f} MiB, max {max(h.values())/MiB:.1f} MiB")
print("300 cycles (declared bounded: max(151-300) <= max(31-150) and |slope 151-300| <= 1% of the early mean per 150 cycles)")
for T in ("sparse", "ring", "hub"):
    for B in VARIANTS:
        f = f"{D}/{T}-300.jsonl" if B == "frozen" else f"{D}/{T}-300-{B}.jsonl"
        cps = load(f); h = {c["cycle"]: c["net_heap_bytes"] for c in cps}
        a = max(h[c] for c in range(31, 151)); b = max(h[c] for c in range(151, 301))
        em = sum(h[c] for c in range(1, 11)) / 10
        s = slope(list(range(151, 301)), [h[c] for c in range(151, 301)]) * 150 / em
        last = [h[c] for c in range(201, 301)]
        ok = b <= a and abs(s) <= 0.01
        mism = sum(1 for c in cps if c["counts"]["logical"] != c["expected"])
        print(f"  {T:6s} {B:19s} peak {max(h.values())/MiB:.2f} MiB @cycle {max(h, key=h.get)} | max31-150 {a} B, max151-300 {b} B ({b-a:+d}) | slope {s*100:+.3f}% | {'bounded' if ok else 'NOT bounded by the declared rule'} | last 100: mean {sum(last)/100/MiB:.2f}, min {min(last)/MiB:.2f}, max {max(last)/MiB:.2f} MiB | count mismatches {mism}")
print("B5 memory at 100k (net heap after construction; budget lifecycle/plain <= 3x)")
for T in ("sparse", "hub"):
    for B in VARIANTS:
        v = {A: load(f"{D}/B5-{A}-{T}-{B if (A == 'lifecycle' or B != 'presized-start') else 'presized-compaction'}.jsonl")[0]["net_heap_bytes"] for A in ("plain", "lifecycle", "reference")}
        print(f"  {T:6s} {B:19s} plain {v['plain']/MiB:.1f}, lifecycle {v['lifecycle']/MiB:.1f}, reference {v['reference']/MiB:.1f} MiB | lifecycle/plain {v['lifecycle']/v['plain']:.3f}")
