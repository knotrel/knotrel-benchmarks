#!/usr/bin/env python3
"""Analysis of the adaptive-BFS impact estimate (knotrel docs/design/adaptive-bfs-impact-
estimate.md, sections 3-5). The frozen analyzers are reused, never re-implemented:

- K1 cells: ``analyze_cf5.classify_paired`` with the #182 matrix's K1 cell definitions
  (24 pairs, [r(7), r(18)], time margin 0.10, TIMER_LIMITED from ``limit_ns``);
- V1 core cells: ``analyze_bc_qualification.evaluate_cell`` with ``analyze_v100q_a.RULES``,
  ``final=True``, on 24 pairs;
- #181 cells: the [min, max] interval of the 6 paired block ratios, as in #181.

    analyze_adaptive.py --validate-attempt1 ATTEMPT1_CAMP     # analyzer check before freeze
    analyze_adaptive.py RUN_DIR [--core-only] > analysis.json # after blocks K, V, L (and F)
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import analyze_bc_qualification as frozen  # noqa: E402
import analyze_cf5 as cf5  # noqa: E402
import analyze_v100q_a as v1a  # noqa: E402

MATRIX = HERE.parent / "v1.2.0-qualification/v120q-matrix.json"
K1_CELLS = {c["id"]: c for c in json.loads(MATRIX.read_text())["cells"] if c["block"] == "K1"}
V1_CORE = [c for c in frozen.QUALIFICATION_CELL_IDS if c.startswith("core_")]
RECOVERY = {
    "R1": "K1-chain-split-rejoin-v1-10000", "R2": "K1-chain-split-rejoin-v1-100000",
    "R3": "K1-cycle-alternatives-v1-10000", "R4": "K1-cycle-alternatives-v1-100000",
    "R5": "K1-components-join-split-v1-10000", "R6": "K1-components-join-split-v1-100000",
    "R7": "K1-sustained-churn-path-v1-100000",
    "R8": "core_sparse_traversal_10k_compact-bfs_warmed",
    "R9": "core_sustained_churn_10k_compact-bfs_warmed",
    "R10": "core_sparse_traversal_10k_compact-workspace_warmed",
}
GAINS_K1 = {"G1": "K1-hub-alternatives-v1-10000", "G2": "K1-hub-alternatives-v1-100000",
            "G9": "K1-dense-bridge-churn-v1-512", "G10": "K1-dense-bridge-churn-v1-2048",
            "G11": "K1-redundant-bridge-churn-v1-512", "G12": "K1-redundant-bridge-churn-v1-2048"}
GAINS_L = {"G3": ("hub", 10000), "G4": ("hub", 100000), "G5": ("sparse", 10000),
           "G6": ("sparse", 100000), "G7": ("ring", 10000), "G8": ("ring", 100000)}
CONCLUSIVE = {"PASS", "REGRESSION"}
METRIC = "workload_wall_ns"


def k_class(cell_id, pairs, cf_arm, ref_arm):
    """pairs: dicts arm -> metrics; returns the frozen CF5 class record for cf against ref."""
    lines = [{"cf": {"metrics": p[cf_arm]}, "ref": {"metrics": p[ref_arm]}} for p in pairs]
    return cf5.classify_paired(K1_CELLS[cell_id], lines)[METRIC]


def v_classes(dirs_phases):
    pairs = []
    for directory, phase in dirs_phases:
        pairs += frozen.load_pairs(Path(directory), phase)
    frozen._check_consistency(pairs)
    out = {}
    for cell_id in V1_CORE:
        cell_pairs = [p for p in pairs if p["cell_id"] == cell_id]
        decision = frozen.evaluate_cell(cell_id, cell_pairs, v1a.RULES, final=True)
        if decision["pairs"] != v1a.PAIRS_PER_CELL:
            raise SystemExit(f"{cell_id}: {decision['pairs']} pairs, expected {v1a.PAIRS_PER_CELL}")
        b = st.median(p["values"]["workload_wall_ns"]["B"] for p in cell_pairs)
        c = st.median(p["values"]["workload_wall_ns"]["C"] for p in cell_pairs)
        decision["absolute_median_ms"] = {"B_v110": b / 1e6, "C_cand": c / 1e6}
        out[cell_id] = decision
    return out


def validate_attempt1(camp):
    camp = Path(camp)
    published = json.loads((HERE.parent / "v1.2.0-qualification/attempt1/cf5-analysis.json").read_text())
    by_cell = {}
    for line in (camp / "session1/raw.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["cell"].startswith("K1") and not r["warmup"]:
            by_cell.setdefault(r["cell"], []).append({"cand": r["cf"]["metrics"], "v110": r["ref"]["metrics"]})
    problems = []
    for cell_id, pairs in sorted(by_cell.items()):
        got = k_class(cell_id, pairs, "cand", "v110")["class"]
        want = published["cells"][cell_id]["metrics"][METRIC]["class"]
        print(f"K1 {cell_id}: recomputed {got}, published {want}")
        if got != want:
            problems.append(cell_id)
    v1pub = {c["cell_id"]: c["status"] for c in
             json.loads((HERE.parent / "v1.2.0-qualification/attempt1/v1-analysis.json").read_text())["cells"]}
    d = camp / "session1/delegated/V1-attempt1"
    for cell_id, dec in v_classes([(d / "raw-main", "main"), (d / "extension/raw-extension", "extension")]).items():
        print(f"V1 {cell_id}: recomputed {dec['status']}, published {v1pub[cell_id]}")
        if dec["status"] != v1pub[cell_id]:
            problems.append(cell_id)
    print("VALIDATION", "OK" if not problems else f"FAILED {problems}")
    return 0 if not problems else 1


def ratio_interval12(xs):
    r = sorted(xs)
    return [r[6], r[17]] if len(r) == 24 else None


def analyze(run, core_only):
    run = Path(run)
    problems = []
    # --- K ---
    pairs = {}
    for line in (run / "raw/K.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("exit") != 0:
            problems.append(f"K exit {r}")
            continue
        pairs.setdefault((r["cell"], r["pair"]), {})[r["arm"]] = r
    by_cell = {}
    for (cell_id, pair), arms in pairs.items():
        if len({a["fingerprint"] for a in arms.values()}) != 1:
            problems.append(f"K fingerprint mismatch {cell_id} pair {pair}")
        if pair >= 0 and set(arms) == {"v110", "bfs196", "cand"}:
            by_cell.setdefault(cell_id, []).append({k: {METRIC: v[METRIC]} for k, v in arms.items()})
    k = {}
    for cell_id in K1_CELLS:
        ps = by_cell.get(cell_id, [])
        med = {a: (st.median(p[a][METRIC] for p in ps) / 1e6 if ps else None) for a in ("v110", "bfs196", "cand")}
        def rat(x, y):
            rs = [p[x][METRIC] / p[y][METRIC] for p in ps]
            return {"median": st.median(rs) if rs else None, "interval_r7_r18": ratio_interval12(rs)}
        k[cell_id] = {"pairs": len(ps), "median_ms": med,
                      "cand_vs_v110": k_class(cell_id, ps, "cand", "v110") if len(ps) >= 24 else {"class": "INCOMPLETE"},
                      "ratios": {"cand/v110": rat("cand", "v110"), "cand/bfs196": rat("cand", "bfs196"),
                                 "bfs196/v110": rat("bfs196", "v110")}}
    # --- V ---
    try:
        v = v_classes([(run / "raw/V/block1", "extension"), (run / "raw/V/block2", "extension")])
    except (SystemExit, frozen.AnalysisError, FileNotFoundError) as error:
        v = {}
        problems.append(f"V analysis: {error}")
    # --- L ---
    lres = {}
    for g, (topo, n) in GAINS_L.items():
        per = {a: [] for a in ("v110", "bfs196", "cand")}
        for block in range(1, 7):
            for arm in per:
                path = run / "raw/L" / f"{topo}-{n}-{arm}-b{block}.jsonl"
                if not path.exists():
                    continue
                recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
                if any(x.get("kind") == "verify" and not x.get("match") for x in recs):
                    problems.append(f"L verify mismatch {path.name}")
                ps = [x["candidate_ns"] for x in recs if x.get("kind") == "pair"]
                per[arm].append(st.median(ps) if ps else None)
        complete = [i for i in range(len(per["cand"])) if all(len(per[a]) > i and per[a][i] for a in per)]
        def rr(x, y):
            rs = [per[x][i] / per[y][i] for i in complete]
            return {"median": st.median(rs), "interval_min_max": [min(rs), max(rs)]} if rs else None
        lres[g] = {"topology": topo, "nodes": n, "blocks": len(complete),
                   "median_ms": {a: st.median(per[a][i] for i in complete) / 1e6 for a in per} if complete else None,
                   "cand/v110": rr("cand", "v110"), "cand/bfs196": rr("cand", "bfs196"),
                   "bfs196/v110": rr("bfs196", "v110")}
    # --- criteria ---
    recovery = {}
    for r_id, cell_id in RECOVERY.items():
        if cell_id in k:
            cls = k[cell_id]["cand_vs_v110"].get("class")
        else:
            cls = v.get(cell_id, {}).get("status", "MISSING")
        recovery[r_id] = {"cell": cell_id, "class": cls}
    others = {c: k[c]["cand_vs_v110"].get("class") for c in K1_CELLS if c not in RECOVERY.values()}
    nonconclusive = [r for r, x in recovery.items() if x["class"] not in CONCLUSIVE]
    c2 = (not any(x["class"] == "REGRESSION" for x in recovery.values()) and len(nonconclusive) <= 1
          and not any(c == "REGRESSION" for c in others.values()))
    gains = {}
    for g, cell_id in GAINS_K1.items():
        m = k[cell_id]["median_ms"]
        iv = k[cell_id]["ratios"]["cand/v110"]["interval_r7_r18"]
        gains[g] = {"cell": cell_id, "median_ms": m,
                    "retained": (math.log(m["v110"] / m["cand"]) / math.log(m["v110"] / m["bfs196"])) if m["cand"] else None,
                    "cand_faster_than_v110": bool(iv and iv[1] < 0.90)}
    for g, x in lres.items():
        m = x["median_ms"]
        gains[g] = {"cell": f"#181 {x['topology']} {x['nodes']}", "median_ms": m,
                    "retained": (math.log(m["v110"] / m["cand"]) / math.log(m["v110"] / m["bfs196"])) if m else None,
                    "cand_faster_than_v110": bool(x["cand/v110"] and x["cand/v110"]["interval_min_max"][1] < 0.90)}
    guards = {c: k[c]["cand_vs_v110"].get("class") for c in ("K1-sustained-churn-blocks-v1-10000", "K1-sustained-churn-blocks-v1-100000")}
    c3 = all(x["retained"] is not None and x["retained"] >= 0.80 and x["cand_faster_than_v110"] for x in gains.values()) \
        and not any(c == "REGRESSION" for c in guards.values())
    c1_runs = not problems
    result = {"problems": problems, "K": k, "V": v, "L": lres, "recovery": recovery,
              "nonconclusive_recovery": nonconclusive, "other_k1_vs_v110": others, "gains": gains,
              "guards": guards, "criteria": {"C1_runs": c1_runs, "C2": c2, "C3": c3}}
    if not core_only:
        result["F"] = feeder(run, problems)
        result["criteria"]["C4"] = result["F"].get("C4")
    core_reject = not (c1_runs and c2 and c3)
    result["core_decides_reject"] = core_reject
    return result


def feeder(run, problems):
    shares = {}
    for arm in ("v110", "bfs196", "cand"):
        rates = {0: [], 16: [], 64: []}
        for rep in (1, 2, 3):
            res = run / "raw/F" / f"{arm}-r{rep}" / "results.jsonl"
            if not res.exists():
                problems.append(f"F missing {res.parent.name}")
                continue
            for line in res.read_text().splitlines():
                r = json.loads(line)
                if (r.get("queries") or {}).get("errors"):
                    problems.append(f"F query errors {res.parent.name}")
                if r.get("scenario") == "L2" and r.get("clients") in rates:
                    rate = (r.get("metrics") or {}).get("events_per_sec")
                    if rate is not None:
                        rates[r["clients"]].append(rate)
        if all(rates.values()):
            c0 = st.median(rates[0])
            shares[arm] = {"rates": rates, "c16_share": st.median(rates[16]) / c0, "c64_share": st.median(rates[64]) / c0}
    out = {"shares": shares}
    if {"v110", "bfs196", "cand"} <= set(shares):
        s = {a: shares[a]["c16_share"] for a in shares}
        out["C4"] = s["cand"] >= 0.90 * s["bfs196"]
        out["recovery_kept_vs_bfs196"] = (s["cand"] - s["v110"]) / (s["bfs196"] - s["v110"])
        out["q3_distance_pp_c16"] = 100 * (s["cand"] - 0.50)
        out["q3_c64_share"] = shares["cand"]["c64_share"]
    return out


if __name__ == "__main__":
    if sys.argv[1] == "--validate-attempt1":
        raise SystemExit(validate_attempt1(sys.argv[2]))
    json.dump(analyze(sys.argv[1], "--core-only" in sys.argv), sys.stdout, indent=1, default=str)
    print()
