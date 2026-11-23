#!/usr/bin/env python3
"""Evaluation of block Q of the v1.0.0 qualification (criteria Q1-Q5).

Plan (knotrel ``docs/releases/v1.0.0-qualification-plan.md`` sections 5.5, 5.7, 6 and 7;
matrix ``v1_0_0.q``). Reads the output directory of ``run_v100q_q.py``: the three rounds of
the candidate (seven cells) and of the Q5 reference arm (v0.9.0 server, L1 G100k C=16 and
C=64), one load-tool invocation per round and side.

- **Q1-Q4** are the approved protocol's criteria with unchanged thresholds, computed by
  ``tool_evaluate``, a line-by-line port of the load tool's ``evaluate`` (knotrel
  ``integrations/postgres-feeder/examples/load.rs``) applied to the candidate's observations
  of the three rounds. The tool itself only ever sees one round per invocation, so its own
  ``summary.json`` cannot hold the three-observation medians; to show that the port is
  faithful, every step's own ``summary.json`` is recomputed from that step's results with the
  port and must match it (``check_port``), otherwise the evaluation stops.
- **Q5** compares, for C=16 and C=64, the candidate's median query throughput and median
  client p99 with the v0.9.0 medians **of this session**: throughput >= 90 % and p99 <= 125 %.
  Q5 against the protocol's frozen v0.8.0 baseline is reported, not deciding.
- **Failures (plan section 5.5).** An observation recorded as failed (``failures.jsonl``,
  not rerun), or whose result lacks a value a criterion needs (for example a feeder that did
  not reach ``ready``), gives every criterion using it no passing value: that criterion is
  FAIL. The tool's own median would silently skip such a value; this rule does not.
- **Cap.** If ``run.json`` says NONCONFORMING (the 30-minute cap), a criterion whose cells
  lack their three observations gets no verdict (``null``) and does not count as PASS; Q is
  then NONCONFORMING as a whole.

Deciding: Q1, Q2, Q4, Q5. Q3 is classified as measured (no acceptance carries over).

    evaluate_v100q_q.py OUT [--baseline-v080 BASELINE-SUMMARY.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_v100q_q as q  # noqa: E402

BASELINE_V080_SHA256 = "bc6e8c094c84a0942d24e4095259d0153f595cb416388afd69392faccc7ef0e6"
DECIDING = ("Q1", "Q2", "Q4", "Q5")
OBSERVATIONS = 3
Q5_CELLS = ("L1 G100k C=16", "L1 G100k C=64")
#: Cells each criterion uses, and the result paths it needs from each of their observations.
USES: Dict[str, Tuple[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]] = {
    "Q1": (("L1 G100k C=16",), (("markers", "p99_ms"), ("markers", "max_ms"))),
    "Q2": (("L1 G100k C=0", "L1 G100k C=16", "L1 G100k C=64", "L1 G10k C=16"),
           (("markers", "first10_median_ms"), ("markers", "last10_median_ms"),
            ("retained_bytes", "start"), ("retained_bytes", "end"))),
    "Q3": (("L2 G100k C=0", "L2 G100k C=16", "L2 G100k C=64"), (("events_per_sec",),)),
    "Q4": (("L2 G100k C=64",), (("secs_to_ready",),)),
    "Q5": (Q5_CELLS, (("queries", "requests_per_sec"), ("queries", "p99_ms"))),
}
L1_STATS = (("marker_p50_ms", ("markers", "p50_ms")), ("marker_p99_ms", ("markers", "p99_ms")),
            ("marker_max_ms", ("markers", "max_ms")), ("marker_timeouts", ("markers", "timeouts")),
            ("first10_median_ms", ("markers", "first10_median_ms")),
            ("last10_median_ms", ("markers", "last10_median_ms")),
            ("writer_changes_per_sec", ("writer", "changes_per_sec")),
            ("query_rps", ("queries", "requests_per_sec")), ("query_p99_ms", ("queries", "p99_ms")),
            ("query_503", ("queries", "refused_503")), ("feeder_503_refusals", ("feeder_503_refusals",)))
L2_STATS = (("events", ("events",)), ("secs_to_ready", ("secs_to_ready",)), ("events_per_sec", ("events_per_sec",)),
            ("query_rps", ("queries", "requests_per_sec")), ("query_p99_ms", ("queries", "p99_ms")),
            ("feeder_503_refusals", ("feeder_503_refusals",)))


# -- port of load.rs ---------------------------------------------------------------------
def flatten(record: Dict[str, Any]) -> Dict[str, Any]:
    """``flatten`` in load.rs: the record with its ``metrics`` merged at the top level."""
    flat = dict(record)
    if isinstance(record.get("metrics"), dict):
        flat.update(record["metrics"])
    return flat


def get(value: Any, path: Sequence[str]) -> Optional[float]:
    """``get`` in load.rs: a number at ``path``, else None (serde ``as_f64``)."""
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def median(values: List[float]) -> Optional[float]:
    """``median`` in load.rs (mean of the two middle values for an even count)."""
    v = sorted(values)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 == 1 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def tool_evaluate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """``evaluate`` in load.rs, unchanged: per-cell medians and ranges, then Q1-Q4."""
    cells: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        cells.setdefault(q.cell_key(r), []).append(r)

    def stat(key: str, path: Sequence[str]) -> Dict[str, Any]:
        vals = [x for x in (get(r, path) for r in cells.get(key, [])) if x is not None]
        return {"median": median(vals), "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                "n": len(vals)}

    summary: Dict[str, Dict[str, Any]] = {}
    for key in sorted(cells):
        summary[key] = {name: stat(key, path) for name, path in (L1_STATS if key.startswith("L1") else L2_STATS)}

    def med(key: str, name: str) -> Optional[float]:
        return summary.get(key, {}).get(name, {}).get("median")

    q1_p99, q1_max = med("L1 G100k C=16", "marker_p99_ms"), med("L1 G100k C=16", "marker_max_ms")
    q1 = q1_p99 is not None and q1_max is not None and q1_p99 <= 1000.0 and q1_max <= 3000.0
    q2, q2_detail = True, []
    for r in results:
        if r.get("scenario") != "L1":
            continue
        first, last = get(r, ("markers", "first10_median_ms")), get(r, ("markers", "last10_median_ms"))
        rs, re_ = get(r, ("retained_bytes", "start")), get(r, ("retained_bytes", "end"))
        lag_ok = first is not None and last is not None and last <= 2.0 * first + 50.0
        wal_ok = rs is not None and re_ is not None and re_ <= rs + 16.0 * 1024.0 * 1024.0
        q2 = q2 and lag_ok and wal_ok
        q2_detail.append({"cell": q.cell_key(r), "rep": r.get("rep"), "lag_ok": lag_ok, "wal_ok": wal_ok})
    r0, r16, r64 = (med(f"L2 G100k C={c}", "events_per_sec") for c in (0, 16, 64))
    q3 = None not in (r0, r16, r64) and r16 >= 0.5 * r0 and r64 >= 0.25 * r0
    t64 = med("L2 G100k C=64", "secs_to_ready")
    q4 = t64 is not None and t64 <= 60.0
    return {"cells": summary, "criteria": {
        "Q1": {"pass": q1, "marker_p99_ms": q1_p99, "marker_max_ms": q1_max,
               "rule": "L1 G100k C=16: p99 <= 1000 ms and max <= 3000 ms"},
        "Q2": {"pass": q2, "observations": q2_detail,
               "rule": "every L1 observation: last10 median <= 2 x first10 median + 50 ms, retained WAL end <= start + 16 MiB"},
        "Q3": {"pass": q3, "rate_c0": r0, "rate_c16": r16, "rate_c64": r64,
               "ratio_c16": r16 / r0 if None not in (r16, r0) else None,
               "ratio_c64": r64 / r0 if None not in (r64, r0) else None,
               "rule": "L2 G100k: C=16 >= 50 % and C=64 >= 25 % of C=0"},
        "Q4": {"pass": q4, "secs_to_ready_c64": t64, "rule": "L2 G100k C=64: time to ready <= 60 s"}}}


def _close(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    return a == b


def check_port(step_dir: Path, records: List[Dict[str, Any]]) -> None:
    """The tool's own per-step summary must equal the port's (cells: median, min, max, n)."""
    path = step_dir / "summary.json"
    if not path.exists():
        return
    tool = json.loads(path.read_text())["summary"]["cells"]
    mine = tool_evaluate(records)["cells"]
    if sorted(tool) != sorted(mine):
        raise SystemExit(f"{step_dir.name}: tool cells {sorted(tool)} differ from the port's {sorted(mine)}")
    for key, stats in tool.items():
        for name, value in stats.items():
            for field in ("median", "min", "max", "n"):
                if not _close(value.get(field), mine[key].get(name, {}).get(field)):
                    raise SystemExit(f"{step_dir.name}: {key} {name}.{field} tool {value.get(field)} != port "
                                     f"{mine[key].get(name, {}).get(field)}: the port is not faithful")


# -- collection --------------------------------------------------------------------------
STEP = re.compile(r"^round(?P<round>[1-3])-(?P<side>candidate|reference)(-cont\d+)?$")


def collect(out: Path) -> Dict[str, Any]:
    """Observations by side and cell (successful records and recorded failures) and the run."""
    run = json.loads((out / "run.json").read_text())
    records: Dict[str, List[Dict[str, Any]]] = {"candidate": [], "reference": []}
    for step_dir in sorted(p for p in out.iterdir() if p.is_dir()):
        match = STEP.match(step_dir.name)
        if not match:
            raise SystemExit(f"unexpected directory {step_dir.name}")
        path = step_dir / "results.jsonl"
        flat = [flatten(json.loads(line)) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
        check_port(step_dir, flat)
        for r in flat:
            r["_round"] = int(match["round"])
        records[match["side"]] += flat
    failures: Dict[str, List[Dict[str, Any]]] = {"candidate": [], "reference": []}
    path = out / "failures.jsonl"
    for line in (path.read_text().splitlines() if path.exists() else []):
        f = json.loads(line)
        if f.get("failed_cell") and not f.get("rerun"):
            failures[f["side"]].append(f)
    return {"run": run, "records": records, "failures": failures}


def criterion_state(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Observation completeness and failures for one criterion (plan sections 5.5 and 9)."""
    cells, paths = USES[name]
    sides = ("candidate", "reference") if name == "Q5" else ("candidate",)
    failed, missing = [], []
    for side in sides:
        for cell in cells:
            obs = [r for r in data["records"][side] if q.cell_key(r) == cell]
            fails = [f for f in data["failures"][side] if f["failed_cell"] == cell]
            for f in fails:
                failed.append(f"{side} {cell}: {f.get('step')} exit {f.get('exit')} ({f.get('classification')})")
            for r in obs:
                for p in paths:
                    if get(r, p) is None:
                        failed.append(f"{side} {cell} round {r['_round']}: no value for {'.'.join(p)}")
            if len(obs) + len(fails) < OBSERVATIONS:
                missing.append(f"{side} {cell}: {len(obs) + len(fails)} of {OBSERVATIONS} observations")
            if len(obs) + len(fails) > OBSERVATIONS:
                raise SystemExit(f"{side} {cell}: {len(obs) + len(fails)} observations, more than {OBSERVATIONS}")
    return {"failed_observations": failed, "missing_observations": missing}


