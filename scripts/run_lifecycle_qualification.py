#!/usr/bin/env python3
"""Collector for the Knotrel v0.5.0 lifecycle qualification (experiments B and C).

Experiment A (existing behavior against v0.4.0) uses the v0.4.0 B/C pipeline
(``prepare_bc_qualification.py``, ``run_p0_aa.py``, ``analyze_bc_qualification.py``)
unchanged and is not run by this script.

The matrix is generated deterministically by :func:`matrix` and archived in
``plan/matrix.json`` before the first measurement. Cells run one at a time in an
order shuffled with ``--order-seed``. Each child's argv, timestamps, exit status,
stdout (raw JSON lines) and stderr are written under ``raw/``. The collector stops
at the first failing child; it never retries or skips a cell.

Usage (from the knotrel-benchmarks root, with ``tools/lifecycle-probes`` built in
both the default and ``count-alloc`` variants)::

    run_lifecycle_qualification.py --out DIR --profile pilot|final \\
        --core BIN --core-count BIN --http BIN --order-seed N [--dry-run]

``--profile pilot`` runs every cell with two pairs and no warmup (B) and three
cycles (C) to estimate durations; it is never used for decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from cli_paths import confined, confined_directory, confined_executable

ENGINES = ("compact-bfs", "ett", "hdt")
#: Engines added later, in scope only when named in ``--lifecycle-engines`` (CF5:
#: ``cluster-forest``), so every earlier matrix, the default included, is unchanged.
OPTIONAL_ENGINES = ("cluster-forest",)
SEED = 5_000_001


def apply_multipliers(cells: List[Dict[str, Any]], multipliers: Dict[str, int]) -> None:
    """Scales B1-B3 ``--window`` and B4 ``--requests`` by the pilot-derived factor.

    Factors come from the pilot's medians of *both* arms (target: the faster arm's window
    >= 2 ms; powers of two, at most 64). Every B1-B4 cell must have a factor and no unknown
    key is accepted, so the frozen windows are exactly the ones that run.
    """
    timed = {c["id"] for c in cells if c["experiment"] in ("B1", "B2", "B3", "B4")}
    unknown = set(multipliers) - timed
    missing = timed - set(multipliers)
    if unknown or missing:
        raise SystemExit(f"window multipliers: unknown {sorted(unknown)[:5]}, missing {sorted(missing)[:5]}")
    for cell in cells:
        if cell["id"] not in timed:
            continue
        factor = int(multipliers[cell["id"]])
        flag = "--requests" if cell["experiment"] == "B4" else "--window"
        index = cell["args"].index(flag) + 1
        cell["args"][index] = str(int(cell["args"][index]) * factor)
        cell["scale"] = factor


ALL_LIFECYCLE_ENGINES = ",".join(ENGINES)


#: Suffixes of twin cells that run right after their frozen counterpart, in this order
#: (qualification 3: ``-equivalent-``; knotrel#180: ``-atomic-``).
TWIN_SUFFIXES = ("-equivalent-", "-atomic-")


def _twin_suffix(cell_id: str) -> str:
    """The twin suffix of ``cell_id``, or an empty string for a frozen cell."""
    found = [suffix for suffix in TWIN_SUFFIXES if suffix in cell_id]
    if len(found) > 1:
        raise SystemExit(f"cell with more than one twin suffix: {cell_id}")
    return found[0] if found else ""


def run_order(cells: List[Dict[str, Any]], seed: int) -> List[int]:
    """Indices of ``cells`` in run order.

    Without twin cells: the frozen rule, a ``random.Random(seed)`` shuffle of all
    indices. With them, the frozen cells keep exactly the order the frozen rule gives
    them on their own, and each twin runs right after its frozen counterpart, so the
    frozen sequence is unchanged: a ``*-equivalent`` cell (qualification 3) first, then
    a ``*-atomic`` cell (knotrel#180, application-gate reference). Without ``-atomic-``
    cells the order is exactly the qualification-3 order.
    """
    frozen = [i for i, c in enumerate(cells) if not _twin_suffix(c["id"])]
    shuffled = list(range(len(frozen)))
    random.Random(seed).shuffle(shuffled)
    if len(frozen) == len(cells):
        return shuffled
    twins: Dict[str, Dict[str, int]] = {}
    for i, c in enumerate(cells):
        suffix = _twin_suffix(c["id"])
        if not suffix:
            continue
        slot = twins.setdefault(c["id"].replace(suffix, "-"), {})
        if suffix in slot:
            raise SystemExit(f"duplicate {suffix.strip('-')} cells")
        slot[suffix] = i
    order: List[int] = []
    for k in shuffled:
        index = frozen[k]
        order.append(index)
        slot = twins.pop(cells[index]["id"], {})
        order.extend(slot[suffix] for suffix in TWIN_SUFFIXES if suffix in slot)
    if twins:
        raise SystemExit(f"twin cells without a frozen counterpart: "
                         f"{sorted(cells[i]['id'] for slot in twins.values() for i in slot.values())}")
    return order


def in_lifecycle_scope(cell: Dict[str, Any], lifecycle_engines: str) -> bool:
    """Whether ``cell`` belongs to a qualification restricted to ``lifecycle_engines``.

    A cell is kept when its engine supports lifecycle in this scope, or when it
    measures no lifecycle at all (``metrics-legacy``: two lifecycle-disabled
    servers). Every other cell of an excluded engine measures lifecycle support
    (or is the paired reference of a lifecycle arm in B5/C) and is dropped.
    """
    args = cell["args"]
    engine = args[args.index("--engine") + 1]
    if engine in lifecycle_engines.split(","):
        return True
    if engine in OPTIONAL_ENGINES:
        return False
    return "--scenario" in args and args[args.index("--scenario") + 1] == "metrics-legacy"


def matrix(profile: str, lifecycle_engines: str = ALL_LIFECYCLE_ENGINES,
           equivalent: bool = False, atomic: bool = False) -> List[Dict[str, Any]]:
    """Every cell of experiments B and C within the lifecycle-engine scope.

    ``profile`` only shrinks repetition counts. The default scope (all engines)
    reproduces the original matrix; amendment 4 restricts it to ``compact-bfs``.
    ``equivalent`` (v0.7.0 qualification 3) adds the capability-equivalent B4
    cells (``*-equivalent`` scenarios, same tolerances and request counts) beside
    the frozen ones; without it the matrix is unchanged. ``atomic`` (knotrel#180,
    decision M1(b)) adds the application-gate reference cells of :data:`ATOMIC_CELLS`
    beside their frozen counterparts; without it the matrix is unchanged.
    """
    unknown = set(lifecycle_engines.split(",")) - set(ENGINES) - set(OPTIONAL_ENGINES)
    if unknown or not lifecycle_engines:
        raise SystemExit(f"unknown lifecycle engines: {sorted(unknown)}")
    return [c for c in _full_matrix(profile, equivalent, atomic) if in_lifecycle_scope(c, lifecycle_engines)]


#: Scenarios whose reference gets a capability-equivalent variant (qualification 3).
EQUIVALENT_SCENARIOS = ("ops", "ops-query", "events", "import")

#: Application-gate (``-atomic``) reference cells (knotrel#180, decisions M1(b) and M4):
#: (scenario, engine, topology, nodes). ``ops`` on the compact-bfs hub 10k only; ``events``
#: has no atomic reference (written disposition).
ATOMIC_CELLS = (("ops", "compact-bfs", "hub", 10_000),)


def _full_matrix(profile: str, equivalent: bool = False, atomic: bool = False) -> List[Dict[str, Any]]:
    """Every cell of experiments B and C. ``profile`` only shrinks repetition counts."""
    pairs, warmup = (2, 0) if profile == "pilot" else (12, 2)
    cycles = 3 if profile == "pilot" else 30
    cells: List[Dict[str, Any]] = []

    def pair_args(**kv: Any) -> List[str]:
        out: List[str] = []
        for key, value in kv.items():
            out += [f"--{key.replace('_', '-')}", str(value)]
        return out + ["--pairs", str(pairs), "--warmup", str(warmup), "--seed", str(SEED)]

    def core(cell_id: str, experiment: str, tolerance: float, **kv: Any) -> None:
        cells.append({"id": cell_id, "experiment": experiment, "tolerance": tolerance,
                      "binary": "core", "args": ["pairs"] + pair_args(**kv)})

    for engine in ENGINES + OPTIONAL_ENGINES:
        for topology in ("sparse", "ring", "hub"):
            for nodes in (1_000, 10_000, 100_000):
                for mix in ("query", "mutation"):
                    core(f"B1-ops-{engine}-{topology}-{nodes}-{mix}", "B1", 0.25, exp="ops",
                         engine=engine, topology=topology, nodes=nodes, mix=mix, window=4000)
                core(f"B2-optin-{engine}-{topology}-{nodes}", "B2", 0.50, exp="optin", engine=engine,
                     topology=topology, nodes=nodes, mix="legacy", window=4000)
        # Fresh-ID churn: enough removals for at least one compaction per window.
        for nodes, window in ((1_000, 8_000), (10_000, 48_000)):
            core(f"B1-ops-{engine}-sparse-{nodes}-fresh-churn", "B1", 0.25, exp="ops", engine=engine,
                 topology="sparse", nodes=nodes, mix="fresh-churn", window=window)
        for degree, window in ((16, 3000), (256, 600), (4096, 300), (16384, 60)):
            core(f"B3-degree-{engine}-{degree}", "B3", 0.25, exp="degree", engine=engine,
                 degree=degree, window=window, topology="sparse", nodes=0, mix="mutation")
        for degree, cycles_ in ((16, 200), (256, 20), (4096, 2), (16384, 1)):
            core(f"B3-degree-remove-{engine}-{degree}", "B3", 0.25, exp="degree-remove",
                 engine=engine, degree=degree, window=cycles_, topology="sparse", nodes=0,
                 mix="mutation")

    def http(cell_id: str, tolerance: float, **kv: Any) -> None:
        cells.append({"id": cell_id, "experiment": "B4", "tolerance": tolerance, "binary": "http",
                      "args": pair_args(**kv)})

    scenarios = (("optin-mutation", 0.50, 40), ("optin-query", 0.25, 4), ("ops", 0.25, 40),
                 ("ops-query", 0.25, 8), ("events", 0.25, 40), ("import", 1.00, 1),
                 ("import-optin", 1.00, 1))
    for engine in ENGINES + OPTIONAL_ENGINES:
        for topology in ("sparse", "hub"):
            for scenario, tolerance, requests in scenarios:
                http(f"B4-http-{scenario}-{engine}-{topology}-10000", tolerance, scenario=scenario,
                     engine=engine, topology=topology, nodes=10_000, requests=requests)
                if equivalent and scenario in EQUIVALENT_SCENARIOS:
                    http(f"B4-http-{scenario}-equivalent-{engine}-{topology}-10000", tolerance,
                         scenario=f"{scenario}-equivalent", engine=engine, topology=topology,
                         nodes=10_000, requests=requests)
                if atomic and (scenario, engine, topology, 10_000) in ATOMIC_CELLS:
                    # The counterpart's requests (40) and tolerance (25%).
                    http(f"B4-http-{scenario}-atomic-{engine}-{topology}-10000", tolerance,
                         scenario=f"{scenario}-atomic", engine=engine, topology=topology,
                         nodes=10_000, requests=requests)
        http(f"B4-http-import-high-{engine}-sparse-10000", 1.00, scenario="import", engine=engine,
             topology="sparse", nodes=10_000, requests=1, inactive_percent=60, disabled_percent=30)
        if equivalent:
            http(f"B4-http-import-high-equivalent-{engine}-sparse-10000", 1.00,
                 scenario="import-equivalent", engine=engine, topology="sparse", nodes=10_000,
                 requests=1, inactive_percent=60, disabled_percent=30)
        for scenario, requests in (("metrics-ops", 40), ("metrics-legacy", 40)):
            http(f"B4-http-{scenario}-{engine}-sparse-10000", 0.06, scenario=scenario,
                 engine=engine, topology="sparse", nodes=10_000, requests=requests)
    for scenario, tolerance, requests in scenarios:
        if scenario.startswith("optin"):
            continue
        http(f"B4-http-{scenario}-compact-bfs-sparse-100000", tolerance, scenario=scenario,
             engine="compact-bfs", topology="sparse", nodes=100_000, requests=requests)
        if equivalent and scenario in EQUIVALENT_SCENARIOS:
            http(f"B4-http-{scenario}-equivalent-compact-bfs-sparse-100000", tolerance,
                 scenario=f"{scenario}-equivalent", engine="compact-bfs", topology="sparse",
                 nodes=100_000, requests=requests)

    for engine in ENGINES + OPTIONAL_ENGINES:
        for topology in ("sparse", "hub"):
            for arm in ("plain", "lifecycle", "reference"):
                cells.append({
                    "id": f"B5-memory-{arm}-{engine}-{topology}-100000", "experiment": "B5",
                    "binary": "core-count",
                    "args": ["resources", "--arm", arm, "--engine", engine, "--topology", topology,
                             "--nodes", "100000", "--cycles", "0", "--churn-percent", "0",
                             "--reuse", "none", "--seed", str(SEED)]})
        sizes = {"sparse": (1_000, 10_000, 100_000), "ring": (100_000,), "hub": (100_000,)}
        for topology, node_counts in sizes.items():
            for nodes in node_counts:
                for reuse in ("fresh", "same", "toggle"):
                    for variant, binary in (("heap", "core-count"), ("rss", "core")):
                        for arm in ("lifecycle", "reference"):
                            cells.append({
                                "id": f"C-{variant}-{arm}-{engine}-{topology}-{reuse}-{nodes}",
                                "experiment": "C", "binary": binary,
                                "args": ["resources", "--arm", arm, "--engine", engine,
                                         "--topology", topology, "--nodes", str(nodes),
                                         "--cycles", str(cycles), "--churn-percent", "5",
                                         "--reuse", reuse, "--seed", str(SEED)]})
    return cells


def sha256(path: Path) -> str:
    return hashlib.sha256(confined(path, "hashed file").read_bytes()).hexdigest()


def git(directory: Path, *args: str) -> str:
    directory = confined_directory(directory, "git directory")
    return subprocess.run(["git", "-C", str(directory), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def host_state() -> Dict[str, Any]:
    def run(cmd: List[str]) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            return f"unavailable: {error}"
    return {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "power": run(["pmset", "-g", "batt"]),
            "load": os.getloadavg(), "therm": run(["pmset", "-g", "therm"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", choices=("pilot", "final"), required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--core-count", type=Path, required=True)
    parser.add_argument("--http", type=Path, required=True)
    parser.add_argument("--order-seed", type=int, required=True)
    parser.add_argument("--knotrel", type=Path, required=True, help="candidate knotrel checkout")
    parser.add_argument("--only", default="", help="comma-separated experiment filter (B1,B2,...,C)")
    parser.add_argument("--lifecycle-engines", default=ALL_LIFECYCLE_ENGINES,
                        help="engines whose lifecycle cells are in scope (amendment 4: compact-bfs)")
    parser.add_argument("--window-multipliers", type=Path,
                        help="pilot-derived JSON {cell id: factor}; archived in plan/")
    parser.add_argument("--equivalent-references", action="store_true",
                        help="add the capability-equivalent B4 cells (v0.7.0 qualification 3)")
    parser.add_argument("--atomic-references", action="store_true",
                        help="add the application-gate B4 reference cells (knotrel#180)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    args.out = confined(args.out, "--out")
    args.core = confined_executable(args.core, "--core")
    args.core_count = confined_executable(args.core_count, "--core-count")
    args.http = confined_executable(args.http, "--http")
    args.knotrel = confined_directory(args.knotrel, "--knotrel")
    if args.window_multipliers:
        args.window_multipliers = confined(args.window_multipliers, "--window-multipliers")
    benchmarks = confined_directory(Path.cwd(), "working directory")
    if args.out.exists():
        print(f"refusing to reuse existing output directory {args.out}", file=sys.stderr)
        return 2
    binaries = {"core": args.core, "core-count": args.core_count, "http": args.http}
    cells = matrix(args.profile, args.lifecycle_engines, args.equivalent_references, args.atomic_references)
    # The multipliers scale only the timed B1-B4 cells: a final run whose --only filter keeps
    # none of them (CF5 L2: --only C) needs none; every other final run still requires them.
    wanted_experiments = set(args.only.split(",")) if args.only else None
    timed_in_scope = any(c["experiment"] in ("B1", "B2", "B3", "B4")
                         and (wanted_experiments is None or c["experiment"] in wanted_experiments)
                         for c in cells)
    if args.profile == "final" and not args.window_multipliers and timed_in_scope:
        print("--window-multipliers is required for the final profile", file=sys.stderr)
        return 2
    if args.window_multipliers:
        apply_multipliers(cells, json.loads(args.window_multipliers.read_text()))
    if args.only:
        wanted = set(args.only.split(","))
        cells = [cell for cell in cells if cell["experiment"] in wanted]
    order = run_order(cells, args.order_seed)
    provenance = {
        "profile": args.profile, "order_seed": args.order_seed, "seed": SEED,
        "only": args.only, "cells": len(cells), "lifecycle_engines": args.lifecycle_engines,
        "equivalent_references": args.equivalent_references,
        **({"atomic_references": True} if args.atomic_references else {}),
        "knotrel": {"path": str(args.knotrel.resolve()), "head": git(args.knotrel, "rev-parse", "HEAD"),
                    "dirty": git(args.knotrel, "status", "--porcelain")},
        "benchmarks": {"head": git(benchmarks, "rev-parse", "HEAD"),
                       "dirty": git(benchmarks, "status", "--porcelain")},
        "binaries": {name: {"path": str(path.resolve()), "sha256": sha256(path)} for name, path in binaries.items()},
        "rustc": subprocess.run(["rustc", "+1.100.0", "-Vv"], capture_output=True, text=True).stdout,
        "platform": platform.platform(), "machine": platform.machine(),
        "window_multipliers": (str(args.window_multipliers.resolve()) if args.window_multipliers else None),
        "window_multipliers_sha256": (sha256(args.window_multipliers) if args.window_multipliers else None),
    }
    if args.dry_run:
        print(json.dumps({"cells": len(cells), "provenance": provenance}, indent=1))
        return 0
    (args.out / "plan").mkdir(parents=True)
    (args.out / "raw").mkdir()
    (args.out / "plan" / "matrix.json").write_text(json.dumps(cells, indent=1))
    (args.out / "plan" / "order.json").write_text(json.dumps([cells[i]["id"] for i in order], indent=1))
    (args.out / "provenance.json").write_text(json.dumps(provenance, indent=1))
    log = (args.out / "run-log.jsonl").open("a")
    for position, index in enumerate(order):
        cell = cells[index]
        argv = [str(confined_executable(binaries[cell["binary"]], cell["binary"]))] + cell["args"]
        before = host_state()
        start = time.monotonic()
        child = subprocess.run(argv, capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
        elapsed = time.monotonic() - start
        (args.out / "raw" / f"{cell['id']}.jsonl").write_text(child.stdout)
        (args.out / "raw" / f"{cell['id']}.stderr").write_text(child.stderr)
        record = {"position": position, "id": cell["id"], "argv": argv, "exit": child.returncode,
                  "seconds": round(elapsed, 3), "host_before": before}
        log.write(json.dumps(record) + "\n")
        log.flush()
        print(f"[{position + 1}/{len(cells)}] {cell['id']} exit={child.returncode} {elapsed:.1f}s", flush=True)
        if child.returncode != 0:
            print(f"stopping: {cell['id']} failed: {child.stderr.strip()[:500]}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
