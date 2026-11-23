#!/usr/bin/env python3
"""Core rule of the v1.0.0 qualification (plan section 4.3), decided at the freeze from builds.

Compares the ``__TEXT,__text`` section of release builds made against the candidate and
against the reference: the core probes (``core-lifecycle``, the B/C ``core`` binary, and its
``count-alloc`` build, the ``core-count`` binary) and the A core harness. Each section is read
with ``otool -s __TEXT __text`` (the two header lines, which name the file, are dropped) and
hashed. Never measures anything.

- every pair identical: outcome ``identical`` (the core's executed code did not change; the
  perimeter is as approved, with ``--only B4,C``);
- any pair different: outcome ``different`` (B1-B3, B5 and T5 join the perimeter with the
  full B/C collector).

The outcome and this file's SHA-256 go into ``FREEZE.json`` (``core_rule``); the runner refuses
to start without them.

    core_rule_v100q.py CAMP OUT.json
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple

#: (name, candidate build, reference build), relative to CAMP/targets.
PAIRS: Tuple[Tuple[str, str, str], ...] = (
    ("core-lifecycle (B/C core)", "cand-probes/release/core-lifecycle", "t5base-probes/release/core-lifecycle"),
    ("core-lifecycle count-alloc (B/C core-count)", "cand-probes-count/release/core-lifecycle",
     "ref-probes-count/release/core-lifecycle"),
    ("A core harness", "A-C-harness/release/knotrel-benchmarks", "A-B-harness/release/knotrel-benchmarks"),
)


def text_section_sha256(path: Path) -> str:
    """SHA-256 of the ``otool -s __TEXT __text`` dump without its two header lines."""
    dump = subprocess.run(["otool", "-s", "__TEXT", "__text", str(path)], capture_output=True, text=True, check=True).stdout
    lines = dump.splitlines()
    if len(lines) < 3 or "(__TEXT,__text)" not in lines[1]:
        raise SystemExit(f"{path}: no __TEXT,__text section in the otool output")
    return hashlib.sha256("\n".join(lines[2:]).encode()).hexdigest()


def compare(targets: Path, digest: Callable[[Path], str] = text_section_sha256) -> Dict[str, object]:
    rows: List[Dict[str, object]] = []
    for name, cand, ref in PAIRS:
        c, r = digest(targets / cand), digest(targets / ref)
        rows.append({"binary": name, "candidate": cand, "reference": ref, "candidate_text_sha256": c,
                     "reference_text_sha256": r, "identical": c == r})
    outcome = "identical" if all(row["identical"] for row in rows) else "different"
    return {"rule": "plan section 4.3: identical __TEXT,__text apart from the knotrel-core version, decided at the freeze",
            "outcome": outcome, "pairs": rows,
            "consequence": ("perimeter as approved (--only B4,C)" if outcome == "identical" else
                            "B1-B3, B5 and T5 join the perimeter (full B/C collector, T5)")}


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(argv[2])
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    result = compare(Path(argv[1]) / "targets")
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"core rule: {result['outcome']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
