#!/usr/bin/env python3
"""Collectors of the v0.7.0 re-qualification, each wrapped by the conformance gate.

The measuring code of every collector is the frozen code of the first v0.7.0
campaign, imported unchanged. This wrapper only inserts
``conformance_gate.gated`` around the one call that runs a measured child:

- ``a``: ``run_p0_aa.observe_child`` (one A observation); arguments as
  ``run_p0_aa.py``;
- ``bc``: the ``subprocess.run`` in ``run_lifecycle_qualification.main`` whose
  program is one of the three probe binaries given with ``--core``,
  ``--core-count`` and ``--http`` (one B/C cell). Provenance calls (``git``,
  ``rustc``, ``pmset``) use bare names and are not gated. Any other
  absolute-path program stops the collector (``GateStop``). Arguments as
  ``run_lifecycle_qualification.py``;
- ``r``, ``rmem``, ``mdesc``, ``mreg``: ``run_v060_qualification.Recorder.run``
  (one R, Rmem or M child), bound to
  ``results/v0.7.0-requalification/MATRIX.json``; arguments as
  ``run_v060_qualification.py``.

``KNOTREL_GATE_DIR`` must be set; without it every gated call refuses to run.

    run_v070r_collect.py a|bc|r|rmem|mdesc|mreg ARGS...
"""

from __future__ import annotations

import os
import subprocess as _subprocess
import sys
from pathlib import Path
from typing import Any, List

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import conformance_gate  # noqa: E402

MATRIX = SCRIPTS.parent / "results" / "v0.7.0-requalification" / "MATRIX.json"


def _a(argv: List[str]) -> int:
    import run_p0_aa as collector
    observe = collector.observe_child

    def gated_observe(*args: Any, **kwargs: Any) -> Any:
        command = kwargs.get("argv", args[0] if args else [])
        label = f"A:{' '.join(str(a) for a in command)[:200]}"
        return conformance_gate.gated(label, lambda: observe(*args, **kwargs))

    collector.observe_child = gated_observe
    sys.argv = ["run_p0_aa.py", *argv]
    return collector.main()


class _GatedSubprocess:
    """``subprocess`` stand-in for the B/C collector: gates the declared probe binaries."""

    def __init__(self, measured: List[str]):
        self.measured = {os.path.realpath(p) for p in measured}

    def __getattr__(self, name: str) -> Any:
        return getattr(_subprocess, name)

    def run(self, args: Any, *rest: Any, **kwargs: Any) -> Any:
        program = str(args[0]) if isinstance(args, (list, tuple)) and args else ""
        if os.path.realpath(program) in self.measured:
            label = f"BC:{' '.join(str(a) for a in args)[:200]}"
            return conformance_gate.gated(label, lambda: _subprocess.run(args, *rest, **kwargs))
        if program.startswith("/"):
            message = f"B/C collector started an undeclared program {program}"
            conformance_gate.gate()._stop(f"BC:{program}", "before", [message])
            raise conformance_gate.GateStop(message)
        return _subprocess.run(args, *rest, **kwargs)


def _measured_binaries(argv: List[str]) -> List[str]:
    found = []
    for flag in ("--core", "--core-count", "--http"):
        if flag in argv and argv.index(flag) + 1 < len(argv):
            found.append(argv[argv.index(flag) + 1])
    return found


def _bc(argv: List[str]) -> int:
    import run_lifecycle_qualification as collector
    collector.subprocess = _GatedSubprocess(_measured_binaries(argv))
    sys.argv = ["run_lifecycle_qualification.py", *argv]
    return collector.main()


def _recorder(experiment: str, argv: List[str]) -> int:
    import run_v060_qualification as collector
    collector.MATRIX = MATRIX
    run = collector.Recorder.run

    def gated_run(self: Any, label: str, child_argv: List[str]) -> str:
        return conformance_gate.gated(f"{experiment}:{label}", lambda: run(self, label, child_argv))

    collector.Recorder.run = gated_run
    sys.argv = ["run_v060_qualification.py", experiment, *argv]
    return collector.main()


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("a", "bc", "r", "rmem", "mdesc", "mreg"):
        print(__doc__, file=sys.stderr)
        return 2
    experiment, argv = sys.argv[1], sys.argv[2:]
    if experiment == "a":
        return _a(argv)
    if experiment == "bc":
        return _bc(argv)
    return _recorder(experiment, argv)


if __name__ == "__main__":
    sys.exit(main())
