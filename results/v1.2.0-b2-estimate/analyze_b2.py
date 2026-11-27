#!/usr/bin/env python3
"""Analysis of the B2 impact estimate (knotrel docs/design/b2-bounded-query-concurrency.md,
sections 5, 5.1 and 6, as approved: option B, K = 4).

Inputs per mode (``off``, ``on``): ``E/<mode>/run/Q-evaluation.json`` (the frozen evaluator,
written by run_q.sh) and the raw ``E/<mode>/run/Q/round*-{candidate,reference}/results.jsonl``.

Decision (section 6, option B):
- off: Q1, Q2, Q4 PASS and Q5 PASS (against the in-session v1.1.0 reference); Q3 reported;
- on : Q1, Q2, Q4 PASS and Q3 PASS (C=16 >= 50 %, C=64 >= 25 % of C=0); Q5 computed and
  published as the operational cost, not deciding.

    analyze_b2.py --stop-check E      # exit 0 if the off mode passes its deciding criteria
    analyze_b2.py E > analysis.json
"""
import json
import statistics as st
import sys
from pathlib import Path

CELLS = ("L2 G100k C=0", "L2 G100k C=16", "L2 G100k C=64", "L1 G100k C=16", "L1 G100k C=64")


def evaluation(e, mode):
    path = Path(e) / mode / "run" / "Q-evaluation.json"
    return json.loads(path.read_text()) if path.exists() and path.stat().st_size else None


def raw(e, mode):
    rows = {}
    for side in ("candidate", "reference"):
        for f in sorted((Path(e) / mode / "run" / "Q").glob(f"round*-{side}/results.jsonl")):
            for line in f.read_text().splitlines():
                r = json.loads(line)
                key = f"{r['scenario']} {r['graph']} C={r['clients']}"
                rows.setdefault((side, key), []).append(r["metrics"])
    out = {}
    for (side, key), ms in rows.items():
        if key not in CELLS:
            continue
        q = [m.get("queries") or {} for m in ms]
        med = lambda xs: st.median(xs) if xs else None
        out.setdefault(side, {})[key] = {
            "n": len(ms),
            "events_per_sec": med([m["events_per_sec"] for m in ms if m.get("events_per_sec") is not None]),
            "query_rps": med([x["requests_per_sec"] for x in q if x.get("requests_per_sec") is not None]),
            "query_p99_ms": med([x["p99_ms"] for x in q if x.get("p99_ms") is not None]),
            "query_refused_503": sum(x.get("refused_503", 0) or 0 for x in q),
            "query_errors": sum(x.get("errors", 0) or 0 for x in q),
            "feeder_503_refusals": sum(m.get("feeder_503_refusals", 0) or 0 for m in ms),
            "host_cpu_busy_median": med([m["host_cpu_busy_percent"]["median"] for m in ms
                                         if isinstance(m.get("host_cpu_busy_percent"), dict)]),
        }
    for side, cells in out.items():
        c0 = (cells.get("L2 G100k C=0") or {}).get("events_per_sec")
        for key in ("L2 G100k C=16", "L2 G100k C=64"):
            if c0 and cells.get(key) and cells[key]["events_per_sec"] is not None:
                cells[key]["share_of_c0"] = cells[key]["events_per_sec"] / c0
    return out


def verdicts(ev):
    return {k: ev["criteria"][k].get("status") for k in ("Q1", "Q2", "Q3", "Q4", "Q5")} if ev else None


def mode_passes(mode, v):
    if v is None:
        return False
    need = ("Q1", "Q2", "Q4", "Q5") if mode == "off" else ("Q1", "Q2", "Q3", "Q4")
    return all(v[k] == "PASS" for k in need)


def main():
    if sys.argv[1] == "--stop-check":
        v = verdicts(evaluation(sys.argv[2], "off"))
        print(json.dumps({"off_verdicts": v}))
        raise SystemExit(0 if mode_passes("off", v) else 1)
    e = sys.argv[1]
    result = {"modes": {}}
    for mode in ("off", "on"):
        ev = evaluation(e, mode)
        v = verdicts(ev)
        q3 = ev["criteria"]["Q3"] if ev else {}
        result["modes"][mode] = {
            "verdicts": v, "deciding_pass": mode_passes(mode, v) if ev else None,
            "q3": {k: q3.get(k) for k in ("rate_c0", "rate_c16", "rate_c64", "ratio_c16", "ratio_c64")},
            "q5": ev["criteria"]["Q5"] if ev else None, "run_status": ev.get("run_status") if ev else None,
            "raw": raw(e, mode) if ev else None,
        }
    off, on = result["modes"]["off"], result["modes"]["on"]
    if on["verdicts"]:
        ref = (on["raw"].get("candidate", {}), off["raw"].get("candidate", {}) if off["raw"] else {})
        s_on, s_off = on["q3"]["ratio_c16"], off["q3"]["ratio_c16"]
        result["summary"] = {
            "feeder_recovery_vs_off_c16": (s_on - s_off) / s_off if s_off else None,
            "q3_distance_pp_c16": 100 * (s_on - 0.50) if s_on is not None else None,
            "q5_on_operational_cost": on["q5"],
        }
    if not off["verdicts"]:
        result["decision"] = "INCOMPLETE (no off evaluation)"
    elif not off["deciding_pass"]:
        result["decision"] = "REJECT (off mode fails a deciding criterion; on skipped by protocol)"
    elif not on["verdicts"]:
        result["decision"] = "INCOMPLETE (no on evaluation)"
    else:
        result["decision"] = "ADOPT" if on["deciding_pass"] else "REJECT (on mode fails a deciding criterion)"
    json.dump(result, sys.stdout, indent=1, default=str)
    print()


main()
