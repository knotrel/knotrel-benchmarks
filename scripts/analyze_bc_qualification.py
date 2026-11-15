#!/usr/bin/env python3
"""Decision analysis for a Knotrel baseline/candidate (B/C) qualification campaign.

Reads the raw pair records written by ``run_p0_aa.py`` (``pair_*.json``) and applies the
decision rules documented in knotrel ``docs/release-v0.3.0-closure-plan.md`` §5.5. With
``--rules v0.4.0`` it applies the stricter combination proposed in
``docs/release-v0.4.0-qualification-plan.md`` §8.2. It runs no benchmark and never reads a
previously computed analysis: every number comes from the raw observations.

Method (both rule sets):
- Each pair yields one paired log ratio ``r_i = ln(C_i / B_i)`` per metric.
- The interval for the median is distribution-free, using one-based order statistics:
  ``[r(3), r(10)]`` at n = 12 and ``[r(7), r(18)]`` at n = 24. No other n is accepted.
- Percent values are ``(exp(x) - 1) * 100`` of the log-scale value. ``median_change_pct``
  uses the median log ratio. ``ratio_of_medians_change_pct`` compares the per-label medians
  and is reported only.
- Tolerances: primary 10%, query/request p99 25%, RSS 20%, each compared as ``ln(1 + tol)``.
- Classification of an interval against tolerance ``t``: PASS if upper <= t, REGRESSION if
  lower > t, otherwise INCONCLUSIVE.

Rule set ``v0.3.0`` reproduces the approved v0.3.0 decisions:
- Supporting metrics only flag ``lower_bound_exceeds_tolerance``; a flagged metric is a
  supporting REGRESSION.
- Only an INCONCLUSIVE primary at n = 12 requires the extension.
- After the extension, a primary still INCONCLUSIVE with median <= t is "D6 disclosure
  permitted"; with median > t it is treated as REGRESSION.

Rule set ``v0.4.0`` (approved decisions G3 and G3a-1, §8.2):
- The input must be the approved qualification design: the main phase has exactly the nine
  cells of ``run_p0_aa.QUALIFICATION_CELL_IDS``, and every cell, in each phase, has 12 pairs
  in sessions 0-2 with two B->C and two C->B pairs per session.
- ``link_p99_ns`` and ``cut_p99_ns`` of the four core cells (``REPORT_ONLY``) are report-only:
  their medians are within two ticks of the host timer. They get the status REPORT_ONLY,
  never PASS, carry no tolerance comparison, and take no part in the cell outcome. Their
  values, intervals and per-pair raw values are still reported. No other metric is exempt.
- Every other supporting metric is classified PASS/INCONCLUSIVE/REGRESSION like the primary.
- Any REGRESSION (primary or supporting) makes the cell REGRESSION.
- A cell is PASS only if every gated metric is PASS.
- At n = 12, any INCONCLUSIVE gated metric requires the extension.
- After the extension: INCONCLUSIVE_DISCLOSED only if the primary is INCONCLUSIVE with
  median <= t and every gated supporting metric is PASS. A primary INCONCLUSIVE with
  median > t is REGRESSION. Anything else (an INCONCLUSIVE supporting metric) is UNRESOLVED,
  which needs an owner disposition and can never be disclosed instead.
- The final report also carries the n = 12 decision of every cell (``main_cells``).

The v0.3.0 rule set is kept exactly as approved; the v0.4.0 policy never changes it.

Input checks, both rule sets (they reject data, they never change a decision):
- each raw directory's ``manifest.json`` must declare its phase (``pilot_design.phase``);
- record and observation types, identities, process status and correctness guardrails;
- observations in launch order matching ``labels``, with ``pair_position`` 0 and 1, the
  record's session, and position 0 launched before position 1;
- one ``binary_identity`` per (label, family) across both phases, different for B and C,
  and one non-empty string trace fingerprint per core cell;
- every observation has integer launch and completion times (completion after launch), no
  two observations share a launch time or a raw pair file, and no observation started
  before the previous one (in launch order, over both phases) completed;
- the extension directory must differ from the main one, and its first launch must come
  after the last main completion.
Invalid or missing data is never dropped: any problem raises ``AnalysisError`` and no
decision is produced. The rule set ``v0.3.0`` is for reproducing the retained v0.3.0
campaign only; it applies none of the v0.4.0 design checks and must not be used on new data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from run_p0_aa import QUALIFICATION_CELL_IDS

RULESETS = ("v0.3.0", "v0.4.0")
LABELS = ("B", "C")
INTERVAL_RANKS = {12: (3, 10), 24: (7, 18)}
MAIN_PAIRS_PER_CELL = 12
TOLERANCES = {"primary": 0.10, "query_tail": 0.25, "rss": 0.20}

PASS = "PASS"
INCONCLUSIVE = "INCONCLUSIVE"
REGRESSION = "REGRESSION"
INCONCLUSIVE_DISCLOSED = "INCONCLUSIVE_DISCLOSED"
UNRESOLVED = "UNRESOLVED"
D6_PERMITTED = "D6 disclosure permitted"
D6_REGRESSION = "treated as REGRESSION"
REPORT_ONLY_STATUS = "REPORT_ONLY"

# Decision G3a-1 (v0.4.0 only): metrics excluded from the gate, listed exhaustively by cell.
REPORT_ONLY_REASON = ("timer resolution: medians are within two ticks (41.67 ns) of the host "
                      "timer, so one tick is a 100% change; no percent bound is established")
REPORT_ONLY: Dict[str, Tuple[str, ...]] = {
    "core_sparse_traversal_10k_compact-bfs_warmed": ("link_p99_ns", "cut_p99_ns"),
    "core_sparse_traversal_10k_compact-workspace_warmed": ("link_p99_ns", "cut_p99_ns"),
    "core_sustained_churn_10k_compact-bfs_warmed": ("link_p99_ns", "cut_p99_ns"),
    "core_sustained_churn_10k_compact-workspace_warmed": ("link_p99_ns", "cut_p99_ns"),
}
SESSIONS = (0, 1, 2)
ORDERS = (("B", "C"), ("C", "B"))
PAIRS_PER_SESSION_ORDER = 2


class AnalysisError(ValueError):
    """Raised for any invalid, missing or inconsistent input. No partial result is produced."""


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{where}: expected a number, found {value!r}")
    try:
        number = float(value)
    except OverflowError as error:
        raise AnalysisError(f"{where}: {value!r} overflows a float") from error
    if not math.isfinite(number) or number <= 0:
        raise AnalysisError(f"{where}: expected a finite positive number, found {value!r}")
    return number


def _get(mapping: Any, path: Sequence[str], where: str) -> Any:
    current = mapping
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise AnalysisError(f"{where}: missing field {'.'.join(path)}")
        current = current[key]
    return current


Extractor = Callable[[Dict[str, Any], str], float]


def _parsed(*path: str) -> Extractor:
    return lambda obs, where: _number(_get(obs, ("parsed_metrics",) + path, where), f"{where} {'.'.join(path)}")


def _exported(name: str) -> Extractor:
    return _parsed("exported_metrics", name)


def _observation(name: str) -> Extractor:
    return lambda obs, where: _number(_get(obs, (name,), where), f"{where} {name}")


# (metric name, extractor, tolerance key); the first entry of each family is the primary metric.
FAMILIES: Dict[str, List[Tuple[str, Extractor, str]]] = {
    "core": [
        ("workload_wall_ns", _parsed("workload_wall_ns"), "primary"),
        ("connected_p99_ns", _parsed("measurements", "connected", "p99_ns"), "query_tail"),
        ("link_p99_ns", _parsed("measurements", "link", "p99_ns"), "query_tail"),
        ("cut_p99_ns", _parsed("measurements", "cut", "p99_ns"), "query_tail"),
        ("peak_rss_bytes", _observation("peak_rss_bytes"), "rss"),
    ],
    "standalone-batch": [
        ("window_duration_ns", _exported("window_duration_ns"), "primary"),
        ("request_latency_p99_ns", _exported("request_latency_p99_ns"), "query_tail"),
        ("sampled_max_rss_bytes", _exported("sampled_max_rss_bytes"), "rss"),
    ],
    "lifecycle": [
        ("time_to_ready_ms", _exported("time_to_ready_ms"), "primary"),
        ("query_latency_p99_ns", _exported("query_latency_p99_ns"), "query_tail"),
        ("sampled_max_rss_bytes", _exported("sampled_max_rss_bytes"), "rss"),
    ],
}


def family_of(cell_id: str) -> str:
    if cell_id.startswith("core_"):
        return "core"
    if cell_id.startswith("http_standalone_batch_"):
        return "standalone-batch"
    if cell_id.startswith("http_lifecycle_"):
        return "lifecycle"
    raise AnalysisError(f"Unknown cell family for {cell_id!r}")


def _integer(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnalysisError(f"{where}: expected an integer, found {value!r}")
    return value


def _check_observation(obs: Any, cell_id: str, pair_id: Any, where: str) -> None:
    if not isinstance(obs, dict):
        raise AnalysisError(f"{where}: observation is not an object")
    if obs.get("cell_id") != cell_id or obs.get("pair_id") != pair_id:
        raise AnalysisError(f"{where}: observation identity does not match its pair")
    if not isinstance(obs.get("parsed_metrics"), dict):
        raise AnalysisError(f"{where}: parsed_metrics is not an object")
    if obs.get("status") != "parsed_valid":
        raise AnalysisError(f"{where}: observation status {obs.get('status')!r} is not parsed_valid")
    if obs.get("exit_code") != 0 or obs.get("timed_out") is not False or obs.get("error") is not None:
        raise AnalysisError(f"{where}: process failure (exit {obs.get('exit_code')!r}, "
                            f"timed_out {obs.get('timed_out')!r}, error {obs.get('error')!r})")


def _check_correctness(cell_id: str, family: str, by_label: Dict[str, Dict[str, Any]], where: str) -> None:
    if family == "core":
        prints = {label: _get(by_label[label], ("parsed_metrics", "trace_fingerprint_fnv1a64"), where)
                  for label in LABELS}
        if prints["B"] != prints["C"]:
            raise AnalysisError(f"{where}: trace fingerprint mismatch {prints}")
    for label in LABELS:
        exported = by_label[label]["parsed_metrics"].get("exported_metrics")
        if family == "standalone-batch" and _get(exported, ("all_items_matched",), f"{where} {label}") is not True:
            raise AnalysisError(f"{where} {label}: all_items_matched is not true")
        if family == "lifecycle":
            agreement = _get(exported, ("oracle_agreement_pct",), f"{where} {label}")
            if isinstance(agreement, bool) or agreement != 100:
                raise AnalysisError(f"{where} {label}: oracle agreement {agreement!r} is not 100%")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _raw_directory(directory: Path, phase: str) -> Path:
    """Resolve a raw campaign directory given on the command line; it must exist."""
    try:
        root = Path(directory).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AnalysisError(f"{phase}: raw directory {directory} is not accessible: {error}") from error
    if not root.is_dir():
        raise AnalysisError(f"{phase}: {directory} is not a directory")
    return root


def _contained_file(root: Path, path: Path, phase: str) -> Path:
    """Resolve ``path`` and require it to lie directly inside ``root``.

    Raw records are read only from the resolved raw directory itself; a name or
    symbolic link that escapes it is refused rather than followed. A missing or
    unreadable file is reported by the caller when it reads it.
    """
    resolved = Path(path).resolve()
    if resolved.parent != root:
        raise AnalysisError(f"{phase}: {path} resolves outside the raw directory {root}")
    return resolved


def _check_manifest(directory: Path, phase: str) -> str:
    """The raw directory's manifest must declare ``phase``; returns its sha256."""
    root = _raw_directory(directory, phase)
    path = _contained_file(root, root / "manifest.json", phase)
    try:
        data = path.read_bytes()
        manifest = json.loads(data)
    except (OSError, json.JSONDecodeError) as error:
        raise AnalysisError(f"{phase}: unreadable {path}: {error}") from error
    except RecursionError as error:
        raise AnalysisError(f"{phase}: {path} is nested too deeply") from error
    declared = _get(manifest, ("pilot_design", "phase"), f"{phase}/manifest.json")
    if declared != phase:
        raise AnalysisError(f"{path} declares phase {declared!r}, expected {phase!r}")
    return _sha256(data)


