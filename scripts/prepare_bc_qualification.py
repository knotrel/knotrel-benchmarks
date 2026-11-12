#!/usr/bin/env python3
"""Generate a Knotrel v0.3.0 baseline/candidate (B/C) qualification plan.

Derives the approved cells from the Increment 1 manifest (read-only) and writes a new
manifest.json and schedule.json for run_p0_aa.py. It runs no benchmark.

- Cell parameters and argv are copied from the source manifest; only the binary
  paths change per label, and standalone-batch cells gain
  ``--batch-warmup-chunk-size 50`` (knotrel docs/release-v0.3.0-closure-plan.md §5.2).
- Schedule (§5.3): 3 sessions; each cell gets 2 B->C and 2 C->B pairs per session.
  Within a session, the slots of all cells are shuffled with the recorded session seed.
- Identities come from a JSON file with ``comparison_identities`` (labels B and C) and
  ``shared_binaries`` (``measure_e2e``), in the format validated by run_p0_aa.py.

The output directory must not exist. Generating a plan does not verify provenance;
run ``run_p0_aa.py --dry-run`` on the result for that.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_p0_aa as p0

DEFAULT_SOURCE_MANIFEST = p0.ROOT.parent / "evidence/p0-coverage-increment-1-plan-20261030/manifest.json"
DEFAULT_SESSION_SEEDS = {"main": (130300, 130301, 130302), "extension": (130310, 130311, 130312)}
LAUNCH_SOURCE_FIELDS = ("executable", "server_binary", "server_binary_sha256", "cwd", "argv", "env")


class PlanError(Exception):
    """The source manifest or identities cannot produce an approved plan."""


def _label_launch(source: Dict[str, Any], identities: Dict[str, Any], shared: Dict[str, Any], label: str) -> Dict[str, Any]:
    binaries = identities[label]["binaries"]
    argv = list(source["argv"])
    env = dict(source["env"])
    if source["type"] == "core":
        harness = binaries["knotrel_benchmarks"]["path"]
        return {
            "executable": harness,
            "cwd": identities[label]["checkouts"]["benchmarks_source"]["path"],
            "argv": [harness] + argv[1:],
            "env": env,
        }
    driver = shared["measure_e2e"]
    server = binaries["knotrel_server"]
    if argv.count("--server-bin") != 1 or argv.index("--server-bin") + 1 >= len(argv):
        raise PlanError(f"Source cell {source['cell_id']} must pass exactly one --server-bin value")
    argv[0] = driver["path"]
    argv[argv.index("--server-bin") + 1] = server["path"]
    if source.get("scenario") == "standalone-batch" and "--batch-warmup-chunk-size" not in argv:
        argv += ["--batch-warmup-chunk-size", str(p0.QUALIFICATION_BATCH_WARMUP_CHUNK_SIZE)]
    env["KNOTREL_BIN"] = server["path"]
    return {
        "executable": driver["path"],
        "server_binary": server["path"],
        "server_binary_sha256": server["sha256"],
        "cwd": driver["source_checkout"],
        "argv": argv,
        "env": env,
    }


def build_cells(source_manifest: Dict[str, Any], cell_ids: Sequence[str], identities: Dict[str, Any],
                shared: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Copy the selected source cells and bind each label's launch to its own binaries."""
    by_id = {cell["cell_id"]: cell for cell in source_manifest["pilot_design"]["cells"]}
    cells = []
    for cell_id in cell_ids:
        if cell_id not in by_id:
            raise PlanError(f"Cell {cell_id} not found in the source manifest")
        source = by_id[cell_id]
        if source["argv"][0] != source["executable"]:
            raise PlanError(f"Source cell {cell_id} argv[0] does not match its executable")
        cell = {key: copy.deepcopy(value) for key, value in source.items() if key not in LAUNCH_SOURCE_FIELDS}
        kind = "core" if source["type"] == "core" else source.get("scenario")
        cell["primary_metric"] = p0.QUALIFICATION_PRIMARY_METRICS[kind]
        if kind == "standalone-batch":
            cell["warmup_chunk_size"] = p0.QUALIFICATION_BATCH_WARMUP_CHUNK_SIZE
        cell["launch_by_label"] = {label: _label_launch(source, identities, shared, label) for label in p0.BC_LABELS}
        cells.append(cell)
    return cells


