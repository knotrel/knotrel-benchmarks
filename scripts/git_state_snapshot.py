#!/usr/bin/env python3
"""Read-only snapshot of Git fetch state under a directory tree.

For every Git clone (symlinks not followed) records the mtime of ``FETCH_HEAD``
and the number of lines in each remote-tracking reflog. Comparing two snapshots
shows whether any fetch updated a clone in between. It never writes to a
repository and never runs Git.

    git_state_snapshot.py snapshot ROOT OUT.json
    git_state_snapshot.py compare BEFORE.json AFTER.json OUT.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_paths import confined, confined_directory  # noqa: E402


def snapshot(root: str) -> Dict[str, Dict[str, float]]:
    state: Dict[str, Dict[str, float]] = {}
    for directory, subdirs, _ in os.walk(root):
        if ".git" in subdirs:
            git = os.path.join(directory, ".git")
            subdirs.remove(".git")
            entry: Dict[str, float] = {}
            fetch_head = os.path.join(git, "FETCH_HEAD")
            if os.path.exists(fetch_head):
                entry["FETCH_HEAD_mtime"] = os.stat(fetch_head).st_mtime
            logs = os.path.join(git, "logs", "refs", "remotes")
            for log_dir, _, files in os.walk(logs):
                for name in files:
                    path = os.path.join(log_dir, name)
                    with open(path, "rb") as handle:
                        entry["reflog:" + os.path.relpath(path, logs)] = float(handle.read().count(b"\n"))
            state[directory] = entry
    return state


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "snapshot":
        root = confined_directory(sys.argv[2], "ROOT")
        out = confined(sys.argv[3], "OUT")
        with open(out, "w") as handle:
            json.dump(snapshot(str(root)), handle, indent=1, sort_keys=True)
        return 0
    if len(sys.argv) == 5 and sys.argv[1] == "compare":
        before_path = confined(sys.argv[2], "BEFORE")
        after_path = confined(sys.argv[3], "AFTER")
        out = confined(sys.argv[4], "OUT")
        with open(before_path) as handle:
            before = json.load(handle)
        with open(after_path) as handle:
            after = json.load(handle)
        changed = sorted(f"{clone}:{key}" for clone in set(before) | set(after)
                         for key in set(before.get(clone, {})) | set(after.get(clone, {}))
                         if before.get(clone, {}).get(key) != after.get(clone, {}).get(key))
        with open(out, "w") as handle:
            json.dump({"clones": len(after), "changed": changed}, handle, indent=1)
        print(f"{len(changed)} changes across {len(after)} clones")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