def load_pairs(directory: Path, phase: str) -> List[Dict[str, Any]]:
    """Load and validate every ``pair_*.json`` in a raw campaign directory.

    Each returned record has ``cell_id``, ``pair_id``, ``phase``, ``session``, ``labels``,
    ``launches`` (observation launch times), ``binaries`` (canonical binary identity per
    label), ``fingerprint`` (core only), ``sha256`` (of the raw file) and ``values``, a
    mapping of metric name to ``{"B": value, "C": value}``.
    """
    manifest_sha256 = _check_manifest(directory, phase)
    root = _raw_directory(directory, phase)
    files = sorted(_contained_file(root, path, phase) for path in root.glob("pair_*.json"))
    if not files:
        raise AnalysisError(f"No pair_*.json records in {directory}")
    pairs = []
    seen = set()
    for path in files:
        where = f"{phase}/{path.name}"
        try:
            data = path.read_bytes()
            record = json.loads(data)
        except (OSError, json.JSONDecodeError) as error:
            raise AnalysisError(f"{where}: unreadable pair record: {error}") from error
        except RecursionError as error:
            raise AnalysisError(f"{where}: pair record is nested too deeply") from error
        if not isinstance(record, dict):
            raise AnalysisError(f"{where}: pair record is not an object")
        cell_id = _get(record, ("cell_id",), where)
        if not isinstance(cell_id, str):
            raise AnalysisError(f"{where}: cell_id {cell_id!r} is not a string")
        pair_id = _integer(_get(record, ("pair_id",), where), f"{where} pair_id")
        session = _integer(_get(record, ("session",), where), f"{where} session")
        labels = _get(record, ("labels",), where)
        if not isinstance(labels, list) or sorted(map(str, labels)) != list(LABELS) \
                or not all(isinstance(label, str) for label in labels):
            raise AnalysisError(f"{where}: labels {labels!r} must be one B and one C")
        if pair_id in seen:
            raise AnalysisError(f"{where}: duplicate pair_id {pair_id!r}")
        seen.add(pair_id)
        family = family_of(cell_id)
        observations = _get(record, ("observations",), where)
        if not isinstance(observations, list) or len(observations) != 2:
            raise AnalysisError(f"{where}: expected exactly 2 observations")
        by_label: Dict[str, Dict[str, Any]] = {}
        launches = []
        completions = []
        for position, obs in enumerate(observations):
            _check_observation(obs, cell_id, pair_id, where)
            label = obs.get("label")
            if label not in LABELS or label in by_label:
                raise AnalysisError(f"{where}: labels must be exactly one B and one C")
            if label != labels[position] or _integer(obs.get("pair_position"), f"{where} pair_position") != position:
                raise AnalysisError(f"{where}: observation {position} ({label!r}, pair_position "
                                    f"{obs.get('pair_position')!r}) does not match labels {labels}")
            if _integer(obs.get("session"), f"{where} observation session") != session:
                raise AnalysisError(f"{where}: observation session {obs.get('session')!r} is not {session}")
            launch = _integer(obs.get("launch_unix_ns"), f"{where} {label} launch_unix_ns")
            completion = _integer(obs.get("completion_unix_ns"), f"{where} {label} completion_unix_ns")
            if completion <= launch:
                raise AnalysisError(f"{where} {label}: completion is not after launch")
            launches.append(launch)
            completions.append(completion)
            by_label[label] = obs
        if completions[0] > launches[1]:
            raise AnalysisError(f"{where}: position 1 was launched before position 0 completed")
        _check_correctness(cell_id, family, by_label, where)
        binaries = {}
        for label in LABELS:
            identity = _get(by_label[label], ("binary_identity",), f"{where} {label}")
            if not isinstance(identity, dict) or not identity:
                raise AnalysisError(f"{where} {label}: binary_identity is not a non-empty object")
            binaries[label] = json.dumps(identity, sort_keys=True)
        fingerprint = None
        if family == "core":
            fingerprint = by_label["B"]["parsed_metrics"]["trace_fingerprint_fnv1a64"]
            if not isinstance(fingerprint, str) or not fingerprint:
                raise AnalysisError(f"{where}: trace fingerprint {fingerprint!r} is not a non-empty string")
        values = {}
        for name, extract, _ in FAMILIES[family]:
            values[name] = {label: extract(by_label[label], f"{where} {label}") for label in LABELS}
        pairs.append({"cell_id": cell_id, "pair_id": pair_id, "phase": phase, "session": session,
                      "labels": labels, "launches": launches, "completions": completions,
                      "binaries": binaries, "fingerprint": fingerprint, "sha256": _sha256(data),
                      "manifest_sha256": manifest_sha256, "values": values})
    return pairs


