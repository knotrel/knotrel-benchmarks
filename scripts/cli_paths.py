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
    roots = allowed_roots()
    # A lexical check first, so that a path outside every root never reaches the
    # filesystem; then the symbolic links are resolved and the result checked again.
    lexical = os.path.normpath(os.path.abspath(text))
    lexical_roots = roots + [os.path.normpath(os.path.abspath(r)) for r in _declared_roots()]
    # macOS: /var, /tmp and /etc are symbolic links into /private.
    lexical_roots += [r[len("/private"):] for r in lexical_roots if r.startswith("/private/")]
    if not any(_inside(lexical, root) for root in lexical_roots):
        raise SystemExit(f"{what}: {text} lies outside the allowed roots {roots}")
    resolved = Path(os.path.realpath(lexical))
    if not any(_inside(str(resolved), root) for root in roots):
        raise SystemExit(f"{what}: {text} resolves outside the allowed roots {roots}")
    return resolved


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _declared_roots() -> List[str]:
    """The roots as written, before symbolic links are resolved (``/tmp`` and
    ``/private/tmp`` on macOS name the same directory)."""
    declared = [str(REPO.parent / sibling) for sibling in ("knotrel", "evidence")]
    declared += [str(Path(__file__).resolve().parent.parent), str(Path(__file__).resolve().parent.parent.parent)]
    declared += [e for e in os.environ.get("LIFECYCLE_QUALIFICATION_ROOTS", "").split(os.pathsep) if e]
    return declared


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
