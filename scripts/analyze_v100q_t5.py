#!/usr/bin/env python3
"""Check T5 of the v1.0.0 qualification, run only if the core rule triggered (plan section 4.3).

``analyze_v090q_t5.py`` unchanged (``analyze_v070q3_t5.py`` with arm B built from a separate,
clean probe revision), with one difference in its probe-source check: arm B links knotrel
0.9.0 and arm C knotrel 1.0.0-rc.1, so the two knotrel version lines of the probe lockfile change
major version, which the v0.9.0 check (``version = "0.`` only) refuses. Here the two commits may
differ in ``tools/lifecycle-probes`` only in ``Cargo.lock``, in at most four changed lines, each
a ``version = "<semver>"`` line (prerelease allowed) of the ``knotrel-core`` or ``knotrel-server`` package. Every other
check is the frozen one. The installed check is restored when the command ends.

    analyze_v100q_t5.py T5_DIR --expect-base-rev SHA --expect-cand-rev SHA \\
        --expect-base-probes-rev SHA --expect-probes-rev SHA --benchmarks DIR [--json OUT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v090q_t5 as v090  # noqa: E402

# SemVer 2.0.0 version, prerelease identifiers allowed (the candidate is 1.0.0-rc.1); no build metadata.
VERSION_LINE = re.compile(r'^[+-]version = "\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"$')
FROZEN_CHECK = v090.probe_source_equal


def probe_source_equal(benchmarks: Path, base: str, cand: str) -> None:
    """The two probe trees are the same source; only the knotrel version lines of the lockfile differ."""
    benchmarks, base, cand = v090.confined(benchmarks, "--benchmarks"), v090.revision(base), v090.revision(cand)
    diff = subprocess.run(["git", "-C", str(benchmarks), "diff", "--unified=1", base, cand, "--",
                           "tools/lifecycle-probes"], check=True, capture_output=True, text=True).stdout
    files = [line[6:] for line in diff.splitlines() if line.startswith("+++ b/")]
    if files not in ([], ["tools/lifecycle-probes/Cargo.lock"]):
        raise v090.frozen.Invalid(f"probe sources differ between {base} and {cand}: {files}")
    lines = diff.splitlines()
    changed = [(i, line) for i, line in enumerate(lines) if line[:1] in "+-" and not line.startswith(("+++", "---"))]
    for i, line in changed:
        context = lines[i - 1] if i else ""
        while context[:1] in "+-" and i > 1:  # the package name line is the context before the pair
            i -= 1
            context = lines[i - 1]
        if not VERSION_LINE.match(line) or context.strip() not in ('name = "knotrel-core"', 'name = "knotrel-server"'):
            raise v090.frozen.Invalid(f"probe lockfiles differ beyond the knotrel versions: {line!r} after {context!r}")
    if len(changed) > 4:
        raise v090.frozen.Invalid(f"probe lockfiles differ beyond the knotrel versions: {[l for _, l in changed]}")


def main() -> int:
    v090.probe_source_equal = probe_source_equal
    try:
        return v090.main()
    finally:
        v090.probe_source_equal = FROZEN_CHECK


if __name__ == "__main__":
    sys.exit(main())