def _check_consistency(pairs: Sequence[Dict[str, Any]]) -> None:
    """Identity, fingerprint and timeline coherence over every given pair (all phases).

    One binary identity per (label, family), different for B and C; one fingerprint per
    core cell; unique launch times and raw files; no observation starts before the previous
    one in launch order completed.
    """
    binaries: Dict[Tuple[str, str], str] = {}
    fingerprints: Dict[str, Any] = {}
    files: Dict[str, str] = {}
    timeline = []
    for pair in pairs:
        where = f"{pair['phase']} {pair['cell_id']} pair {pair['pair_id']}"
        if pair["sha256"] in files:
            raise AnalysisError(f"{where}: raw pair file is identical to {files[pair['sha256']]}")
        files[pair["sha256"]] = where
        for label, launch, completion in zip(pair["labels"], pair["launches"], pair["completions"]):
            timeline.append((launch, completion, f"{where} {label}"))
    timeline.sort()
    for (launch, completion, where), (next_launch, _, next_where) in zip(timeline, timeline[1:]):
        if next_launch == launch:
            raise AnalysisError(f"{next_where}: same launch time as {where}")
        if next_launch < completion:
            raise AnalysisError(f"{next_where}: launched before {where} completed")
    for pair in pairs:
        where = f"{pair['phase']} {pair['cell_id']} pair {pair['pair_id']}"
        family = family_of(pair["cell_id"])
        for label, identity in pair["binaries"].items():
            if binaries.setdefault((label, family), identity) != identity:
                raise AnalysisError(f"{where}: {label} {family} binary identity differs from earlier pairs")
        if family == "core" and fingerprints.setdefault(pair["cell_id"], pair["fingerprint"]) != pair["fingerprint"]:
            raise AnalysisError(f"{where}: trace fingerprint differs from earlier pairs of the cell")
    for family in {f for _, f in binaries}:
        if ("B", family) in binaries and binaries[("B", family)] == binaries.get(("C", family)):
            raise AnalysisError(f"B and C use the same {family} binary identity")


