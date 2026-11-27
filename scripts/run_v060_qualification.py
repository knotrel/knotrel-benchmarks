#!/usr/bin/env python3
"""Collector for the knotrel v0.6.0 qualification experiments R, Rmem, M_desc and M_reg.

Experiments A (v0.4.0 pipeline) and B/C (``run_lifecycle_qualification.py``) use
their existing collectors unchanged. This collector reads the frozen
``results/v0.6.0-qualification/MATRIX.json``, refuses to run unless
``FREEZE.json`` exists next to it (``--dry-run`` and ``--pilot`` excepted), and
writes every child's argv, timestamps, exit status, stdout and stderr under the
output directory, which must not exist yet.

Host checks before every child: AC power (``pmset -g batt``) and no recorded
thermal or performance warning (``pmset -g therm``); before every experiment:
no ``cargo``/``rustc`` process. A failed check or a failing child stops the run.

Usage (from the knotrel-benchmarks root)::

    run_v060_qualification.py r     --out DIR --ref BIN --cand BIN
    run_v060_qualification.py rmem  --out DIR --ref BIN --cand BIN
    run_v060_qualification.py mdesc --out DIR --probe BIN --server BIN
    run_v060_qualification.py mreg  --out DIR --probe BIN --ref BIN --cand BIN
        [--dry-run] [--pilot]

``r`` and ``rmem`` take two builds of ``tools/lifecycle-probes``
(``release-cells`` and ``memory-peak`` respectively), one linked against each
knotrel release; ``mreg`` takes two ``knotrel-server`` binaries.
``--pilot`` runs two pairs per cell (one config per server for ``mdesc``) to
check the pipeline; it is never used for decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_paths import confined  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.6.0-qualification" / "MATRIX.json"


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host_state() -> Dict[str, Any]:
    batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    therm = subprocess.run(["pmset", "-g", "therm"], capture_output=True, text=True).stdout
    load = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True).stdout.strip()
    return {"utc": utc(), "batt": batt.strip(), "therm": therm.strip(), "loadavg": load}


def check_host(state: Dict[str, Any]) -> None:
    """Raises ``SystemExit`` unless the host is on AC power without thermal warnings."""
    first = state["batt"].splitlines()[0] if state["batt"] else ""
    if "AC Power" not in first:
        raise SystemExit(f"host check failed: not on AC power ({first!r})")
    therm = state["therm"]
    for marker in ("thermal warning level", "performance warning level", "CPU power status"):
        for line in therm.splitlines():
            if marker in line and "No " not in line:
                raise SystemExit(f"host check failed: {line.strip()!r}")


def check_no_builds() -> None:
    out = subprocess.run(["pgrep", "-l", "cargo|rustc"], capture_output=True, text=True).stdout.strip()
    if out:
        raise SystemExit(f"host check failed: build processes running: {out}")


class Recorder:
    """Writes one directory per child under ``out/raw`` and a JSON log."""

    def __init__(self, out: Path, meta: Dict[str, Any], enforce_host: bool) -> None:
        if out.exists():
            raise SystemExit(f"refusing to overwrite {out}")
        (out / "raw").mkdir(parents=True)
        self.out = out
        self.enforce_host = enforce_host
        self.log: Dict[str, Any] = {"meta": meta, "started": utc(), "children": []}
        self.counter = 0

    def run(self, label: str, argv: List[str]) -> str:
        state = host_state()
        if self.enforce_host:
            check_host(state)
        self.counter += 1
        name = f"{self.counter:05d}-{label}"
        start = time.time()
        proc = subprocess.run(argv, capture_output=True, text=True)
        elapsed = time.time() - start
        (self.out / "raw" / f"{name}.stdout").write_text(proc.stdout)
        (self.out / "raw" / f"{name}.stderr").write_text(proc.stderr)
        self.log["children"].append({"name": name, "argv": argv, "exit": proc.returncode,
                                     "seconds": round(elapsed, 3), "host": state})
        self.flush()
        if proc.returncode != 0:
            self.log["stopped"] = f"{name} exited {proc.returncode}"
            self.flush()
            raise SystemExit(f"child {name} failed with exit {proc.returncode}: {proc.stderr[-500:]}")
        return proc.stdout

    def flush(self) -> None:
        self.log["updated"] = utc()
        (self.out / "run-log.json").write_text(json.dumps(self.log, indent=1))


def last_json(stdout: str, kind: str) -> Dict[str, Any]:
    """The last JSON line of ``stdout`` whose ``kind`` equals ``kind``."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        value = json.loads(line)
        if value.get("kind") == kind:
            return value
    raise ValueError(f"no {kind!r} record in output")


def build_record(stdout: str) -> Dict[str, Any]:
    return last_json(stdout.splitlines()[0] + "\n", "build") if stdout else {}


