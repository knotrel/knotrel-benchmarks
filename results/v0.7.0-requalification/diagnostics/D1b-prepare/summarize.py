"""D1b summary: median per sub-phase (us) per arm, pair min-max, coverage of the import total."""
import json, statistics, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
setup = rows[0]; names = setup["phases"]
rounds = [r for r in rows[1:] if not r["warmup"]]
print(f"nodes {setup['nodes']}, registered edges {setup['registered_edges']}, effective edges {setup['effective_edges']}; analyzed rounds {len(rounds)}")
med = lambda xs: statistics.median(xs)
arms = "LFE"
print(f"{'sub-phase':26s}" + "".join(f"{a+' median':>12s}{a+' min-max':>18s}" for a in arms))
for i, name in enumerate(names):
    vals = {a: [r["arms"][a]["phases_ns"][i] / 1000 for r in rounds] for a in arms}
    if all(max(v) == 0 for v in vals.values()):
        continue
    print(f"{name:26s}" + "".join(f"{med(vals[a]):12.1f}{f'{min(vals[a]):.1f}-{max(vals[a]):.1f}':>18s}" for a in arms))
for a in arms:
    tot = [r["arms"][a]["total_ns"] / 1000 for r in rounds]
    cov = [sum(r["arms"][a]["phases_ns"]) / r["arms"][a]["total_ns"] for r in rounds]
    print(f"{a}: import total median {med(tot):.1f} us (min {min(tot):.1f}, max {max(tot):.1f}); sub-phase coverage median {med(cov)*100:.1f}%")
ratio = lambda x, y: [r["arms"][x]["total_ns"] / r["arms"][y]["total_ns"] for r in rounds]
for x, y in (("L", "E"), ("F", "E"), ("L", "F")):
    v = ratio(x, y); print(f"{x}/{y}: median {med(v):.3f} (min {min(v):.3f}, max {max(v):.3f})")
# groups
G = {"parse": [0], "request_checks": [1], "spec_conversion (L)": [2],
     "catalog (nodes, counting+checks, alloc, fill)": [3, 4, 5, 6], "sort_dedup (incl. conflict check)": [7],
     "finish counts/shrink": [8], "effective engine build": [9, 10, 11, 12],
     "plain engine build (add_node + link)": [13, 14], "publish": [15]}
print("grouped medians (sum of per-round group sums, median over rounds), us")
for g, idx in G.items():
    v = {a: med([sum(r["arms"][a]["phases_ns"][i] for i in idx) / 1000 for r in rounds]) for a in arms}
    print(f"  {g:48s} L {v['L']:9.1f}  F {v['F']:9.1f}  E {v['E']:9.1f}")
