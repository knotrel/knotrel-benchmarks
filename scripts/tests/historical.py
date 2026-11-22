"""Frozen campaign directories that left main but stay at their release tags.

The working tree keeps only the current release's evidence under ``results/``; earlier
campaigns are read from the tag that closed them. Their tooling still binds those
directories by path (frozen ``MATRIX`` defaults, shell scripts, matrix diffs), so the tests
that pin it call ``ensure()`` first: each missing directory is extracted from its tag into
``results/`` for the life of the test process and removed at exit. The directories are
git-ignored, so a test run never adds them to the index.

Without the tags (a shallow clone), ``ensure()`` raises ``unittest.SkipTest``; run
``git fetch --tags`` to include these tests.
"""

import atexit
import io
import shutil
import subprocess
import tarfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# Directory under results/ -> the release tag whose tree holds its final, frozen state.
TAGS = {
    "v0.6.0-qualification": "v0.6.0",
    "v0.7.0-qualification": "v0.7.0",
    "v0.7.0-qualification-3": "v0.7.0",
    "v0.7.0-requalification": "v0.7.0",
}

_extracted = []


def _cleanup():
    for path in _extracted:
        shutil.rmtree(path, ignore_errors=True)


atexit.register(_cleanup)


def ensure(*names):
    """Make ``results/<name>`` available for each name (all known ones by default)."""
    for name in names or tuple(TAGS):
        target = REPO / "results" / name
        if target.exists():
            continue
        tag = TAGS[name]
        try:
            archive = subprocess.run(
                ["git", "-C", str(REPO), "archive", "--format=tar", tag, f"results/{name}"],
                capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise unittest.SkipTest(f"results/{name} needs tag {tag} (git fetch --tags): {exc}")
        _extracted.append(target)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(REPO, filter="data")
