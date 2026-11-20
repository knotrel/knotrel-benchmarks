#!/usr/bin/env python3
"""Ring-drift correction (maintainer 2026-11-20): observed behaviour over 6,000 cycles.

Reads raw/{sparse,ring,hub}-6000-{frozen,T1}.jsonl (count build) and prints, per series:
- the per-compaction-interval maxima of net heap, by blocks of 50 intervals;
- the least-squares slope of the interval maxima over intervals 151-300 with its 95%
  interval (serial correlation not modelled), and what that interval excludes;
- the storage counts that bound the heap structurally (catalog capacity, engine vertices)
  and the one that is not bounded by construction (incident-list capacity).
No classification is printed: an interval that contains zero does not demonstrate a bound.
"""
import json
import math

MiB = 1 << 20
T_975 = 1.9761  # t(0.975, 148)


def slope(ys):
    xs = list(range(len(ys)))
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    resid = [y - (my + b * (x - mx)) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(r * r for r in resid) / (len(xs) - 2) / sxx)
    return b, b - T_975 * se, b + T_975 * se


for topology in ("sparse", "ring", "hub"):
    for policy in ("frozen", "T1"):
        cps = [json.loads(line) for line in open(f"raw/{topology}-6000-{policy}.jsonl")]
        h = {c["cycle"]: c for c in cps if c.get("kind") == "checkpoint"}
        retired = {c: h[c]["counts"]["retired_vertices"] for c in h}
        comp = [c for c in range(1, 6001) if retired[c] == 0 and retired[c - 1] > 0]
        bounds = [1] + [c + 1 for c in comp]
        iv = [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)] + [(bounds[-1], 6000)]
        iv = [x for x in iv if x[1] >= x[0]]
        imax = [max(h[c]["net_heap_bytes"] for c in range(lo, hi + 1)) for lo, hi in iv]
        print(f"{topology} {policy}: {len(imax)} compaction intervals")
        print(f"  interval 1 (transient) max {imax[0] / MiB:.4f} MiB")
        for a in range(0, 300, 50):
            blk = imax[max(a, 1):a + 50]
            print(f"  intervals {max(a, 1) + 1:3d}-{a + 50:3d}: mean {sum(blk) / len(blk) / MiB:.4f}, "
                  f"min {min(blk) / MiB:.4f}, max {max(blk) / MiB:.4f} MiB")
        later = imax[50:]
        means = [sum(imax[a:a + 50]) / 50 for a in range(50, 300, 50)]
        print(f"  intervals 51-300: range of interval maxima {(max(later) - min(later)) / 1024:.1f} KiB; "
              f"spread of 50-interval block means {(max(means) - min(means)) / 1024:.1f} KiB")
        b, lo, hi = slope(imax[150:300])
        print(f"  slope 151-300: {b:+.1f} B/interval [{lo:+.1f}, {hi:+.1f}]; at the upper bound, "
              f"+{hi * 300 / 1024:.1f} KiB per 300 further intervals (6,000 cycles)")
        starts = [b_ for b_ in bounds[1:] if b_ <= 6000]
        for key in ("catalog_node_capacity", "engine_vertices", "incident_capacity"):
            vals = [h[s]["counts"][key] for s in starts]
            peak = [h[c]["counts"][key] for c in range(1, 6001)]
            print(f"  {key}: at interval starts {min(vals)}-{max(vals)} (first {vals[0]}, last {vals[-1]}); "
                  f"max over all cycles {max(peak)}")
