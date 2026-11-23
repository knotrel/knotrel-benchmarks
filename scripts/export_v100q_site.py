#!/usr/bin/env python3
"""Exports the v1.0.0 qualification results to the benchmark site's schema (plan section 11).

``docs/SITE.md``: "Add an adapter/export from a campaign analyzer rather than manually
transcribing measurements." This is that adapter. It reads only the frozen analyzers'
outputs, never raw data, and recomputes no verdict:

- A (``analyze_v100q_a.py``): one row per cell for the primary metric with the cell's class,
  and one row per gated supporting metric with that metric's class;
- B4 (``analyze_v100q_bc.py`` numbers, ``report_v100q_bc.py`` roles and statuses): deciding
  cells and the descriptive frozen counterparts (``role``); the two not-equivalent cells (E6)
  go to the campaign report only (plan section 11);
- C (same files): C3 and C4 rows (late over early maximum of the lifecycle arm against the
  1.25 budget); C1 and C2 (rules checked at every checkpoint) as threshold-kind rows with their
  verdict and no ratio or interval; B5 and T5 rows (core rule different) with their verdict;
- R, Rmem, M_reg (``analyze_v100q.py``; an Rmem metric with a zero reference keeps its verdict
  and counts, with no ratio); Q1-Q5 (``evaluate_v100q_q.py``; Q2, a rule on every observation,
  is a threshold-kind row without an estimate). Only E6 and Q5 against v0.8.0 (plan section 11)
  and the A supporting metrics the frozen analyzer marks REPORT_ONLY (no verdict) go to the
  campaign report; no deciding verdict is dropped.

Intervals (plan section 11): ``delta_ci95`` holds the frozen order-statistic interval of the
median paired change, converted to percent; ``ci_method`` names it exactly with its coverage
(97.73 % at n = 24, 96.14 % at n = 12): it is **not** a 95 % interval and the field name does
not make it one. Rmem and Q rows have no interval, with the plan's reason. B4 and C rows say
that their reference is an arm of the candidate build, not v0.9.0. Rows whose reference
column holds a threshold say so (``reference_kind: "threshold"``).

**Site schema 2** (``scripts/build_site.py``, ``docs/SITE.md``). Every row carries three
separate fields: ``verdict``, the analyzer's class copied verbatim (PASS, "PASS (IMPROVED)",
FAIL, REGRESSION, INCONCLUSIVE, INCONCLUSIVE_DISCLOSED, UNRESOLVED, TIMER_LIMITED,
EXCEEDS_BUDGET, INVALID, NOT_EQUIVALENT; NOT_RUN; null for no verdict); ``category``
(``decisive``, ``descriptive``, ``disclosure``: the row's role in plan section 7, never derived
from its verdict); and ``status`` (``completed``, ``not_run``, ``nonconforming``, ``failed``). A
row that is not ``completed`` has a ``status_reason`` and no measured value. Mapping:

- A primary and gated supporting metrics, B4 deciding cells, C1-C3, B5 and T5 (core rule
  different), R, Rmem, M_reg, Q1, Q2, Q4 and Q5: ``decisive``. Q3 ("classified as measured") is ``decisive`` too: a non-PASS Q3 needs a
  disposition and an envelope and blocks the rc (plan section 8.2).
- B4 descriptive frozen counterparts (including ``import-high``) and C4: ``disclosure`` (plan
  section 7, "Disclosure categories").
- An M_reg cell the analyzer made INVALID without metrics: ``failed``, its invalid
  observations as the reason. A Q criterion that FAILs without a value (a failed observation):
  ``failed``. A Q criterion with no verdict because block Q was NONCONFORMING: verdict null,
  ``nonconforming``. Cells listed in the optional ``--not-run`` file (an experiment stopped by a
  product failure, plan section 5.5): NOT_RUN, ``not_run``, with their mandatory reason.
- C1, C2, Q2, B5/T5 and an Rmem metric with a zero reference: ``completed`` with their verdict and
  an ``estimate_unavailable_reason``, without a ratio or an interval.

**Fail closed.** A measured class outside ``build_site.MEASURED_VERDICTS`` (a truly unknown
class) stops the export and is named; nothing is mapped onto another verdict. A not-run entry
without a reason, or one that names a measured row, stops it too. The output is validated with
``build_site.validate``.

**Final Q attempt only.** ``--q`` must be ``<CAMP>/<attempt>/evaluation.json`` inside the campaign
directory of the frozen candidate (``v1.0.0-qualification-<cand7>-attemptN``). The final Q attempt
is derived from the campaign's own records, never from the argument: ``part3`` when it carries no
``superseded_by.json`` and no ``part3-attempt2`` exists; ``part3-attempt2`` when ``part3``'s
``superseded_by.json`` names it and it carries no marker itself. Any other layout (an attempt-2
directory without the marker, a marker naming a missing or different directory, a marker in
attempt 2, an unknown ``part3*`` directory) is ambiguous and refused, as is a ``--q`` naming a
superseded attempt or an ``evaluation.json`` whose ``final_attempt`` or ``superseded_attempts``
disagree. Every Q row records the attempt as ``q_attempt``.

**Never publishes.** It requires the decision record (``--decision``) to exist, writes the
whole dataset with the 1.0.0 entry ``published`` to ``--out``, which must lie outside
``docs/``, and the excluded items to ``--report-only``. Copying the result into
``docs/data/releases.json`` is a separate, reviewed change.

    export_v100q_site.py --freeze FREEZE.json --decision DECISION.md --a A.json --bc BC.json \\
        --bc-report REPORT.json --r R.json --rmem RMEM.json --mreg MREG.json --q Q.json \\
        --campaign-url URL --evidence-url URL --environment TEXT \\
        --releases docs/data/releases.json --out OUT.json --report-only EXCLUDED.json \\
        [--not-run NOT-RUN.json]

``NOT-RUN.json``: ``{"not_run": [{"experiment": "R", "scenario": CELL, "metric": METRIC,
"reason": TEXT, "category": "decisive"}]}`` (``category`` defaults to ``decisive``).
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
SITE_SCHEMA = 2
DECISIVE, DESCRIPTIVE, DISCLOSURE = build_site.CATEGORIES
COMPLETED, NOT_RUN_STATUS, NONCONFORMING, FAILED = build_site.STATUSES
CI_24 = ("distribution-free interval for the median of 24 paired log ratios ln(C/B): one-based order "
         "statistics [r(7), r(18)], coverage 97.73 % (1 - 2 P(Bin(24, 1/2) <= 6)); not a 95 % interval; "
         "converted to percent")
CI_12 = ("distribution-free interval for the median of 12 paired log ratios ln(C/B): one-based order "
         "statistics [r(3), r(10)], coverage 96.14 % (1 - 2 P(Bin(12, 1/2) <= 2)); not a 95 % interval; "
         "converted to percent")
WITHIN = "; the reference is an arm within the candidate build (lifecycle against its reference arm), not v0.9.0"
NO_ABS = "the campaign estimates the paired relative change only; no interval is computed for the absolute medians"
RMEM_REASON = "deterministic counts, one run per arm"
C_RULES = {"C1": "engine_vertices <= 2 x nodes + 1024 at every checkpoint",
           "C2": "logical counts equal the expected counts at every checkpoint"}
Q_REASON = "3 observations; the protocol reports the median and range"
C_REASON = "one run per arm and cell; C3/C4 are rules on one 30-cycle series, not estimates with an interval"


class ExportError(ValueError):
    """The inputs cannot be exported without changing a verdict or inventing a value."""


Q_ATTEMPTS = ("part3", "part3-attempt2")


def final_q_attempt(q_path: Path, candidate: str) -> str:
    """The final Q attempt of the campaign holding ``q_path``; ``q_path`` must be its evaluation.

    Derived from the campaign directory's records (``superseded_by.json`` written by the Q
    attempt-2 gate), so a superseded or ambiguous input is refused instead of exported."""
    q_path = Path(q_path).resolve()
    if q_path.name != "evaluation.json":
        raise ExportError(f"--q must be a Q attempt's evaluation.json, not {q_path.name}")
    attempt_dir, camp = q_path.parent, q_path.parent.parent
    prefix = f"v1.0.0-qualification-{candidate[:7]}-attempt"
    if not (camp.name.startswith(prefix) and camp.name[len(prefix):].isdigit()):
        raise ExportError(f"--q is not inside a campaign directory of the frozen candidate ({prefix}N): {camp.name}")
    present = sorted(p.name for p in camp.iterdir() if p.is_dir() and p.name.startswith("part3"))
    unknown = [n for n in present if n not in Q_ATTEMPTS]
    if unknown or "part3" not in present:
        raise ExportError(f"ambiguous Q attempts in {camp.name}: {present} (expected part3, optionally part3-attempt2)")

    def marker(name: str) -> Optional[Dict[str, Any]]:
        path = camp / name / "superseded_by.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
        except ValueError as error:
            raise ExportError(f"{name}/superseded_by.json is unreadable: {error}") from error
        if not isinstance(data, dict):
            raise ExportError(f"{name}/superseded_by.json is not an object")
        return data

    first = marker("part3")
    if "part3-attempt2" in present:
        if first is None or first.get("superseded_by") != "part3-attempt2":
            raise ExportError("ambiguous Q attempts: part3-attempt2 exists but part3/superseded_by.json does not name it")
        if marker("part3-attempt2") is not None:
            raise ExportError("ambiguous Q attempts: part3-attempt2 is itself marked superseded")
        final = "part3-attempt2"
    else:
        if first is not None:
            raise ExportError(f"ambiguous Q attempts: part3 is superseded by {first.get('superseded_by')!r}, "
                              "which does not exist")
        final = "part3"
    if attempt_dir.name != final:
        raise ExportError(f"--q names {attempt_dir.name}, but the final Q attempt of {camp.name} is {final}")
    if not q_path.is_file():
        raise ExportError(f"the final Q attempt {final} has no evaluation.json")
    return final


def check_q_attempt(q: Dict[str, Any], final: Any) -> None:
    """The evaluation must be the one the evaluator wrote for the final attempt."""
    if final not in Q_ATTEMPTS:
        raise ExportError(f"the final Q attempt is not established ({final!r})")
    if q.get("final_attempt") != final:
        raise ExportError(f"the Q evaluation is for {q.get('final_attempt')!r}, not the final attempt {final!r}")
    expected = [] if final == "part3" else ["part3"]
    if q.get("superseded_attempts") != expected:
        raise ExportError(f"the Q evaluation lists superseded attempts {q.get('superseded_attempts')!r}, "
                          f"expected {expected!r}")


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


def measured_class(verdict: Any, where: str) -> str:
    """The analyzer's class, unchanged, if the site schema knows it; otherwise stop (fail closed)."""
    if verdict not in build_site.MEASURED_VERDICTS:
        raise ExportError(f"{where}: measured class {verdict!r} is unknown to the site schema "
                          f"{build_site.MEASURED_VERDICTS}; it is never mapped onto another verdict")
    return verdict