def _inputs_digest(pairs: Sequence[Dict[str, Any]], directory: Path, phase: str) -> Dict[str, Any]:
    manifests = {p["manifest_sha256"] for p in pairs}
    if len(manifests) != 1:
        raise AnalysisError(f"{phase}: manifest changed while reading {directory}")
    digest = hashlib.sha256()
    for pair in sorted(pairs, key=lambda p: p["pair_id"]):
        digest.update(f"{pair['pair_id']}\0{pair['sha256']}\0".encode())
    return {"directory": str(Path(directory).resolve()), "phase": phase,
            "manifest_sha256": manifests.pop(),
            "pair_files": len(pairs), "pair_files_digest_sha256": digest.hexdigest()}


def _pct(log_value: float) -> float:
    return (math.exp(log_value) - 1.0) * 100.0


def classify(lower: float, upper: float, tolerance_log: float) -> str:
    if upper <= tolerance_log:
        return PASS
    if lower > tolerance_log:
        return REGRESSION
    return INCONCLUSIVE


def summarize_metric(name: str, values: Sequence[Dict[str, float]], tolerance: float) -> Dict[str, Any]:
    """Paired summary of one metric over a cell's pairs."""
    n = len(values)
    if n not in INTERVAL_RANKS:
        raise AnalysisError(f"{name}: {n} pairs; only {sorted(INTERVAL_RANKS)} are pre-declared")
    ratios = sorted(math.log(v["C"] / v["B"]) for v in values)
    if not all(math.isfinite(r) for r in ratios):
        raise AnalysisError(f"{name}: a C/B ratio is not a finite positive number")
    low_rank, high_rank = INTERVAL_RANKS[n]
    lower, upper = ratios[low_rank - 1], ratios[high_rank - 1]
    median = statistics.median(ratios)
    tolerance_log = math.log(1.0 + tolerance)
    b_median = statistics.median(v["B"] for v in values)
    c_median = statistics.median(v["C"] for v in values)
    return {
        "metric": name,
        "pairs": n,
        "B_median": b_median,
        "C_median": c_median,
        "median_log_ratio": median,
        "median_change_pct": _pct(median),
        "ratio_of_medians_change_pct": (c_median / b_median - 1.0) * 100.0,
        "interval_log": [lower, upper],
        "interval_pct": [_pct(lower), _pct(upper)],
        "tolerance_pct": round(tolerance * 100),
        "tolerance_log": tolerance_log,
        "lower_bound_exceeds_tolerance": lower > tolerance_log,
        "median_exceeds_tolerance": median > tolerance_log,
        "status": classify(lower, upper, tolerance_log),
    }


