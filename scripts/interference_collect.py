#!/usr/bin/env python3
"""Collectors of qualification 3 under the proportional interference policy (revision 3).

The measuring code of every collector is imported unchanged. This module only decides the
**unit** each measured child belongs to and runs it through ``interference_gate``
(PROTOCOL section 14.4):

- ``a`` (experiment A, ``run_p0_aa``): its pair loop cannot repeat one pair, so the unit is
  the **whole block** (A main or A extension). Before each child the gate waits for an
  acceptable host; an invalid child raises ``BlockInvalid`` (exit 75) and the runner
  preserves the block's output and restarts the block.
- ``bc`` (``run_lifecycle_qualification``): the unit is the **cell**. One cell is one child
  that runs both arms, the warmup and the 12 pairs. An invalidated attempt's stdout/stderr
  are kept in ``BC/invalidated/``; the collector records only the valid attempt.
- ``r``, ``mreg`` (``run_v060_qualification.paired_experiment``): the unit is the **pair**
  (both arms). The pair order is generated exactly as the frozen function does (same RNG
  calls); a test pins the identity. An invalidated pair's children move from the run log's
  ``children`` to ``invalidated`` and their raw files to ``raw/invalidated/``.
- ``rmem``: the unit is the cell (its ``ref`` and ``cand`` children).
- ``mdesc``: unpaired; the unit is the child (one server configuration list).

Under this policy the frozen collectors' build-process checks (``check_no_builds``,
``competing_workloads`` in A's host state) are disabled: a build is judged by the external
CPU it uses, not by its presence. Their AC power and thermal checks stay.

    interference_collect.py a|bc|r|rmem|mdesc|mreg ARGS...   (with KNOTREL_INTERFERENCE_DIR)
"""

from __future__ import annotations

import json
import os
import random
import shutil
import subprocess as _subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import interference_gate as ig  # noqa: E402

MATRIX = SCRIPTS.parent / "results" / "v0.7.0-qualification-3" / "MATRIX.json"