def row(scenario: str, metric: str, unit: str, direction: str, candidate: float, reference: float, runs: int,
        verdict: Any, ci_method: str, evidence: str, delta_ci: Optional[Sequence[float]] = None,
        reason: Optional[str] = None, category: str = DECISIVE, **extra: Any) -> Dict[str, Any]:
    """A ``completed`` row with its measured values."""
    out: Dict[str, Any] = {"scenario": scenario, "metric": metric, "unit": unit, "direction": direction,
                           "candidate": candidate, "reference": reference,
                           "delta_pct": 100.0 * (candidate / reference - 1.0) if reference else None,
                           "candidate_ci95": None, "reference_ci95": None,
                           "delta_ci95": list(delta_ci) if delta_ci is not None else None,
                           "runs": runs, "verdict": measured_class(verdict, f"{scenario} {metric}"),
                           "category": category, "status": COMPLETED, "ci_method": ci_method,
                           "evidence_url": evidence}
    out["ci_unavailable_reason"] = reason or NO_ABS
    out.update(extra)
    return out


def rule_row(scenario: str, metric: str, verdict: Any, why: str, evidence: str, category: str = DECISIVE,
             **extra: Any) -> Dict[str, Any]:
    """A ``completed`` row whose verdict has no ratio or interval (a rule, or a zero reference): the verdict
    is published, ``estimate_unavailable_reason`` says why no estimate is shown, and no value is invented."""
    out: Dict[str, Any] = {"scenario": scenario, "metric": metric,
                           "verdict": measured_class(verdict, f"{scenario} {metric}"), "category": category,
                           "status": COMPLETED, "estimate_unavailable_reason": why, "evidence_url": evidence}
    out.update({k: v for k, v in extra.items() if v is not None})
    return out


