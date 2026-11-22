#!/usr/bin/env python3
"""Check T5 of the v0.9.0 qualification: ``analyze_v070q3_t5.py`` unchanged, except that the
two arms are built from two knotrel-benchmarks commits with the same probe source.

Arm B (v0.7.0) links knotrel 0.7.0, so its probes are built at a commit whose probe lockfile
resolves 0.7.0 (``--expect-base-probes-rev``); arm C (the candidate) at the freeze commit
(``--expect-probes-rev``). Every other check (clean builds, the frozen plan, equal workloads and
compaction cycles, 30 intervals, the estimators and the 25 % tolerance) is the frozen one. The
analysis additionally requires that the two commits differ in ``tools/lifecycle-probes`` only by
the two knotrel version lines of ``Cargo.lock`` (``--benchmarks`` checkout).

    analyze_v090q_t5.py T5_DIR --expect-base-rev SHA --expect-cand-rev SHA \\
        --expect-base-probes-rev SHA --expect-probes-rev SHA --benchmarks DIR [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v070q3_t5 as frozen  # noqa: E402


def probe_source_equal(benchmarks: Path, base: str, cand: str) -> None:
    diff = subprocess.run(["git", "-C", str(benchmarks), "diff", "--unified=0", base, cand, "--",
                           "tools/lifecycle-probes"], check=True, capture_output=True, text=True).stdout
    files = [line[6:] for line in diff.splitlines() if line.startswith("+++ b/")]
    if files not in ([], ["tools/lifecycle-probes/Cargo.lock"]):
        raise frozen.Invalid(f"probe sources differ between {base} and {cand}: {files}")
    changed = [line for line in diff.splitlines()
               if line[:1] in "+-" and not line.startswith(("+++", "---"))]
    if any(not line[1:].startswith('version = "0.') for line in changed) or len(changed) > 4:
        raise frozen.Invalid(f"probe lockfiles differ beyond the knotrel versions: {changed}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expect-base-rev", required=True)
    parser.add_argument("--expect-cand-rev", required=True)
    parser.add_argument("--expect-base-probes-rev", required=True)
    parser.add_argument("--expect-probes-rev", required=True)
    parser.add_argument("--benchmarks", type=Path, required=True)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    original = frozen.run_summary

    def per_arm(run_id, topology, records, rev, probes_rev):
        chosen = args.expect_base_probes_rev if rev == args.expect_base_rev else probes_rev
        return original(run_id, topology, records, rev, chosen)

    frozen.run_summary = per_arm
    try:
        probe_source_equal(args.benchmarks, args.expect_base_probes_rev, args.expect_probes_rev)
        out = frozen.analyze(args.directory, args.expect_base_rev, args.expect_cand_rev, args.expect_probes_rev)
    except (frozen.Invalid, frozen._bc.AnalysisError, OSError, KeyError, ValueError, IndexError, TypeError,
            ZeroDivisionError, subprocess.CalledProcessError) as error:
        # Same marker as the frozen analyzer: the report turns it into six INVALID deciding rows.
        print(f"T5 INVALID: {error}", file=sys.stderr)
        if args.json:
            args.json.write_text(json.dumps({"check": "T5", "invalid": f"{type(error).__name__}: {error}"}, indent=1))
        return 1
    finally:
        frozen.run_summary = original
    out["base_probes_rev"] = args.expect_base_probes_rev
    if args.json:
        args.json.write_text(json.dumps(out, indent=1))
    for r in out["results"]:
        print(f"{r['id']}: {r['status']} median {r['median_change_pct']:+.1f}% interval "
              f"[{r['interval_pct'][0]:+.1f}%, {r['interval_pct'][1]:+.1f}%] | B median "
              f"{r['absolute_ms']['B']['median']:.2f} ms, C median {r['absolute_ms']['C']['median']:.2f} ms")
    return 0

if __name__ == "__main__":
    sys.exit(main())
