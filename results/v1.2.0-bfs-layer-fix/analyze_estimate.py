#!/usr/bin/env python3
"""Analysis of the bidirectional-BFS per-layer fix impact estimate (knotrel
docs/design/bidirectional-bfs-layer-fix-impact-estimate.md): verdicts per cell, the decision
rule, and the descriptive fix-against-v1.1.0 view next to the frozen K1 tolerance.

    analyze_estimate.py E > analysis.json
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

E = Path(sys.argv[1])
PATH_LIKE = {"chain-split-rejoin-v1", "cycle-alternatives-v1", "components-join-split-v1",
             "sustained-churn-path-v1"}
LOW_DIAMETER = {"hub-alternatives-v1", "dense-bridge-churn-v1", "redundant-bridge-churn-v1"}


def verdict(lo, hi):
    if hi < 0.90:
        return "FASTER"
    if lo > 1.10:
        return "SLOWER"
    if lo >= 0.90 and hi <= 1.10:
        return "NEUTRAL"
    return "INCONCLUSIVE"


def interval12(ratios):
    r = sorted(ratios)
    return r[2], r[9]


problems = []
# --- A ---
a = defaultdict(dict)  # (wl, n) -> block -> arm -> record
for line in open(E / "raw/A.jsonl"):
    rec = json.loads(line)
    if rec["exit"] != 0:
        problems.append(f"A exit {rec['exit']}: {rec['workload']} {rec['nodes']} {rec['arm']} b{rec['block']}")
        continue
    a[(rec["workload"], rec["nodes"])].setdefault(rec["block"], {})[rec["arm"]] = rec
cells_a = []
for (wl, n), blocks in a.items():
    fps = {r["fingerprint"] for b in blocks.values() for r in b.values()}
    if len(fps) != 1:
        problems.append(f"A fingerprints differ: {wl} {n}")
    full = [b for b in blocks.values() if {"prev", "fix", "v110"} <= set(b)]
    if len(full) != 12:
        problems.append(f"A {wl} {n}: {len(full)} complete blocks")
    rp = [b["fix"]["workload_wall_ns"] / b["prev"]["workload_wall_ns"] for b in full]
    rv = [b["fix"]["workload_wall_ns"] / b["v110"]["workload_wall_ns"] for b in full]
    rpv = [b["prev"]["workload_wall_ns"] / b["v110"]["workload_wall_ns"] for b in full]
    lo, hi = interval12(rp)
    vlo, vhi = interval12(rv)
    med = lambda arm: st.median(b[arm]["workload_wall_ns"] for b in full) / 1e6
    cells_a.append({
        "workload": wl, "nodes": n,
        "set": "path-like" if wl in PATH_LIKE else "low-diameter" if wl in LOW_DIAMETER else "blocks",
        "median_ms": {arm: med(arm) for arm in ("v110", "prev", "fix")},
        "fix_vs_prev": {"median": st.median(rp), "interval": [lo, hi], "verdict": verdict(lo, hi)},
        "fix_vs_v110": {"median": st.median(rv), "interval": [vlo, vhi],
                        "k1_tolerance": "time margin 0.10: REGRESSION-like if lo > 1.10, PASS-like if hi <= 1.10",
                        "reading": "above tolerance" if vlo > 1.10 else "within tolerance" if vhi <= 1.10 else "undecided"},
        "prev_vs_v110_median": st.median(rpv),
    })
cells_a.sort(key=lambda c: ([*PATH_LIKE, *LOW_DIAMETER].index(c["workload"]) if c["workload"] in PATH_LIKE | LOW_DIAMETER else 99, c["nodes"]))
# --- B ---
cells_b = []
for topo in ("sparse", "ring", "hub"):
    for n in (10000, 100000):
        ratios, meds = [], {"prev": [], "fix": []}
        for block in range(1, 7):
            per = {}
            for arm in ("prev", "fix"):
                path = E / "raw/B" / f"{topo}-{n}-{arm}-b{block}.jsonl"
                recs = [json.loads(l) for l in open(path) if l.strip()]
                for r in recs:
                    if r.get("kind") == "verify" and not r.get("match"):
                        problems.append(f"B verify mismatch {path.name}")
                pairs = [r["candidate_ns"] for r in recs if r.get("kind") == "pair"]
                if not pairs:
                    problems.append(f"B no pairs {path.name}")
                    continue
                per[arm] = st.median(pairs)
                meds[arm].append(per[arm])
            if len(per) == 2:
                ratios.append(per["fix"] / per["prev"])
        lo, hi = (min(ratios), max(ratios)) if ratios else (None, None)
        cells_b.append({"topology": topo, "nodes": n,
                        "median_ms": {k: st.median(v) / 1e6 for k, v in meds.items() if v},
                        "median_ratio": st.median(ratios) if ratios else None,
                        "interval": [lo, hi], "verdict": verdict(lo, hi) if ratios else "MISSING"})
# --- C ---
c = {"prev": {"C0": [], "C16": []}, "fix": {"C0": [], "C16": []}}
cdir = E / "raw/C"
for arm in ("prev", "fix"):
    for rep in (1, 2, 3):
        res = cdir / f"{arm}-r{rep}" / "results.jsonl"
        if not res.exists():
            problems.append(f"C missing {res}")
            continue
        for line in open(res):
            r = json.loads(line)
            key = {0: "C0", 16: "C16"}.get(r.get("clients")) if r.get("scenario") == "L2" else None
            rate = (r.get("metrics") or {}).get("events_per_sec")
            if (r.get("metrics") or {}).get("queries", {}).get("errors") or (r.get("queries") or {}).get("errors"):
                problems.append(f"C query errors {res}")
            if key and rate is not None:
                c[arm][key].append(rate)
feeder = {}
for arm in ("prev", "fix"):
    if c[arm]["C0"] and c[arm]["C16"]:
        feeder[arm] = {"C0": c[arm]["C0"], "C16": c[arm]["C16"],
                       "share_c16": st.median(c[arm]["C16"]) / st.median(c[arm]["C0"])}
# --- decision ---
path = [x for x in cells_a if x["set"] == "path-like"]
guard_cells = [x["fix_vs_prev"]["verdict"] for x in cells_a if x["set"] != "path-like"] + [x["verdict"] for x in cells_b]
all_verdicts = [x["fix_vs_prev"]["verdict"] for x in cells_a] + [x["verdict"] for x in cells_b]
rule = {
    "1_correctness_runs": not problems,
    "2_path_like": sum(x["fix_vs_prev"]["verdict"] == "FASTER" for x in path) >= 6
                   and not any(x["fix_vs_prev"]["verdict"] == "SLOWER" for x in path),
    "3_no_loss": "SLOWER" not in guard_cells and all_verdicts.count("INCONCLUSIVE") <= 2,
    "4_feeder": (feeder.get("fix", {}).get("share_c16", 0) >= 0.90 * feeder["prev"]["share_c16"])
                if "prev" in feeder and "fix" in feeder else None,
}
decision = "ADOPT" if all(v is True for v in rule.values()) else "REJECT or incomplete"
json.dump({"problems": problems, "A": cells_a, "B": cells_b, "C": feeder, "rule": rule,
           "decision_runs": decision,
           "note": "rule 1 also needs CI on knotrel#202 (checked separately)"}, sys.stdout, indent=1)
print()
