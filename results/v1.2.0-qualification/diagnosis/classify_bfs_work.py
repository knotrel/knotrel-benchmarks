#!/usr/bin/env python3
"""D2 of the knotrel#182 BFS regression diagnosis (PROTOCOL.md): joins the D1 work counts
with the attempt-1 K1 and V1 timings (medians of the paired runs, no new timing) and applies
the protocol's decision rules per cell and query kind.

    classify_bfs_work.py WORK.json RAW.jsonl V1_DIR > d2.json
"""
import glob
import json
import statistics as st
import sys
from collections import defaultdict

work_path, raw_path, v1_dir = sys.argv[1:]
work = {(w["workload"], w["config"]["nodes"]): w["work"] for w in json.load(open(work_path))}
times = defaultdict(list)  # (source, workload, nodes, kind, arm) -> totals
for line in open(raw_path):
    r = json.loads(line)
    if r["warmup"] or not r["cell"].startswith("K1"):
        continue
    for arm, name in (("cf", "new"), ("ref", "old")):
        o = r[arm]["object"]
        rep = o["repetitions"][0]
        for kind in ("query_true", "query_false"):
            if rep.get(kind):
                times[("K1", o["workload"], o["config"]["nodes"], kind, name)].append(rep[kind]["total_ns"])
for f in glob.glob(f"{v1_dir}/raw-main/pair_*_core_*compact-bfs*.json") + \
         glob.glob(f"{v1_dir}/extension/raw-extension/pair_*_core_*compact-bfs*.json"):
    d = json.load(open(f))
    for o in d["observations"]:
        pm = o.get("parsed_metrics") or {}
        if not pm:
            continue
        nodes = int(o["argv"][o["argv"].index("--nodes") + 1])
        for kind in ("query_true", "query_false"):
            if kind in pm:
                times[("V1", pm["workload"], nodes, kind, "new" if o["label"] == "C" else "old")].append(pm[kind]["total_ns"])
rows = []
for (src, wl, n, kind, arm) in sorted({k[:4] + ("old",) for k in times}):
    w = work.get((wl, n))
    old, new = times.get((src, wl, n, kind, "old")), times.get((src, wl, n, kind, "new"))
    if not w or not old or not new:
        continue
    wo, wn = w[kind]["old"], w[kind]["new"]
    if not wo["entries"] or not wn["entries"]:
        continue
    to, tn = st.median(old), st.median(new)
    R = tn / to
    W = wn["entries"] / wo["entries"]
    c_ratio = (tn / wn["entries"]) / (to / wo["entries"])
    if R <= 1:
        verdict = "faster (not classified)"
    elif W >= 0.8 * R:
        verdict = "H-work"
    elif W <= 1.2 and c_ratio >= 1.5:
        verdict = "H-const"
    else:
        verdict = "mixed"
    rows.append({"source": src, "workload": wl, "nodes": n, "kind": kind, "queries": wo["queries"],
                 "time_old_ms": to / 1e6, "time_new_ms": tn / 1e6, "R": R,
                 "entries_old": wo["entries"], "entries_new": wn["entries"], "W": W,
                 "ns_per_entry_old": to / wo["entries"], "ns_per_entry_new": tn / wn["entries"],
                 "c_ratio": c_ratio, "layers_new": wn["layers"],
                 "entries_per_layer_new": wn["entries"] / max(wn["layers"], 1), "verdict": verdict})
json.dump(rows, sys.stdout, indent=1)
print()
for r in rows:
    print(f"{r['source']} {r['workload'][:-3]:24s} {r['nodes']:>6} {r['kind'][6:]:5s} "
          f"t {r['time_old_ms']:8.3f}->{r['time_new_ms']:8.3f}ms R={r['R']:5.2f} W={r['W']:6.3f} "
          f"ns/entry {r['ns_per_entry_old']:5.2f}->{r['ns_per_entry_new']:6.2f} c={r['c_ratio']:5.2f} "
          f"ent/layer={r['entries_per_layer_new']:7.1f} {r['verdict']}", file=sys.stderr)
