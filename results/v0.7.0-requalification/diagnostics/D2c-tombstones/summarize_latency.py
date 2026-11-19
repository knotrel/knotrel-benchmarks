"""D2c latency (timing build, quiet phase-3 chain) and the A2 operations impact (B1 fresh-churn)."""
import glob, json, os, statistics as st, sys
D = sys.argv[1]
print("Event durations, timing build (6,000 cycles; median / p99 / max, us; count)")
for top in ("sparse", "ring", "hub"):
    for pol in ("frozen", "T1", "T2"):
        ev = next(r["events"] for r in map(json.loads, open(f"{D}/time-{top}-6000-{pol}.jsonl")) if r.get("kind") == "d2c_events")
        parts = []
        for kind in ("catalog_rebuild_on_grow", "catalog_rebuild_after_compaction", "engine_compaction"):
            v = sorted(e[1] / 1e3 for e in ev if e[0] == kind)
            if v:
                parts.append(f"{kind} n={len(v)} {st.median(v):.0f}/{v[int(0.99 * (len(v) - 1))]:.0f}/{v[-1]:.0f}")
        print(f"  {top:6s} {pol:6s} " + "; ".join(parts))
print("A2: B1 fresh-churn, lifecycle arm window and cell ratio (median, pair min-max), runs in order frozen, T1, T1, frozen")
for nodes in ("1000", "10000"):
    for pol in ("frozen", "T1"):
        rows = []
        for f in sorted(glob.glob(f"{D}/b1/run*-{pol}-{nodes}.jsonl")):
            rows += [r for r in map(json.loads, open(f)) if r.get("kind") == "pair"]
        c = [r["candidate_ns"] for r in rows]; ratio = [r["candidate_ns"] / r["reference_ns"] for r in rows]
        print(f"  {nodes:>6s} {pol:6s} n={len(rows)} lifecycle window median {st.median(c)/1e3:.1f} us (min {min(c)/1e3:.1f}, max {max(c)/1e3:.1f}) | lifecycle/reference median {st.median(ratio):.3f} ({min(ratio):.3f}-{max(ratio):.3f})")