def build_schedule_pairs(cells: List[Dict[str, Any]], seeds: Sequence[int],
                         pairs_per_cell_per_session: int) -> List[Dict[str, Any]]:
    """Return balanced pairs: per session, half B->C and half C->B per cell, shuffled by seed."""
    forward, reverse = list(p0.BC_LABELS), list(reversed(p0.BC_LABELS))
    half = pairs_per_cell_per_session // 2
    pairs = []
    for session, seed in enumerate(seeds):
        slots = [(cell, labels) for cell in cells for labels in [forward] * half + [reverse] * half]
        random.Random(seed).shuffle(slots)
        for cell, labels in slots:
            pairs.append({
                "pair_id": len(pairs),
                "session": session,
                "cell_id": cell["cell_id"],
                "cell_type": cell["type"],
                "engine": cell.get("engine"),
                "workload": cell.get("workload"),
                "labels": list(labels),
                "launch_by_label": copy.deepcopy(cell["launch_by_label"]),
            })
    return pairs


def build_plan(source_manifest: Dict[str, Any], source_manifest_sha256: str, identities_doc: Dict[str, Any],
               phase: str, cell_ids: Sequence[str], seeds: Sequence[int],
               checkpoint: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Build and structurally validate a B/C qualification manifest and schedule."""
    if phase not in p0.QUALIFICATION_PHASES:
        raise PlanError(f"Unknown phase {phase!r}")
    if len(seeds) != p0.QUALIFICATION_SESSIONS_COUNT or len(set(seeds)) != len(seeds):
        raise PlanError(f"Exactly {p0.QUALIFICATION_SESSIONS_COUNT} distinct session seeds are required")
    identities = identities_doc.get("comparison_identities")
    shared = identities_doc.get("shared_binaries")
    if not isinstance(shared, dict) or not shared.get("measure_e2e", {}).get("source_checkout"):
        raise PlanError("shared_binaries.measure_e2e.source_checkout is required (HTTP working directory)")
    per_session = p0.QUALIFICATION_PAIRS_PER_CELL_PER_SESSION
    cells = build_cells(source_manifest, cell_ids, identities, shared)
    pairs = build_schedule_pairs(cells, seeds, per_session)
    pairs_per_cell = per_session * len(seeds)
    lifecycle = sum(1 for c in cells if c["type"] == "http" and c.get("scenario") == "lifecycle")
    batch = sum(1 for c in cells if c["type"] == "http" and c.get("scenario") == "standalone-batch")
    child = {
        "http_lifecycle_servers": lifecycle * pairs_per_cell * 2 * 2,
        "http_standalone_batch_servers": batch * pairs_per_cell * 2,
        "description": "Lifecycle launches start a primary and a restart server; batch launches start one server.",
    }
    child["total_child_servers"] = child["http_lifecycle_servers"] + child["http_standalone_batch_servers"]
    now = datetime.datetime.now(datetime.timezone.utc)
    checkpoint = checkpoint or f"v0.3.0-Qualification-{phase.capitalize()}"
    manifest = {
        "schema": "knotrel-p0-pilot-manifest-bc-v1",
        "checkpoint": checkpoint,
        "status": "prepared_not_executed",
        "timestamp_utc": now.isoformat(),
        "comparison_model": (
            "Interleaved paired baseline (B) / candidate (C) comparison; per-label server and core harness, "
            "shared HTTP driver (knotrel docs/release-v0.3.0-closure-plan.md §5)"
        ),
        "provenance": {"comparison_identities": copy.deepcopy(identities), "shared_binaries": copy.deepcopy(shared)},
        "pilot_design": {
            "comparison_mode": p0.BASELINE_CANDIDATE_MODE,
            "qualification_protocol": p0.QUALIFICATION_PROTOCOL,
            "phase": phase,
            "labels": list(p0.BC_LABELS),
            "total_cells": len(cells),
            "core_cells": sum(1 for c in cells if c["type"] == "core"),
            "http_cells": sum(1 for c in cells if c["type"] == "http"),
            "pairs_per_cell": pairs_per_cell,
            "pairs_per_cell_per_session": per_session,
            "total_pairs": len(pairs),
            "total_measured_launches": 2 * len(pairs),
            "additional_child_launches": child,
            "total_process_launches": 2 * len(pairs) + child["total_child_servers"],
            "sessions_count": len(seeds),
            "session_seeds": list(seeds),
            "source_manifest": {"checkpoint": source_manifest.get("checkpoint"), "sha256": source_manifest_sha256},
            "cells": cells,
        },
        "resource_budget": {
            "per_process_timeout_seconds": p0.PER_PROCESS_TIMEOUT_SECONDS,
            "per_stream_capture_bytes": p0.DEFAULT_STREAM_LIMIT_BYTES,
            "overall_deadline_seconds": p0.PROPOSED_OVERALL_DEADLINE_SECONDS,
            "bundle_ceiling_bytes": p0.QUALIFICATION_BUNDLE_CEILING_BYTES,
            "core_peak_rss_retrospective_ceiling_bytes": p0.PROPOSED_PEAK_RSS_CEILING_BYTES,
            "http_server_rss": "sampled and recorded; no ceiling is enforced",
        },
    }
    sessions = []
    for index, seed in enumerate(seeds):
        session = {
            "session_id": index,
            "seed": seed,
            "pair_count": per_session * len(cells),
            "pre_quiet_seconds": p0.PER_SESSION_PRE_QUIET_SECONDS,
        }
        if index:
            session["inter_session_cooldown_seconds"] = p0.INTER_SESSION_COOLDOWN_SECONDS
        sessions.append(session)
    schedule = {
        "schema": "knotrel-p0-pilot-schedule-bc-v1",
        "checkpoint": checkpoint,
        "total_cells": len(cells),
        "total_pairs": len(pairs),
        "total_measured_runs": 2 * len(pairs),
        "sessions": sessions,
        "pairs": pairs,
    }
    try:
        p0.validate_inputs(manifest, schedule, check_provenance=False)
    except p0.ConfigurationValidationError as exc:
        raise PlanError(f"Generated plan failed structural validation: {exc}") from exc
    return {"manifest": manifest, "schedule": schedule}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_dir", type=Path, help="New plan directory (must not exist).")
    parser.add_argument("--identities", type=Path, required=True, help="Label and shared binary identities JSON.")
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST,
                        help="Increment 1 manifest providing the cell definitions (read-only).")
    parser.add_argument("--phase", choices=p0.QUALIFICATION_PHASES, default="main")
    parser.add_argument("--cells", nargs="+", help="Extension phase only: inconclusive cells to rerun.")
    parser.add_argument("--session-seeds", type=int, nargs=p0.QUALIFICATION_SESSIONS_COUNT,
                        help="Per-session shuffle seeds (default: fixed per phase).")
    parser.add_argument("--checkpoint", help="Override the manifest checkpoint label.")
    args = parser.parse_args(argv)

    if args.phase == "main" and args.cells:
        parser.error("--cells is only valid with --phase extension; the main phase runs all approved cells")
    if args.phase == "extension" and not args.cells:
        parser.error("--phase extension requires --cells")
    if args.output_dir.exists():
        parser.error(f"Output directory already exists: {args.output_dir}")
    cell_ids = args.cells or list(p0.QUALIFICATION_CELL_IDS)
    seeds = args.session_seeds or DEFAULT_SESSION_SEEDS[args.phase]
    try:
        plan = build_plan(
            p0.read_json(args.source_manifest), p0.digest(args.source_manifest), p0.read_json(args.identities),
            args.phase, cell_ids, seeds, args.checkpoint,
        )
    except (PlanError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True)
    p0.save_json(args.output_dir / "manifest.json", plan["manifest"])
    p0.save_json(args.output_dir / "schedule.json", plan["schedule"])
    print(f"Wrote {plan['schedule']['total_pairs']} pairs for {len(cell_ids)} cells to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