def unmeasured(scenario: str, metric: str, verdict: Any, status: str, status_reason: str, evidence: str,
               category: str = DECISIVE, **extra: Any) -> Dict[str, Any]:
    """A row without measured values (``not_run``, ``nonconforming`` or ``failed``) and its reason."""
    if verdict not in build_site.STATUS_VERDICTS[status]:
        raise ExportError(f"{scenario} {metric}: verdict {verdict!r} is impossible with status {status}")
    if not isinstance(status_reason, str) or not status_reason.strip():
        raise ExportError(f"{scenario} {metric}: a {status} row needs a reason")
    out: Dict[str, Any] = {"scenario": scenario, "metric": metric, "verdict": verdict, "category": category,
                           "status": status, "status_reason": status_reason, "evidence_url": evidence}
    out.update({k: v for k, v in extra.items() if v is not None})
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
            deciding = r["role"] == "deciding"
            if not deciding and r["role"] != "descriptive":
                raise ExportError(f"{r['id']}: unknown B4 role {r['role']!r}")
            role = "deciding" if deciding else "descriptive frozen counterpart (disclosure, no release verdict)"
            extra = {"measured_status": r["measured_status"]} if "measured_status" in r else {}
            rows.append(row(r["id"] if deciding else f"{r['id']} (descriptive)", "window_ns", "ns", "lower",
                            t["C_median"], t["B_median"], t["pairs"], r["status"], CI_12 + WITHIN, evidence,
                            t["interval_pct"], category=DECISIVE if deciding else DISCLOSURE,
                            experiment=t["experiment"], role=role, **extra))
        elif r["kind"] in ("C3", "C4"):
            cell_id = r["id"].rsplit(":", 1)[0]
            s = sustained[cell_id]
            rows.append(row(f"{cell_id} {r['kind']} (late over early max; slope rule in the campaign report)",
                            f"{s['metric']} max(cycles 21-30) / max(cycles 1-10)", "ratio", "lower",
                            s["late_over_early"], 1.25, 1, r["status"], "none: " + C_REASON + WITHIN, evidence,
                            None, C_REASON, category=DECISIVE if r["kind"] == "C3" else DISCLOSURE,
                            experiment="C", role="deciding" if r["kind"] == "C3" else "disclosure (C4)",
                            reference_kind="threshold"))
        elif r["kind"] in C_RULES:
            cell_id = r["id"].rsplit(":", 1)[0]
            rows.append(rule_row(f"{cell_id} {r['kind']} (rule at every checkpoint)", C_RULES[r["kind"]], r["status"],
                                 "a rule checked at every checkpoint: no single numeric estimate (checkpoints in the "
                                 "campaign report)" + WITHIN, evidence, experiment="C", role="deciding",
                                 reference_kind="threshold"))
        elif r["kind"] == "T5" and r["status"] == "INVALID" and r.get("reason"):
            rows.append(unmeasured(r["id"], "T5 tail latency", "INVALID", FAILED, f"T5 analysis invalid: {r['reason']}",
                                   evidence, experiment="T5", role="deciding (core rule different)"))
        elif r["kind"] in ("B5", "T5"):
            rows.append(rule_row(r["id"], f"{r['kind']} (core rule different)", r["status"],
                                 f"{r['kind']}: the frozen decision view copies the status only; its values are in the "
                                 "campaign report", evidence, experiment=r["kind"], role="deciding (core rule different)"))
        else:
            raise ExportError(f"{r['id']}: unknown B/C row kind {r['kind']!r}")
    return rows, excluded