def _make_report_only(metric: Dict[str, Any]) -> None:
    """Strip every verdict from a G3a-1 metric, keeping its values and interval."""
    metric.update(status=REPORT_ONLY_STATUS, gated=False, report_only_reason=REPORT_ONLY_REASON,
                  tolerance_pct=None, tolerance_log=None,
                  lower_bound_exceeds_tolerance=None, median_exceeds_tolerance=None)


def evaluate_cell(cell_id: str, pairs: Sequence[Dict[str, Any]], rules: str, final: bool) -> Dict[str, Any]:
    """Apply one rule set to one cell. ``final`` is True for the post-extension decision."""
    if rules not in RULESETS:
        raise AnalysisError(f"Unknown rule set {rules!r}")
    family = family_of(cell_id)
    metrics = [summarize_metric(name, [p["values"][name] for p in pairs], TOLERANCES[key])
               for name, _, key in FAMILIES[family]]
    primary, supporting = metrics[0], metrics[1:]
    report_only = REPORT_ONLY.get(cell_id, ()) if rules == "v0.4.0" else ()
    if rules == "v0.4.0":
        for metric in metrics:
            metric["pair_values"] = [{"pair_id": p["pair_id"], "phase": p["phase"],
                                      "B": p["values"][metric["metric"]]["B"],
                                      "C": p["values"][metric["metric"]]["C"]} for p in pairs]
            if metric["metric"] in report_only:
                _make_report_only(metric)
            else:
                metric["gated"] = True
    gated_supporting = [m for m in supporting if m["status"] != REPORT_ONLY_STATUS]
    extended = primary["pairs"] == 24
    cell: Dict[str, Any] = {
        "cell_id": cell_id,
        "family": family,
        "pairs": primary["pairs"],
        "primary_metric": primary["metric"],
        "B_median": primary["B_median"],
        "C_median": primary["C_median"],
        "median_change_pct": primary["median_change_pct"],
        "ratio_of_medians_change_pct": primary["ratio_of_medians_change_pct"],
        "primary_interval_pct": primary["interval_pct"],
        "primary_tolerance_pct": primary["tolerance_pct"],
        "primary_status": primary["status"],
        "primary": primary,
        "supporting": supporting,
        "supporting_regressions": [m["metric"] for m in supporting if m["lower_bound_exceeds_tolerance"]],
    }
    if rules == "v0.4.0":
        cell["report_only_metrics"] = list(report_only)
    if rules == "v0.3.0":
        regression = primary["status"] == REGRESSION or bool(cell["supporting_regressions"])
        status = REGRESSION if regression else primary["status"]
        cell["extension_required"] = (not final) and status == INCONCLUSIVE
        disposition = None
        if final and extended and status == INCONCLUSIVE:
            disposition = D6_REGRESSION if primary["median_exceeds_tolerance"] else D6_PERMITTED
        if final and not extended and status == INCONCLUSIVE:
            raise AnalysisError(f"{cell_id}: INCONCLUSIVE at n=12 without extension data")
        cell["status"] = status
        cell["extension_disposition"] = disposition
        return cell

    statuses = [primary["status"]] + [m["status"] for m in gated_supporting]
    if REGRESSION in statuses:
        status = REGRESSION
    elif all(s == PASS for s in statuses):
        status = PASS
    elif not final:
        status = INCONCLUSIVE
    elif not extended:
        raise AnalysisError(f"{cell_id}: INCONCLUSIVE at n=12 without extension data")
    elif primary["status"] == INCONCLUSIVE and primary["median_exceeds_tolerance"]:
        status = REGRESSION
    elif primary["status"] == INCONCLUSIVE and all(m["status"] == PASS for m in gated_supporting):
        status = INCONCLUSIVE_DISCLOSED
    else:
        status = UNRESOLVED
    cell["extension_required"] = (not final) and status == INCONCLUSIVE
    cell["status"] = status
    cell["extension_disposition"] = None
    return cell