def evaluate(out: Path, baseline_v080: Optional[Path] = None) -> Dict[str, Any]:
    data = collect(out)
    nonconforming = data["run"]["status"] != "COMPLETE"
    cand = tool_evaluate(data["records"]["candidate"])
    ref = tool_evaluate(data["records"]["reference"])
    criteria: Dict[str, Any] = {k: dict(v) for k, v in cand["criteria"].items()}
    q5: Dict[str, Any] = {"rule": "L1 G100k C=16 and C=64: candidate median query_rps >= 90 % and median query_p99_ms "
                                  "<= 125 % of the v0.9.0 medians of this session", "cells": {}}
    q5_pass = True
    for key in Q5_CELLS:
        c, r = cand["cells"].get(key, {}), ref["cells"].get(key, {})
        values = [x.get(m, {}).get("median") for x in (r, c) for m in ("query_rps", "query_p99_ms")]
        if None in values:
            q5["cells"][key] = {"pass": False, "reason": "a median is missing"}
            q5_pass = False
            continue
        ref_rps, ref_p99, cand_rps, cand_p99 = values
        rps_ok, p99_ok = cand_rps / ref_rps >= 0.90, cand_p99 / ref_p99 <= 1.25
        q5["cells"][key] = {"query_rps": [ref_rps, cand_rps], "rps_ratio": cand_rps / ref_rps, "rps_pass": rps_ok,
                            "query_p99_ms": [ref_p99, cand_p99], "p99_ratio": cand_p99 / ref_p99, "p99_pass": p99_ok,
                            "pass": rps_ok and p99_ok}
        q5_pass = q5_pass and rps_ok and p99_ok
    q5["pass"] = q5_pass
    criteria["Q5"] = q5
    for name in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        state = criterion_state(name, data)
        criteria[name].update(state)
        measured = bool(criteria[name]["pass"])
        if state["missing_observations"] and nonconforming:
            criteria[name]["status"] = None  # no verdict: block Q did not conform
        elif state["failed_observations"] or state["missing_observations"]:
            criteria[name]["status"] = "FAIL"  # no passing value (plan section 5.5)
        else:
            criteria[name]["status"] = "PASS" if measured else "FAIL"
    deciding = {k: criteria[k]["status"] for k in DECIDING}
    result: Dict[str, Any] = {
        "block": "Q", "run_status": data["run"]["status"], "run_cause": data["run"]["cause"],
        "q_status": "NONCONFORMING" if nonconforming else "COMPLETE",
        "observations": {side: {k: v["query_rps" if k.startswith("L1") else "events"]["n"] for k, v in s["cells"].items()}
                         for side, s in (("candidate", cand), ("reference", ref))},
        "candidate_cells": cand["cells"], "reference_cells": ref["cells"], "criteria": criteria,
        "deciding": deciding,
        "q_pass": (None if nonconforming else all(v == "PASS" for v in deciding.values())),
        "Q3": {"status": criteria["Q3"]["status"],
               "note": "classified as measured with unchanged thresholds; the v0.9.0 acceptance does not carry over; "
                       "if not PASS it needs a disposition and a documented operational envelope (plan section 8)"},
        "reruns": data["run"].get("reruns", {}),
    }
    if baseline_v080 is not None:
        raw = baseline_v080.read_bytes()
        if hashlib.sha256(raw).hexdigest() != BASELINE_V080_SHA256:
            raise SystemExit("v0.8.0 baseline summary differs from the approved protocol's")
        base = json.loads(raw)["summary"]["cells"]
        desc = {}
        for key in Q5_CELLS:
            c = cand["cells"].get(key, {})
            if c.get("query_rps", {}).get("median") is None or c.get("query_p99_ms", {}).get("median") is None:
                desc[key] = {"reason": "a candidate median is missing"}
                continue
            desc[key] = {"rps_ratio": c["query_rps"]["median"] / base[key]["query_rps"]["median"],
                         "p99_ratio": c["query_p99_ms"]["median"] / base[key]["query_p99_ms"]["median"]}
        result["Q5_v0_8_0"] = {"role": "descriptive, not deciding (campaign report only)", "cells": desc}
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--baseline-v080", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(evaluate(args.out, args.baseline_v080), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