def balanced_orders(count: int, seed: int) -> List[List[str]]:
    """``count`` pair orders, half reference-first, shuffled with ``seed``."""
    orders = [["ref", "cand"]] * (count // 2) + [["cand", "ref"]] * (count - count // 2)
    random.Random(seed).shuffle(orders)
    return orders


def paired_experiment(rec: Recorder, cells: List[Dict[str, Any]], arms: Dict[str, List[str]],
                      warmup: int, pairs: int, seed: int, run_cell) -> None:
    """Runs ``warmup + pairs`` alternating pairs per cell, cells in shuffled order."""
    rng = random.Random(seed)
    order = list(cells)
    rng.shuffle(order)
    for cell in order:
        orders = [["ref", "cand"], ["cand", "ref"]][:warmup] + balanced_orders(pairs, rng.randrange(1 << 30))
        for index, arm_order in enumerate(orders):
            phase = "warmup" if index < warmup else "analyzed"
            for arm in arm_order:
                run_cell(cell, arm, f"{cell['id']}-{phase}-{index:02d}-{arm}")


def cmd_r(args: argparse.Namespace, matrix: Dict[str, Any], rec: Recorder) -> None:
    spec = matrix["experiments"]["R"]
    arms = {"ref": args.ref, "cand": args.cand}
    pairs = 2 if args.pilot else spec["pairs"]
    warmup = 0 if args.pilot else spec["warmup_pairs"]
    check_no_builds()

    def run_cell(cell, arm, label):
        rec.run(label, [arms[arm]] + cell["args"])

    paired_experiment(rec, spec["cells"], arms, warmup, pairs, spec["order_seed"], run_cell)


def cmd_rmem(args: argparse.Namespace, matrix: Dict[str, Any], rec: Recorder) -> None:
    spec = matrix["experiments"]["Rmem"]
    check_no_builds()
    for cell in spec["cells"]:
        for arm, binary in (("ref", args.ref), ("cand", args.cand)):
            rec.run(f"{cell['id']}-{arm}", [binary] + cell["args"])


def write_configs(configs: List[Dict[str, Any]]) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for config in configs:
        handle.write(json.dumps(config) + "\n")
    handle.close()
    return handle.name


def probe_argv(probe: str, server: str, mode: str, lifecycle: bool, nodes: int, seed: int,
               configs_path: str) -> List[str]:
    return [probe, "--server-bin", server, "--mode", mode, "--lifecycle", str(lifecycle).lower(),
            "--nodes", str(nodes), "--seed", str(seed), "--configs", configs_path]


def cmd_mdesc(args: argparse.Namespace, matrix: Dict[str, Any], rec: Recorder) -> None:
    spec = matrix["experiments"]["M_desc"]
    check_no_builds()
    closed: Dict[str, float] = {}
    for server in spec["servers"]:
        configs = server["configs"][:1] if args.pilot else server["configs"]
        path = write_configs(configs)
        (rec.out / f"{server['id']}.configs.jsonl").write_text(Path(path).read_text())
        stdout = rec.run(server["id"], probe_argv(args.probe, args.server, server["mode"], server["lifecycle"],
                                                  server["nodes"], spec["seed"], path))
        for line in stdout.splitlines():
            if line.startswith("{") and '"kind":"config"' in line:
                record = json.loads(line)
                closed[f"{server['id']}/{record['config']['id']}"] = record["requests_per_s"]
    if args.pilot:
        return
    for lifecycle in ("off", "on"):
        key = f"M-standalone-{lifecycle}-100k/read95-b8-c16"
        base = closed[key]
        configs = [{"id": f"open-read95-b8-c16-f{f}", "mix": "read95", "batch": 8, "clients": 16,
                    "warmup_ms": 1000, "measure_ms": 3000, "open_rate": round(base * f, 1), "background": "none"}
                   for f in spec["open_loop"]["fractions"]]
        path = write_configs(configs)
        (rec.out / f"M-open-{lifecycle}-100k.configs.jsonl").write_text(Path(path).read_text())
        rec.run(f"M-open-{lifecycle}-100k", probe_argv(args.probe, args.server, "standalone", lifecycle == "on",
                                                       100000, spec["seed"], path))


def cmd_mreg(args: argparse.Namespace, matrix: Dict[str, Any], rec: Recorder) -> None:
    spec = matrix["experiments"]["M_reg"]
    servers = {"ref": args.ref, "cand": args.cand}
    pairs = 2 if args.pilot else spec["pairs"]
    warmup = 0 if args.pilot else spec["warmup_pairs"]
    check_no_builds()

    def run_cell(cell, arm, label):
        path = write_configs([cell["config"]])
        rec.run(label, probe_argv(args.probe, servers[arm], cell["mode"], cell["lifecycle"], cell["nodes"],
                                  spec["seed"], path))

    paired_experiment(rec, spec["cells"], servers, warmup, pairs, spec["order_seed"], run_cell)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("experiment", choices=["r", "rmem", "mdesc", "mreg"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--cand")
    parser.add_argument("--probe")
    parser.add_argument("--server")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text())
    freeze = MATRIX.parent / "FREEZE.json"
    if not (args.dry_run or args.pilot) and not freeze.exists():
        raise SystemExit("MATRIX.json is not frozen (FREEZE.json missing); only --dry-run or --pilot may run")
    args.out = confined(args.out, "--out")
    binaries = {k: confined(getattr(args, k), f"--{k}")
                for k in ("ref", "cand", "probe", "server") if getattr(args, k)}
    for k, path in binaries.items():
        if not path.is_file() or not os.access(path, os.X_OK):
            raise SystemExit(f"--{k}: {path} is not an executable file")
    meta = {"experiment": args.experiment, "pilot": args.pilot, "matrix_sha256": sha256(MATRIX),
            "freeze_sha256": sha256(freeze) if freeze.exists() else None,
            "binaries": {k: {"path": str(v), "sha256": sha256(v)} for k, v in binaries.items()}}
    if args.dry_run:
        print(json.dumps(meta, indent=1))
        return 0
    rec = Recorder(args.out, meta, enforce_host=not args.pilot)
    {"r": cmd_r, "rmem": cmd_rmem, "mdesc": cmd_mdesc, "mreg": cmd_mreg}[args.experiment](args, matrix, rec)
    rec.log["finished"] = utc()
    rec.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