# -- A ---------------------------------------------------------------------------------------
def _a(argv: List[str]) -> int:
    import run_p0_aa as collector
    observe = collector.observe_child
    validate = collector.validate_host_state

    def gated_observe(*args: Any, **kwargs: Any) -> Any:
        command = kwargs.get("argv", args[0] if args else [])
        label = f"A:{' '.join(str(a) for a in command)[:200]}"
        return ig.gate().block_child(label, lambda: observe(*args, **kwargs))

    def proportional_validate(current: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        return validate({**current, "competing_workloads": []}, *args, **kwargs)

    collector.observe_child = gated_observe
    collector.validate_host_state = proportional_validate
    sys.argv = ["run_p0_aa.py", *argv]
    return collector.main()


# -- B/C -------------------------------------------------------------------------------------
class _UnitSubprocess:
    """``subprocess`` stand-in for the B/C collector: each probe child is one unit (a cell)."""

    def __init__(self, measured: List[str], out: Path):
        self.measured = {os.path.realpath(p) for p in measured}
        self.out = out

    def __getattr__(self, name: str) -> Any:
        return getattr(_subprocess, name)

    def run(self, args: Any, *rest: Any, **kwargs: Any) -> Any:
        program = str(args[0]) if isinstance(args, (list, tuple)) and args else ""
        if os.path.realpath(program) not in self.measured:
            if program.startswith("/"):
                raise SystemExit(f"B/C collector started an undeclared program {program}")
            return _subprocess.run(args, *rest, **kwargs)
        label = f"BC:{' '.join(str(a) for a in args)[:200]}"
        unit = f"BC:{_bc_cell_id(args)}"
        holder: Dict[str, Any] = {}
        g = ig.gate()

        def children() -> Any:
            holder["result"] = g.child(label, lambda: _subprocess.run(args, *rest, **kwargs))
            return holder["result"]

        def preserve(attempt: int, reasons: List[str]) -> None:
            keep = self.out / "invalidated"
            keep.mkdir(parents=True, exist_ok=True)
            name = f"{_bc_cell_id(args)}.attempt{attempt}"
            result = holder.get("result")
            (keep / f"{name}.stdout").write_text(getattr(result, "stdout", "") or "")
            (keep / f"{name}.stderr").write_text(getattr(result, "stderr", "") or "")
            (keep / f"{name}.json").write_text(json.dumps({"argv": [str(a) for a in args], "reasons": reasons,
                                                           "exit": getattr(result, "returncode", None)}))
        return g.run_unit(unit, children, preserve)


#: Set by ``_bc`` from the collector's plan: argv tuple -> cell id.
_BC_IDS: Dict[tuple, str] = {}


def _bc_cell_id(args: Any) -> str:
    key = (os.path.realpath(str(args[0])), *(str(a) for a in args[1:]))
    if key not in _BC_IDS:
        raise SystemExit(f"B/C child not in the plan: {' '.join(key)[:200]}")
    return _BC_IDS[key]


def _bc(argv: List[str]) -> int:
    import run_lifecycle_qualification as collector
    measured = [argv[argv.index(f) + 1] for f in ("--core", "--core-count", "--http") if f in argv]
    out = Path(argv[argv.index("--out") + 1])
    apply = collector.apply_multipliers

    binaries = {name: os.path.realpath(argv[argv.index(flag) + 1])
                for name, flag in (("core", "--core"), ("core-count", "--core-count"), ("http", "--http"))
                if flag in argv}

    def recording_apply(cells: List[Dict[str, Any]], multipliers: Dict[str, int]) -> None:
        apply(cells, multipliers)
        for cell in cells:  # keyed by binary and arguments: core and core-count cells share arguments
            key = (binaries[cell["binary"]], *(str(a) for a in cell["args"]))
            if key in _BC_IDS:
                raise SystemExit(f"two B/C cells with the same binary and arguments: {cell['id']}")
            _BC_IDS[key] = cell["id"]

    collector.apply_multipliers = recording_apply
    collector.subprocess = _UnitSubprocess(measured, out)
    sys.argv = ["run_lifecycle_qualification.py", *argv]
    return collector.main()


# -- R, Rmem, M_desc, M_reg ----------------------------------------------------------------
def _recorder(experiment: str, argv: List[str]) -> int:
    import run_v060_qualification as collector
    collector.MATRIX = MATRIX
    collector.check_no_builds = lambda: None  # builds are judged by external CPU (revision 3)
    g = ig.gate()
    run = collector.Recorder.run

    def unit_run(self: Any, label: str, child_argv: List[str]) -> str:
        if g.in_unit:
            return g.child(f"{experiment}:{label}", lambda: run(self, label, child_argv))
        mark = len(self.log["children"])
        return g.run_unit(f"{experiment}:{label}",
                          lambda: g.child(f"{experiment}:{label}", lambda: run(self, label, child_argv)),
                          lambda attempt, reasons: invalidate(self, mark, attempt, reasons))

    def invalidate(rec: Any, mark: int, attempt: int, reasons: List[str]) -> None:
        moved = rec.log["children"][mark:]
        del rec.log["children"][mark:]
        keep = rec.out / "raw" / "invalidated"
        keep.mkdir(parents=True, exist_ok=True)
        for child in moved:
            for suffix in (".stdout", ".stderr"):
                source = rec.out / "raw" / f"{child['name']}{suffix}"
                if source.exists():
                    shutil.move(str(source), str(keep / source.name))
        rec.log.setdefault("invalidated", []).append({"attempt": attempt, "reasons": reasons, "children": moved})
        rec.flush()

    def paired_experiment(rec: Any, cells: List[Dict[str, Any]], arms: Dict[str, List[str]],
                          warmup: int, pairs: int, seed: int, run_cell: Any) -> None:
        rng = random.Random(seed)
        order = list(cells)
        rng.shuffle(order)
        for cell in order:
            orders = [["ref", "cand"], ["cand", "ref"]][:warmup] + collector.balanced_orders(pairs, rng.randrange(1 << 30))
            for index, arm_order in enumerate(orders):
                phase = "warmup" if index < warmup else "analyzed"
                mark = len(rec.log["children"])

                def pair(cell=cell, arm_order=arm_order, index=index, phase=phase) -> None:
                    for arm in arm_order:
                        run_cell(cell, arm, f"{cell['id']}-{phase}-{index:02d}-{arm}")

                g.run_unit(f"{experiment}:{cell['id']}-{phase}-{index:02d}", pair,
                           lambda attempt, reasons, mark=mark: invalidate(rec, mark, attempt, reasons))

    def cmd_rmem(args: Any, matrix: Dict[str, Any], rec: Any) -> None:
        for cell in matrix["experiments"]["Rmem"]["cells"]:
            mark = len(rec.log["children"])

            def both(cell=cell) -> None:
                for arm, binary in (("ref", args.ref), ("cand", args.cand)):
                    rec.run(f"{cell['id']}-{arm}", [binary] + cell["args"])

            g.run_unit(f"rmem:{cell['id']}", both,
                       lambda attempt, reasons, mark=mark: invalidate(rec, mark, attempt, reasons))

    collector.Recorder.run = unit_run
    collector.paired_experiment = paired_experiment
    collector.cmd_rmem = cmd_rmem
    sys.argv = ["run_v060_qualification.py", experiment, *argv]
    return collector.main()


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("a", "bc", "r", "rmem", "mdesc", "mreg"):
        print(__doc__, file=sys.stderr)
        return 2
    experiment, argv = sys.argv[1], sys.argv[2:]
    if "--dry-run" in argv:  # a dry run measures nothing and touches no gate
        import run_v070q3_collect as frozen
        sys.argv = ["run_v070q3_collect.py", experiment, *argv]
        return frozen.base.main()
    if experiment == "a":
        return _a(argv)
    if experiment == "bc":
        return _bc(argv)
    return _recorder(experiment, argv)


if __name__ == "__main__":
    sys.exit(main())
