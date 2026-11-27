"""Validation of command-line paths for the lifecycle qualification scripts.

Every path taken from the command line is resolved with ``os.path.realpath``
and must lie inside an allowed root: this repository, its parent directory, and
the sibling checkouts the harness documents (``../knotrel`` and
``../evidence``), resolved through their symbolic links. Additional roots can
be granted explicitly with ``LIFECYCLE_QUALIFICATION_ROOTS`` (``os.pathsep``
separated), which the unit tests use for their temporary directories. Values
that start with ``-`` are refused so that no path can be read as an option of
a program it is passed to. Executables must be existing regular files with
execute permission.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

REPO = Path(os.path.realpath(Path(__file__).resolve().parent.parent))


def allowed_roots() -> List[str]:
    """Resolved roots under which command-line paths are accepted."""
    roots = {str(REPO), os.path.realpath(REPO.parent)}
    for sibling in ("knotrel", "evidence"):
        candidate = REPO.parent / sibling
        if candidate.exists():
            roots.add(os.path.realpath(candidate))
    for extra in os.environ.get("LIFECYCLE_QUALIFICATION_ROOTS", "").split(os.pathsep):
        if extra:
            roots.add(os.path.realpath(extra))
    return sorted(roots)


def confined(value: os.PathLike | str, what: str) -> Path:
    """Resolve ``value`` and require it to lie inside an allowed root."""
    text = os.fspath(value)
    if not text or text.startswith("-"):
        raise SystemExit(f"{what}: invalid path {text!r}")
    resolved = Path(text).resolve()
    for root in allowed_roots():
        if resolved == Path(root) or resolved.is_relative_to(root):
            return resolved
    raise SystemExit(f"{what}: {text} resolves outside the allowed roots {allowed_roots()}")


def contained_file(directory: Path, name: str, what: str) -> Path:
    """``directory / name`` resolved, refused unless it lies directly inside ``directory``.

    Used for file names derived from data (cell identifiers in a plan), so that
    a name containing a separator, ``..`` or a symbolic link cannot escape the
    run directory.
    """
    root = Path(directory).resolve()
    resolved = (root / name).resolve()
    if resolved.parent != root:
        raise SystemExit(f"{what}: {name!r} resolves outside {root}")
    return resolved


def confined_executable(value: os.PathLike | str, what: str) -> Path:
    """A confined, existing regular file with execute permission."""
    path = confined(value, what)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SystemExit(f"{what}: {path} is not an executable file")
    return path


def confined_directory(value: os.PathLike | str, what: str) -> Path:
    """A confined, existing directory."""
    path = confined(value, what)
    if not path.is_dir():
        raise SystemExit(f"{what}: {path} is not a directory")
    return path
