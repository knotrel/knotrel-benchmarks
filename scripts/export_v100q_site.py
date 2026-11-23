#!/usr/bin/env python3
"""Exports the v1.0.0 qualification results to the benchmark site's schema (plan section 11).

``docs/SITE.md``: "Add an adapter/export from a campaign analyzer rather than manually
transcribing measurements." This is that adapter. It reads only the frozen analyzers'
outputs, never raw data, and recomputes no verdict:

- A (``analyze_v100q_a.py``): one row per cell for the primary metric with the cell's class,
  and one row per gated supporting metric with that metric's class;
- B4 (``analyze_v100q_bc.py`` numbers, ``report_v100q_bc.py`` roles and statuses): deciding
  cells and the descriptive frozen counterparts (``role``); the two not-equivalent cells (E6)
  go to the campaign report only;
- C (same files): C3 and C4 rows (late over early maximum of the lifecycle arm against the
  1.25 budget); C1 and C2 (rules checked at every checkpoint, no single estimate) go to the
  campaign report only;
- R, Rmem, M_reg (``analyze_v100q.py``); Q1, Q3, Q4 and Q5 (``evaluate_v100q_q.py``); Q2 (a
  rule on every observation) goes to the campaign report only, as do Q5 against v0.8.0 and
  any criterion without a verdict.

Intervals (plan section 11): ``delta_ci95`` holds the frozen order-statistic interval of the
median paired change, converted to percent; ``ci_method`` names it exactly with its coverage
(97.73 % at n = 24, 96.14 % at n = 12): it is **not** a 95 % interval and the field name does
not make it one. Rmem and Q rows have no interval, with the plan's reason. B4 and C rows say
that their reference is an arm of the candidate build, not v0.9.0. Rows whose reference
column holds a threshold say so (``reference_kind: "threshold"``).

**Fail closed.** The site schema (``scripts/build_site.py``) accepts the verdicts PASS, FAIL,
REGRESSION, INCONCLUSIVE, INVALID and NOT_EQUIVALENT. A measured class outside that list
(INCONCLUSIVE_DISCLOSED, UNRESOLVED, TIMER_LIMITED, EXCEEDS_BUDGET, not run, ...) is never
mapped onto another verdict: the export stops and names it, so the schema is extended first
(a maintainer decision). The output is validated with ``build_site.validate``.

**Never publishes.** It requires the decision record (``--decision``) to exist, writes the
whole dataset with the 1.0.0 entry ``published`` to ``--out``, which must lie outside
``docs/``, and the excluded items to ``--report-only``. Copying the result into
``docs/data/releases.json`` is a separate, reviewed change.

    export_v100q_site.py --freeze FREEZE.json --decision DECISION.md --a A.json --bc BC.json \\
        --bc-report REPORT.json --r R.json --rmem RMEM.json --mreg MREG.json --q Q.json \\
        --campaign-url URL --evidence-url URL --environment TEXT \\
        --releases docs/data/releases.json --out OUT.json --report-only EXCLUDED.json
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import build_site  # noqa: E402
from cli_paths import confined  # noqa: E402

VERSION = "1.0.0"
SITE_VERDICTS = ("PASS", "FAIL", "REGRESSION", "INCONCLUSIVE", "INVALID", "NOT_EQUIVALENT")
CI_24 = ("distribution-free interval for the median of 24 paired log ratios ln(C/B): one-based order "
         "statistics [r(7), r(18)], coverage 97.73 % (1 - 2 P(Bin(24, 1/2) <= 6)); not a 95 % interval; "
         "converted to percent")
CI_12 = ("distribution-free interval for the median of 12 paired log ratios ln(C/B): one-based order "
         "statistics [r(3), r(10)], coverage 96.14 % (1 - 2 P(Bin(12, 1/2) <= 2)); not a 95 % interval; "
         "converted to percent")
WITHIN = "; the reference is an arm within the candidate build (lifecycle against its reference arm), not v0.9.0"
NO_ABS = "the campaign estimates the paired relative change only; no interval is computed for the absolute medians"
RMEM_REASON = "deterministic counts, one run per arm"
Q_REASON = "3 observations; the protocol reports the median and range"
C_REASON = "one run per arm and cell; C3/C4 are rules on one 30-cycle series, not estimates with an interval"


class ExportError(ValueError):
    """The inputs cannot be exported without changing a verdict or inventing a value."""


def pct(log_value: float) -> float:
    return (math.exp(log_value) - 1.0) * 100.0


def unit_of(metric: str) -> str:
    if metric.endswith("_ns") or metric.endswith(".p99") or metric.startswith("latency_ns"):
        return "ns"
    if metric.endswith("_ms"):
        return "ms"
    if metric.endswith("_bytes") or metric in ("peak_after", "live_after", "max_net_live", "max_net_peak",
                                               "transient_over_final"):
        return "bytes"
    if metric == "requests_per_s":
        return "requests/s"
    return "value"


def row(scenario: str, metric: str, unit: str, direction: str, candidate: float, reference: float, runs: int,
        verdict: Any, ci_method: str, evidence: str, delta_ci: Optional[Sequence[float]] = None,
        reason: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"scenario": scenario, "metric": metric, "unit": unit, "direction": direction,
                           "candidate": candidate, "reference": reference,
                           "delta_pct": 100.0 * (candidate / reference - 1.0) if reference else None,
                           "candidate_ci95": None, "reference_ci95": None,
                           "delta_ci95": list(delta_ci) if delta_ci is not None else None,
                           "runs": runs, "verdict": verdict, "ci_method": ci_method, "evidence_url": evidence}
    out["ci_unavailable_reason"] = reason or NO_ABS
    out.update(extra)
    return out


def a_rows(a: Dict[str, Any], evidence: str) -> List[Dict[str, Any]]:
    if a.get("pairs_per_cell") != 24 or a.get("phase") != "final":
        raise ExportError("A analysis is not the fixed n = 24 final decision (analyze_v100q_a.py)")
    rows = []
    for cell in a["cells"]:
        p = cell["primary"]
        rows.append(row(cell["cell_id"], p["metric"], unit_of(p["metric"]), "lower", p["C_median"], p["B_median"],
                        p["pairs"], cell["status"], CI_24, evidence, p["interval_pct"], experiment="A",
                        role="deciding", metric_status=p["status"]))
        for m in cell["supporting"]:
            if m["status"] == "REPORT_ONLY":
                continue
            rows.append(row(f"{cell['cell_id']} (supporting)", m["metric"], unit_of(m["metric"]), "lower",
                            m["C_median"], m["B_median"], m["pairs"], m["status"], CI_24, evidence,
                            m["interval_pct"], experiment="A", role="deciding (supporting metric)"))
    return rows


def a_report_only(a: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"id": f"{c['cell_id']}:{m['metric']}", "status": m["status"], "reason": m.get("report_only_reason")}
            for c in a["cells"] for m in c["supporting"] if m["status"] == "REPORT_ONLY"]


def bc_rows(bc: Dict[str, Any], report: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    timing = {t["id"]: t for t in bc["timing"]}
    sustained = {s["id"]: s for s in bc["sustained"]}
    rows, excluded = [], []
    for r in report["rows"]:
        if r["kind"] == "timing":
            t = timing[r["id"]]
            if r["role"] == "not_equivalent":
                excluded.append({"id": r["id"], "status": "no verdict (E6, unqualified)", "measured_status": r["status"],
                                 "reason": "not equivalent: indicative evidence in the campaign report only"})
                continue
            role = "deciding" if r["role"] == "deciding" else "descriptive frozen counterpart (disclosure, no release verdict)"
            rows.append(row(r["id"] if r["role"] == "deciding" else f"{r['id']} (descriptive)", "window_ns", "ns", "lower",
                            t["C_median"], t["B_median"], t["pairs"], r["status"], CI_12 + WITHIN, evidence,
                            t["interval_pct"], experiment=t["experiment"], role=role))
        elif r["kind"] in ("C3", "C4"):
            cell_id = r["id"].rsplit(":", 1)[0]
            s = sustained[cell_id]
            rows.append(row(f"{cell_id} {r['kind']} (late over early max; slope rule in the campaign report)",
                            f"{s['metric']} max(cycles 21-30) / max(cycles 1-10)", "ratio", "lower",
                            s["late_over_early"], 1.25, 1, r["status"], "none: " + C_REASON + WITHIN, evidence,
                            None, C_REASON, experiment="C", role="deciding" if r["kind"] == "C3" else "disclosure (C4)",
                            reference_kind="threshold"))
        elif r["kind"] in ("C1", "C2"):
            excluded.append({"id": r["id"], "status": r["status"],
                             "reason": "rule checked at every checkpoint; no single numeric estimate (campaign report)"})
        else:
            excluded.append({"id": r["id"], "status": r["status"], "reason": f"{r['kind']}: core-rule row, campaign report"})
    return rows, excluded


def r_rows(r: Dict[str, Any], evidence: str) -> List[Dict[str, Any]]:
    return [row(cell_id, s["metric"], unit_of(s["metric"]), "lower", s["C_median"], s["B_median"], s["pairs"],
                s["status"], CI_12, evidence, s["interval_pct"], experiment="R", role="deciding",
                improved=s.get("verdict") == "PASS (IMPROVED)")
            for cell_id, s in r.items()]


def rmem_rows(rmem: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows, excluded = [], []
    for cell_id, cell in rmem.items():
        for metric, m in cell["metrics"].items():
            if not m["ref"]:
                excluded.append({"id": f"{cell_id}:{metric}", "status": m["verdict"],
                                 "reason": "reference count is zero: no ratio (campaign report)"})
                continue
            rows.append(row(cell_id, metric, unit_of(metric), "lower", m["cand"], m["ref"], 1, m["verdict"],
                            "none: deterministic allocator counts, REGRESSION if candidate > reference x 1.20",
                            evidence, None, RMEM_REASON, experiment="Rmem", role="deciding"))
    return rows, excluded


def mreg_rows(mreg: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows, excluded = [], []
    for cell_id, cell in mreg.get("result", mreg).items():
        if not cell.get("metrics"):
            excluded.append({"id": cell_id, "status": cell.get("verdict"),
                             "reason": "no metrics in the analysis (an invalid observation): campaign report"})
            continue
        for metric, s in cell["metrics"].items():
            lo, hi = s["interval_log"]
            if s["direction"] == "higher_is_better":  # analyzed as ln(ref/cand)
                cand, ref, ci, direction = s["B_median"], s["C_median"], [pct(-hi), pct(-lo)], "higher"
            else:
                cand, ref, ci, direction = s["C_median"], s["B_median"], [pct(lo), pct(hi)], "lower"
            rows.append(row(cell_id, metric, unit_of(metric), direction, cand, ref, s["pairs"],
                            cell["verdict"] if cell["verdict"] == "INVALID" else s["status"],
                            CI_12 + " (for higher-is-better metrics the analyzed ratio is reference/candidate; "
                                    "shown here as candidate/reference)", evidence, ci,
                            experiment="M_reg", role="deciding", cell_verdict=cell["verdict"]))
    return rows, excluded


def q_rows(q: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    crit = q["criteria"]
    rows, excluded = [], []
    method = "none: " + Q_REASON

    def add(name: str, scenario: str, metric: str, unit: str, direction: str, cand: Any, ref: Any, verdict: Any,
            **extra: Any) -> None:
        if verdict is None or cand is None or ref in (None, 0):
            excluded.append({"id": f"{name}:{scenario}:{metric}", "status": verdict,
                             "reason": "no verdict or no value (block Q NONCONFORMING or a failed observation)"})
            return
        rows.append(row(scenario, metric, unit, direction, cand, ref, 3, verdict, method, evidence, None, Q_REASON,
                        experiment="Q", criterion=name, **extra))

    s1 = crit["Q1"]["status"]
    add("Q1", "Q1 L1 G100k C=16 (reference = threshold)", "marker lag p99 (median of observations)", "ms", "lower",
        crit["Q1"].get("marker_p99_ms"), 1000.0, s1, reference_kind="threshold", role="deciding")
    add("Q1", "Q1 L1 G100k C=16 (reference = threshold)", "marker lag max (median of observations)", "ms", "lower",
        crit["Q1"].get("marker_max_ms"), 3000.0, s1, reference_kind="threshold", role="deciding")
    excluded.append({"id": "Q2", "status": crit["Q2"]["status"],
                     "reason": "a rule on every L1 observation (lag and retained WAL): campaign report"})
    s3 = crit["Q3"]["status"]
    add("Q3", "Q3 L2 G100k C=16 over C=0 (reference = threshold)", "catch-up rate ratio", "ratio", "higher",
        crit["Q3"].get("ratio_c16"), 0.5, s3, reference_kind="threshold", role="classified as measured")
    add("Q3", "Q3 L2 G100k C=64 over C=0 (reference = threshold)", "catch-up rate ratio", "ratio", "higher",
        crit["Q3"].get("ratio_c64"), 0.25, s3, reference_kind="threshold", role="classified as measured")
    add("Q4", "Q4 L2 G100k C=64 (reference = threshold)", "time to ready (median of observations)", "s", "lower",
        crit["Q4"].get("secs_to_ready_c64"), 60.0, crit["Q4"]["status"], reference_kind="threshold", role="deciding")
    s5 = crit["Q5"]["status"]
    clean = not crit["Q5"].get("failed_observations") and not crit["Q5"].get("missing_observations")
    for key, cell in crit["Q5"]["cells"].items():
        if "query_rps" not in cell:
            excluded.append({"id": f"Q5:{key}", "status": s5, "reason": cell.get("reason", "missing median")})
            continue
        rps_v = ("PASS" if cell["rps_pass"] else "FAIL") if clean and s5 is not None else s5
        p99_v = ("PASS" if cell["p99_pass"] else "FAIL") if clean and s5 is not None else s5
        add("Q5", f"Q5 {key} (reference = v0.9.0, same session)", "query throughput (median)", "requests/s", "higher",
            cell["query_rps"][1], cell["query_rps"][0], rps_v, role="deciding", threshold="candidate >= 90 % of reference")
        add("Q5", f"Q5 {key} (reference = v0.9.0, same session)", "client p99 (median)", "ms", "lower",
            cell["query_p99_ms"][1], cell["query_p99_ms"][0], p99_v, role="deciding", threshold="candidate <= 125 % of reference")
    if "Q5_v0_8_0" in q:
        excluded.append({"id": "Q5 against v0.8.0", "status": "descriptive", "reason": "reported, not deciding (plan section 11)",
                         "values": q["Q5_v0_8_0"]})
    return rows, excluded


def build(inputs: Dict[str, Any], urls: Dict[str, str], environment: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    freeze = inputs["freeze"]
    ev = urls["evidence"]
    rows = a_rows(inputs["a"], ev)
    excluded = a_report_only(inputs["a"])
    for part in (bc_rows(inputs["bc"], inputs["bc_report"], ev), rmem_rows(inputs["rmem"], ev),
                 mreg_rows(inputs["mreg"], ev), q_rows(inputs["q"], ev)):
        rows += part[0]
        excluded += part[1]
    rows += r_rows(inputs["r"], ev)
    outside = sorted({str(r["verdict"]) for r in rows if r["verdict"] not in SITE_VERDICTS})
    if outside:
        raise ExportError(f"measured classes outside the site schema's verdicts {SITE_VERDICTS}: {outside} "
                          f"(rows: {[r['scenario'] for r in rows if r['verdict'] not in SITE_VERDICTS][:8]}); "
                          "they are never mapped onto another verdict: extend the schema first (maintainer decision)")
    ref = freeze["reference"]
    version = str(ref.get("tag", "")).lstrip("v")
    comparison = {"candidate_sha": freeze["candidate"]["commit"], "reference_version": version,
                  "reference_sha": ref["commit"], "campaign_url": urls["campaign"], "environment": environment,
                  "results": rows}
    return comparison, excluded


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("freeze", "decision", "a", "bc", "bc-report", "r", "rmem", "mreg", "q", "releases", "out", "report-only"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("campaign-url", "evidence-url", "environment"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    for name in ("freeze", "decision", "a", "bc", "bc_report", "r", "rmem", "mreg", "q", "releases", "out",
                 "report_only"):
        setattr(args, name, confined(getattr(args, name), f"--{name.replace('_', '-')}"))
    if not args.decision.is_file() or not args.decision.read_text().strip():
        parser.error("the decision record does not exist: the 1.0.0 entry is published only after it (plan section 11)")
    docs = (REPO / "docs").resolve()
    for out in (args.out, args.report_only):
        resolved = out.resolve()
        if resolved == docs or docs in resolved.parents:
            parser.error(f"{out} is inside docs/: this exporter never publishes; copy the reviewed output separately")
        if out.exists():
            parser.error(f"{out} already exists")
    load = lambda p: json.loads(p.read_text())  # noqa: E731
    inputs = {"freeze": load(args.freeze), "a": load(args.a), "bc": load(args.bc), "bc_report": load(args.bc_report),
              "r": load(args.r), "rmem": load(args.rmem), "mreg": load(args.mreg), "q": load(args.q)}
    if inputs["freeze"].get("campaign") != "v1.0.0 qualification" or not inputs["freeze"].get("frozen_utc"):
        parser.error("--freeze is not the frozen v1.0.0 freeze record")
    try:
        comparison, excluded = build(inputs, {"campaign": args.campaign_url, "evidence": args.evidence_url}, args.environment)
    except (ExportError, KeyError, TypeError) as error:
        print(f"export refused: {error!r}", file=sys.stderr)
        return 2
    data = copy.deepcopy(load(args.releases))
    entries = [r for r in data["releases"] if r["version"] == VERSION]
    if len(entries) != 1:
        print(f"export refused: {args.releases} has {len(entries)} {VERSION} entries", file=sys.stderr)
        return 2
    entries[0]["status"] = "published"
    entries[0]["comparisons"] = [comparison]
    try:
        build_site.validate(data)
    except (AssertionError, KeyError, TypeError) as error:
        print(f"export refused: the result fails the site validation ({error!r})", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(data, indent=1) + "\n")
    args.report_only.write_text(json.dumps({"campaign_report_only": excluded}, indent=1) + "\n")
    print(f"{len(comparison['results'])} rows; {len(excluded)} items for the campaign report only; nothing published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