def r_rows(r: Dict[str, Any], evidence: str) -> List[Dict[str, Any]]:
    # ``verdict`` is the analyzer's class with its qualifier ("PASS (IMPROVED)"), published verbatim.
    return [row(cell_id, s["metric"], unit_of(s["metric"]), "lower", s["C_median"], s["B_median"], s["pairs"],
                s.get("verdict", s["status"]), CI_12, evidence, s["interval_pct"], experiment="R", role="deciding",
                metric_status=s["status"], improved=s.get("verdict") == "PASS (IMPROVED)")
            for cell_id, s in r.items()]


def rmem_rows(rmem: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows, excluded = [], []
    for cell_id, cell in rmem.items():
        for metric, m in cell["metrics"].items():
            if not m["ref"]:
                rows.append(rule_row(cell_id, metric, m["verdict"],
                                     "the reference count is zero: no ratio; the rule is candidate > reference x 1.20",
                                     evidence, experiment="Rmem", role="deciding", unit=unit_of(metric),
                                     direction="lower", candidate=m["cand"], reference=m["ref"], runs=1))
                continue
            rows.append(row(cell_id, metric, unit_of(metric), "lower", m["cand"], m["ref"], 1, m["verdict"],
                            "none: deterministic allocator counts, REGRESSION if candidate > reference x 1.20",
                            evidence, None, RMEM_REASON, experiment="Rmem", role="deciding"))
    return rows, excluded


def mreg_rows(mreg: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows, excluded = [], []
    for cell_id, cell in mreg.get("result", mreg).items():
        if not cell.get("metrics"):
            reasons = cell.get("invalid_observations") or []
            rows.append(unmeasured(cell_id, "all M_reg metrics of the cell", cell.get("verdict"), FAILED,
                                   "no analyzable metrics: " + ("; ".join(reasons) or "an observation is invalid")
                                   + " (MATRIX rules.validity; observations in the campaign report)",
                                   evidence, experiment="M_reg", role="deciding"))
            continue
        for metric, s in cell["metrics"].items():
            lo, hi = s["interval_log"]
            if s["direction"] == "higher_is_better":  # analyzed as ln(ref/cand)
                cand, ref, ci, direction = s["B_median"], s["C_median"], [pct(-hi), pct(-lo)], "higher"
            else:
                cand, ref, ci, direction = s["C_median"], s["B_median"], [pct(lo), pct(hi)], "lower"
            rows.append(row(cell_id, metric, unit_of(metric), direction, cand, ref, s["pairs"],
                            cell["verdict"] if cell["verdict"] == "INVALID" else s.get("verdict", s["status"]),
                            CI_12 + " (for higher-is-better metrics the analyzed ratio is reference/candidate; "
                                    "shown here as candidate/reference)", evidence, ci,
                            experiment="M_reg", role="deciding", cell_verdict=cell["verdict"],
                            metric_status=s["status"]))
    return rows, excluded


def q_rows(q: Dict[str, Any], evidence: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    crit = q["criteria"]
    rows, excluded = [], []
    method = "none: " + Q_REASON

    def add(name: str, scenario: str, metric: str, unit: str, direction: str, cand: Any, ref: Any, verdict: Any,
            **extra: Any) -> None:
        state = crit[name]
        if verdict is None:  # no verdict: legitimate only when block Q did not conform (protocol section 4)
            if q.get("q_status") != "NONCONFORMING":
                raise ExportError(f"{name} {scenario} {metric}: no verdict although block Q is {q.get('q_status')!r}")
            missing = "; ".join(state.get("missing_observations") or []) or "observations missing"
            rows.append(unmeasured(scenario, metric, None, NONCONFORMING,
                                   f"block Q NONCONFORMING ({q.get('run_cause') or 'cause not recorded'}): {missing}; "
                                   "no verdict, and it does not count as PASS (protocol section 4)", evidence,
                                   experiment="Q", criterion=name, unit=unit, direction=direction, **extra))
            return
        if cand is None or ref in (None, 0):
            if verdict != "FAIL":
                raise ExportError(f"{name} {scenario} {metric}: verdict {verdict!r} without a value")
            why = (state.get("failed_observations") or []) + (state.get("missing_observations") or [])
            rows.append(unmeasured(scenario, metric, "FAIL", FAILED,
                                   "no passing value (plan section 5.5): " + ("; ".join(why) or extra.pop("missing_reason", None)
                                                                          or "a value is missing"),
                                   evidence, experiment="Q", criterion=name, unit=unit, direction=direction, **extra))
            return
        extra.pop("missing_reason", None)
        rows.append(row(scenario, metric, unit, direction, cand, ref, 3, verdict, method, evidence, None, Q_REASON,
                        experiment="Q", criterion=name, **extra))

    s1 = crit["Q1"]["status"]
    add("Q1", "Q1 L1 G100k C=16 (reference = threshold)", "marker lag p99 (median of observations)", "ms", "lower",
        crit["Q1"].get("marker_p99_ms"), 1000.0, s1, reference_kind="threshold", role="deciding")
    add("Q1", "Q1 L1 G100k C=16 (reference = threshold)", "marker lag max (median of observations)", "ms", "lower",
        crit["Q1"].get("marker_max_ms"), 3000.0, s1, reference_kind="threshold", role="deciding")
    q2 = crit["Q2"]["status"]
    q2_scenario, q2_metric = "Q2 L1 (rule on every observation)", "marker lag and retained WAL within limits"
    if q2 is None:
        add("Q2", q2_scenario, q2_metric, "rule", "lower", None, None, None, reference_kind="threshold", role="deciding")
    else:
        rows.append(rule_row(q2_scenario, q2_metric, q2,
                             "a rule on every L1 observation (lag and retained WAL): no single estimate; "
                             + ("; ".join((crit["Q2"].get("failed_observations") or [])
                                          + (crit["Q2"].get("missing_observations") or []))
                                or "observations in the campaign report"),
                             evidence, experiment="Q", criterion="Q2", reference_kind="threshold", role="deciding"))
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
        has_values = "query_rps" in cell
        rps_v = ("PASS" if cell["rps_pass"] else "FAIL") if has_values and clean and s5 is not None else s5
        p99_v = ("PASS" if cell["p99_pass"] else "FAIL") if has_values and clean and s5 is not None else s5
        rps = cell.get("query_rps") or [None, None]
        p99 = cell.get("query_p99_ms") or [None, None]
        missing = {} if has_values else {"missing_reason": cell.get("reason", "missing median")}
        add("Q5", f"Q5 {key} (reference = v0.9.0, same session)", "query throughput (median)", "requests/s", "higher",
            rps[1], rps[0], rps_v, role="deciding", threshold="candidate >= 90 % of reference", **missing)
        add("Q5", f"Q5 {key} (reference = v0.9.0, same session)", "client p99 (median)", "ms", "lower",
            p99[1], p99[0], p99_v, role="deciding", threshold="candidate <= 125 % of reference", **missing)
    if "Q5_v0_8_0" in q:
        excluded.append({"id": "Q5 against v0.8.0", "status": "descriptive", "reason": "reported, not deciding (plan section 11)",
                         "values": q["Q5_v0_8_0"]})
    return rows, excluded


def not_run_rows(entries: Sequence[Dict[str, Any]], evidence: str) -> List[Dict[str, Any]]:
    """NOT_RUN rows for cells that an experiment stopped by a product failure never measured."""
    rows = []
    for entry in entries:
        for key in ("experiment", "scenario", "metric"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ExportError(f"not-run entry {entry!r}: {key} is required")
        category = entry.get("category", DECISIVE)
        if category not in build_site.CATEGORIES:
            raise ExportError(f"not-run entry {entry['scenario']}: unknown category {category!r}")
        rows.append(unmeasured(entry["scenario"], entry["metric"], build_site.NOT_RUN, NOT_RUN_STATUS,
                               entry.get("reason"), evidence, category, experiment=entry["experiment"],
                               unit=entry.get("unit"), direction=entry.get("direction")))
    return rows


def build(inputs: Dict[str, Any], urls: Dict[str, str], environment: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    freeze = inputs["freeze"]
    ev = urls["evidence"]
    rows = a_rows(inputs["a"], ev)
    excluded = a_report_only(inputs["a"])
    for part in (bc_rows(inputs["bc"], inputs["bc_report"], ev), rmem_rows(inputs["rmem"], ev),
                 mreg_rows(inputs["mreg"], ev), q_rows(inputs["q"], ev)):
        rows += part[0]
        excluded += part[1]
    check_q_attempt(inputs["q"], inputs.get("q_attempt"))
    for r in rows:
        if r.get("experiment") == "Q":
            r["q_attempt"] = inputs["q_attempt"]
    rows += r_rows(inputs["r"], ev)
    not_run = not_run_rows(inputs.get("not_run", []), ev)
    measured = {(r["scenario"], r["metric"]) for r in rows}
    clash = [(r["scenario"], r["metric"]) for r in not_run if (r["scenario"], r["metric"]) in measured]
    if clash:
        raise ExportError(f"not-run entries name rows the analyzers classified: {clash}")
    rows += not_run
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
    parser.add_argument("--not-run", type=Path, help="cells not run, each with its reason (see the module docstring)")
    args = parser.parse_args(argv)
    if args.not_run is not None:
        args.not_run = confined(args.not_run, "--not-run")
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
              "r": load(args.r), "rmem": load(args.rmem), "mreg": load(args.mreg), "q": load(args.q),
              "not_run": load(args.not_run)["not_run"] if args.not_run is not None else []}
    if inputs["freeze"].get("campaign") != "v1.0.0 qualification" or not inputs["freeze"].get("frozen_utc"):
        parser.error("--freeze is not the frozen v1.0.0 freeze record")
    try:
        inputs["q_attempt"] = final_q_attempt(args.q, inputs["freeze"]["candidate"]["commit"])
        comparison, excluded = build(inputs, {"campaign": args.campaign_url, "evidence": args.evidence_url}, args.environment)
    except (ExportError, KeyError, TypeError) as error:
        print(f"export refused: {error!r}", file=sys.stderr)
        return 2
    data = copy.deepcopy(load(args.releases))
    entries = [r for r in data["releases"] if r["version"] == VERSION]
    if len(entries) != 1:
        print(f"export refused: {args.releases} has {len(entries)} {VERSION} entries", file=sys.stderr)
        return 2
    data["schema_version"] = max(data["schema_version"], SITE_SCHEMA)  # older entries keep their own schema
    entries[0]["status"] = "published"
    entries[0]["schema_version"] = SITE_SCHEMA
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
