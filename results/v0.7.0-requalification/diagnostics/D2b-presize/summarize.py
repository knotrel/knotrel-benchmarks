"""D2b summary: C3 (30 cycles), B5 (100k) and 300-cycle peak/steady state per pre-sizing variant."""
import json, sys
D = sys.argv[1]; MiB = 1048576
VARIANTS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["frozen", "cat", "ids", "hdr-1.25", "hdr-1.5", "hdr-2", "eng", "full"]
def load(p): return [json.loads(l) for l in open(p) if '"checkpoint"' in l]
def slope(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
def c3(T, B):
    h = {c["cycle"]: c["net_heap_bytes"] for c in load(f"{D}/{T}-30-{B}.jsonl")}
    early = [h[c] for c in range(1, 11)]
    lo = max(h[c] for c in range(21, 31)) / max(early)
    g = slope(list(range(1, 31)), [h[c] for c in range(1, 31)]) * 30 / (sum(early) / 10)
    return lo, g, ("PASS" if lo <= 1.25 and g <= 0.10 else "FAIL")
def b5(T, B):
    v = {A: load(f"{D}/B5-{A}-{T}.jsonl")[0]["net_heap_bytes"] for A in ("plain", "reference")}
    v["lifecycle"] = load(f"{D}/B5-lifecycle-{T}-{B}.jsonl")[0]["net_heap_bytes"]
    return v
print("variant    | C3 sparse            | C3 ring              | C3 hub               | B5 sparse (<=3x)     | B5 hub (<=3x)        | peak300 sparse/ring/hub MiB | last100 mean s/r/h MiB")
for B in VARIANTS:
    cells = []
    for T in ("sparse", "ring", "hub"):
        lo, g, st = c3(T, B); cells.append(f"{lo:.3f} {g:+.3f} {st}")
    for T in ("sparse", "hub"):
        v = b5(T, B); r = v["lifecycle"] / v["plain"]
        cells.append(f"{v['lifecycle']/MiB:.1f}MiB {r:.3f} {'PASS' if r <= 3 else 'FAIL'}")
    peaks, means = [], []
    for T in ("sparse", "ring", "hub"):
        h = {c["cycle"]: c["net_heap_bytes"] for c in load(f"{D}/{T}-300-{B}.jsonl")}
        peaks.append(f"{max(h.values())/MiB:.2f}"); means.append(f"{sum(h[c] for c in range(201, 301))/100/MiB:.2f}")
    print(f"{B:10s} | " + " | ".join(f"{c:20s}" for c in cells) + f" | {'/'.join(peaks):27s} | {'/'.join(means)}")
print("C3 cell: late/early, 30-cycle growth (rule <= 1.25 and <= 0.10). B5 cell: lifecycle net heap after construction, lifecycle/plain.")
print("plain/reference net heap: " + ", ".join(f"{T} plain {b5(T,'frozen')['plain']/MiB:.2f} reference {b5(T,'frozen')['reference']/MiB:.2f} MiB" for T in ("sparse", "hub")))