def _group(pairs: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    cells: Dict[str, List[Dict[str, Any]]] = {}
    for pair in pairs:
        cells.setdefault(pair["cell_id"], []).append(pair)
    return cells


def _check_design(cells: Dict[str, List[Dict[str, Any]]], phase: str) -> None:
    """v0.4.0: every cell has two pairs per session and order (12 pairs, 3 balanced sessions)."""
    for cell_id, pairs in sorted(cells.items()):
        counts: Dict[Tuple[Any, Any], int] = {}
        for pair in pairs:
            labels = pair["labels"]
            key = (pair["session"], tuple(labels) if isinstance(labels, list) else labels)
            counts[key] = counts.get(key, 0) + 1
        expected = {(s, o): PAIRS_PER_SESSION_ORDER for s in SESSIONS for o in ORDERS}
        if counts != expected:
            raise AnalysisError(f"{phase} {cell_id}: pairs by (session, order) {sorted(counts.items(), key=repr)} "
                                f"differ from the balanced design {sorted(expected.items())}")


def analyze(main_dir: Path, extension_dir: Optional[Path], rules: str) -> Dict[str, Any]:
    """Main-phase decision, or the final decision when extension data is given."""
    if rules not in RULESETS:
        raise AnalysisError(f"Unknown rule set {rules!r}")
    main_pairs = load_pairs(main_dir, "main")
    _check_consistency(main_pairs)
    main_cells = _group(main_pairs)
    for cell_id, pairs in main_cells.items():
        if len(pairs) != MAIN_PAIRS_PER_CELL:
            raise AnalysisError(f"{cell_id}: {len(pairs)} main pairs, expected {MAIN_PAIRS_PER_CELL}")
    if rules == "v0.4.0":
        if sorted(main_cells) != sorted(QUALIFICATION_CELL_IDS):
            raise AnalysisError(f"Main cells {sorted(main_cells)} are not the approved nine "
                                f"{sorted(QUALIFICATION_CELL_IDS)}")
        _check_design(main_cells, "main")
    main_decision = {cell_id: evaluate_cell(cell_id, pairs, rules, final=False)
                     for cell_id, pairs in sorted(main_cells.items())}
    required = sorted(c for c, d in main_decision.items() if d["extension_required"])
    report: Dict[str, Any] = {
        "analysis": "knotrel-bc-qualification-decision",
        "rules": rules,
        "interval_definition": "paired log ratios ln(C/B); one-based order statistics "
                               "n=12 r(3),r(10); n=24 r(7),r(18)",
        "tolerances": TOLERANCES,
        "main_pairs": len(main_pairs),
        "extension_cells_required": required,
        "inputs": {"script_sha256": _sha256(Path(__file__).read_bytes()),
                   "main": _inputs_digest(main_pairs, main_dir, "main")},
    }
    if rules == "v0.4.0":
        report["report_only"] = {"reason": REPORT_ONLY_REASON,
                                 "metrics_by_cell": {c: list(m) for c, m in REPORT_ONLY.items()}}
    if extension_dir is None:
        report["phase"] = "main"
        report["cells"] = list(main_decision.values())
        return report

    if Path(extension_dir).resolve() == Path(main_dir).resolve():
        raise AnalysisError("The extension directory is the main directory")
    extension_pairs = load_pairs(extension_dir, "extension")
    if min(min(p["launches"]) for p in extension_pairs) <= max(max(p["completions"]) for p in main_pairs):
        raise AnalysisError("Extension observations were launched before the main phase ended")
    _check_consistency(main_pairs + extension_pairs)
    report["inputs"]["extension"] = _inputs_digest(extension_pairs, extension_dir, "extension")
    extension_cells = _group(extension_pairs)
    if sorted(extension_cells) != required:
        raise AnalysisError(f"Extension cells {sorted(extension_cells)} differ from required {required}")
    for cell_id, extra in sorted(extension_cells.items()):
        if len(extra) != MAIN_PAIRS_PER_CELL:
            raise AnalysisError(f"{cell_id}: {len(extra)} extension pairs, expected {MAIN_PAIRS_PER_CELL}")
    if rules == "v0.4.0":
        _check_design(extension_cells, "extension")
    final_cells = []
    for cell_id, pairs in sorted(main_cells.items()):
        extra = extension_cells.get(cell_id, [])
        final_cells.append(evaluate_cell(cell_id, list(pairs) + list(extra), rules, final=True))
    report["phase"] = "final"
    report["extension_pairs"] = len(extension_pairs)
    report["cells"] = final_cells
    if rules == "v0.4.0":
        report["main_cells"] = list(main_decision.values())
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--main", type=Path, required=True, help="Main-phase raw directory (pair_*.json).")
    parser.add_argument("--extension", type=Path, help="Extension-phase raw directory, for the final decision.")
    parser.add_argument("--rules", choices=RULESETS, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Output JSON file (must not exist).")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"{args.output} already exists")
    if not args.output.parent.is_dir():
        parser.error(f"{args.output.parent} is not a directory")
    try:
        report = analyze(args.main, args.extension, args.rules)
    except AnalysisError as error:
        print(f"analysis refused: {error}", file=sys.stderr)
        return 2
    except (TypeError, AttributeError, KeyError, ValueError, ArithmeticError, RecursionError) as error:
        print(f"analysis refused: malformed input ({type(error).__name__}: {error})", file=sys.stderr)
        return 2
    try:
        text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except ValueError as error:
        print(f"analysis refused: non-finite value in the report ({error})", file=sys.stderr)
        return 2
    try:
        with args.output.open("x") as handle:
            handle.write(text)
    except FileExistsError:
        print(f"analysis refused: {args.output} appeared during the analysis", file=sys.stderr)
        return 2
    summary = ", ".join(f"{c['cell_id']}={c['status']}" for c in report["cells"])
    print(f"{report['phase']} decision ({args.rules}): {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
