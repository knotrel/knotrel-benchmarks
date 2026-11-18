#!/usr/bin/env python3
"""Allow-list host-activity monitor for the v0.7.0 re-qualification.

The first v0.7.0 campaign matched a block pattern (Git, Cargo, two IDEs) and
recorded only the five busiest processes. Interactive use of the host went
undetected (``results/v0.7.0-qualification/conformance/``). This monitor
classifies **every** process by an allow-list, detects foreground apps and
detects user input directly.

Process classes, evaluated in this order (``classify_one``; PROTOCOL §3.2):

1. ``campaign``: the chain process and its descendants (PID ancestry).
2. ``forbidden``: a descendant of the controlling Claude Code CLI that is not
   in the chain and is not one of the chain's ancestors recorded in the
   policy (a tool call), whatever its executable, zombies included.
3. Any other zombie takes the class of its parent.
4. ``system``: PID 0 (the kernel).
5. ``forbidden``: an executable whose base name is on the deny-list (user
   actions run by system binaries: disk-image mounts, file dialogs, remote
   logins, Git, installers and so on), wherever it lives. For a process
   whose path is unavailable, the base name of ``comm`` is used.
6. ``forbidden``: a registered foreground app (``lsappinfo``) other than
   Finder and the Claude desktop app, wherever it lives. This covers apps in
   system locations, such as Safari in its cryptex, DiskImageMounter and
   Installer.
7. ``baseline``: the controlling CLI and the chain's ancestors below it
   (``Policy.controller_children``), and the Claude desktop app (executable
   under ``/Applications/Claude.app/``).
8. ``forbidden``: a live process whose executable cannot be resolved.
9. ``system``: an executable in an Apple-controlled location
   (``SYSTEM_PREFIXES``) or a system app extension
   (``/System/Applications/*.app/Contents/PlugIns/*.appex/``).
10. ``baseline``: an executable listed in the frozen host baseline.
11. ``forbidden``: everything else.

User input: the HID idle time (``ioreg -c IOHIDSystem`` ``HIDIdleTime``),
read once per second and timestamped with the monotonic clock at the read.
Without input it grows with elapsed time. Input more than
``HID_TOLERANCE_S`` after the previous input makes a reading smaller than the
previous reading plus the elapsed time minus the tolerance (``hid_reset``).

Output of the ``monitor`` sub-command, one JSON object per line:
- ``start``: the policy and the settings;
- ``s`` (every ``--interval`` s, the heartbeat): wall time ``t``, sequence
  ``seq``, and the forbidden processes ``v`` of that sample;
- ``h`` (every second): HID idle seconds and whether a reset was detected;
- ``top`` (every second): the five busiest non-campaign processes (disclosure);
- ``stop``, with a reason: a signal, or ``chain_gone`` when the chain process
  has disappeared.

The status file (``--status``) is replaced atomically after every sample.
The per-child gate (``conformance_gate.py``) reads it.

Other sub-commands:
- ``check``: classify now; exit 1 if anything is forbidden.
- ``inventory``: every non-campaign process and its class.
- ``policy``: build and validate the policy for a chain.
- ``git-snapshot``: read-only state of every Git clone under a root.

Amendment 2 (PROTOCOL §9), controller kind ``terminal`` (``Policy.controller_kind``):
the chain is launched from Terminal.app with no Claude process running. The
controller is then the Terminal.app process. Changes to the rules above:
- rule 2 applies to Terminal's descendants (another window or tab is forbidden);
- the controller and the chain's ancestors below it, which must be exactly
  ``/usr/bin/login`` and ``/bin/zsh`` (``TERMINAL_LINEAGE``), are ``baseline`` right after rule 2, before the
  deny-list (``login`` is deny-listed), only while each PID still runs the
  executable the policy recorded for it (``Policy.controller_paths``); a
  reused PID falls through to the other rules;
- rule 6 allows Finder and Terminal.app as foreground apps, not the Claude
  desktop app;
- rule 7 no longer makes the Claude desktop app ``baseline``. Any Claude
  executable (``is_claude``: the desktop app, the Claude Code CLI under the
  app or a native install ``~/.local/share/claude/versions/``, or a process
  named ``claude``) is ``forbidden``, wherever it lives.
The policy refuses the launch if Terminal.app is not the chain's topmost
ancestor below launchd, if the ancestors in between are not exactly
``TERMINAL_LINEAGE``, if the chain has no ``/usr/bin/caffeinate`` child
(``caffeinate UTILITY`` gives its PID to the utility and asserts from a child
it forks; PROTOCOL §9.11), if Terminal has any other live descendant, if another
Terminal process exists, or if any Claude process is running (``is_claude``,
or a command line naming claude-code, for example a node-based CLI).

Amendment 3 (PROTOCOL §10), ``Policy.background_allowed`` (MATRIX
``conformance.background_allowed``, terminal kind only): rules 8 and 11 give
``background`` instead of ``forbidden``. A live process whose executable cannot
be resolved, or that is in no other class, is allowed and its CPU time is
recorded. Rules 1-7 are unchanged: new controller descendants, deny-listed
executables, foreground apps other than Finder and Terminal, and any Claude
executable stay ``forbidden``.

Limits (PROTOCOL §3.6): a process that starts and exits between two samples
can be missed. With controller kind ``claude-cli``, tool calls that start no
process are covered only by the controller transcript check in the chain;
with ``terminal`` (amendment 2), Claude is quit and ``~/.claude/projects`` is
compared instead (PROTOCOL §9.3).

    conformance_monitor.py monitor --policy POLICY.json --out LOG.jsonl --status STATUS.json [--interval 0.2]
    conformance_monitor.py check|inventory --policy POLICY.json
    conformance_monitor.py policy --chain PID --controller PID --matrix MATRIX.json --out POLICY.json
    conformance_monitor.py policy --chain PID --controller-kind terminal --matrix MATRIX.json --out POLICY.json
    conformance_monitor.py tree-state DIR
    conformance_monitor.py git-snapshot ROOT
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

SYSTEM_PREFIXES: Tuple[str, ...] = (
    "/System/Library/",
    "/System/Cryptexes/",
    "/System/iOSSupport/System/Library/",
    "/System/Volumes/Preboot/Cryptexes/",
    "/usr/libexec/",
    "/usr/sbin/",
    "/sbin/",
    "/usr/bin/",
    "/bin/",
    "/Library/Apple/",
)
SYSTEM_APPEX = re.compile(r"^/System/Applications/[^/]+\.app/Contents/PlugIns/[^/]+\.appex/")
CONTROLLER_APP = "/Applications/Claude.app/"
CONTROLLER_CLI = re.compile(r"/claude-code/[^/]+/.*/claude$")
ALLOWED_FOREGROUND: Tuple[str, ...] = ("/System/Library/CoreServices/Finder.app/", CONTROLLER_APP)
TERMINAL_APP = "/System/Applications/Utilities/Terminal.app/"
TERMINAL_EXE = TERMINAL_APP + "Contents/MacOS/Terminal"
ALLOWED_FOREGROUND_TERMINAL: Tuple[str, ...] = ("/System/Library/CoreServices/Finder.app/", TERMINAL_APP)
KINDS = ("claude-cli", "terminal")
# Amendment 2: the only accepted ancestors between Terminal.app and the chain, from the top.
TERMINAL_LINEAGE: Tuple[str, ...] = ("/usr/bin/login", "/bin/zsh")
# ``/usr/bin/caffeinate -dimsu /bin/sh CHAIN`` execs the chain in caffeinate's PID and forks a
# caffeinate child that holds the assertions (observed on this host, PROTOCOL §9.11).
CAFFEINATE = "/usr/bin/caffeinate"
# Amendment 3: extra names forbidden in terminal mode (non-campaign interpreters), and the
# command-line scan for a Claude CLI not recognised by path, cached for one second.
TERMINAL_EXTRA_DENY: Set[str] = {"Python", "node"}
COMM_MAX = 16  # ps shows a starting or exiting process as "(name)", cut to 16 characters
_CLAUDE_PIDS: Dict[str, object] = {"t": 0.0, "pids": set()}
CLAUDE_NATIVE = re.compile(r"/\.local/share/claude/versions/[^/]+$")
CLAUDE_CMDLINE = re.compile(r"claude-code|@anthropic-ai/claude|/\.local/share/claude/")
DENY_BASENAMES: Set[str] = {
    "diskimages-helper", "hdiejectd", "hdiutil",
    "com.apple.appkit.xpc.openAndSavePanelService",
    "ScreenSaverEngine", "screencapture", "installer", "softwareupdate",
    "git", "xcodebuild", "xcrun", "osascript", "open", "ssh", "scp", "curl",
    "python3", "cargo", "rustc", "rustup",
    "sshd", "sshd-session", "screensharingd", "ScreensharingAgent", "ARDAgent", "login", "atrun",
}
DENY_BASENAME_PREFIXES: Tuple[str, ...] = ("git-",)
HID_TOLERANCE_S = 1.0
SNAPSHOT_SKIP: Tuple[str, ...] = (".git", "target", "targets", "node_modules", "raw", "raw-main", "raw-extension")
C_ENV = {**os.environ, "LC_ALL": "C"}

_LIBPROC = ctypes.CDLL("/usr/lib/libproc.dylib") if sys.platform == "darwin" else None
_PATH_CACHE: Dict[Tuple[int, str], Optional[str]] = {}


def utc(t: Optional[float] = None) -> str:
    moment = datetime.datetime.fromtimestamp(time.time() if t is None else t, datetime.timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def executable_path(pid: int, comm: str) -> Optional[str]:
    """Executable path of ``pid`` (``proc_pidpath``), cached by (pid, comm)."""
    key = (pid, comm)
    if key in _PATH_CACHE:
        return _PATH_CACHE[key]
    path: Optional[str] = None
    if _LIBPROC is not None:
        buffer = ctypes.create_string_buffer(4096)
        if _LIBPROC.proc_pidpath(pid, buffer, 4096) > 0:
            path = buffer.value.decode("utf-8", "replace")
    elif os.path.exists(f"/proc/{pid}/exe"):
        try:
            path = os.readlink(f"/proc/{pid}/exe")
        except OSError:
            path = None
    if path is None and comm.startswith("/"):
        path = comm
    if path is not None:
        _PATH_CACHE[key] = path
    return path


@dataclass
class Proc:
    """One row of the process table."""

    pid: int
    ppid: int
    pcpu: float
    comm: str
    path: Optional[str]
    cputime_s: float = 0.0
    stat: str = ""

    @property
    def zombie(self) -> bool:
        return self.stat.startswith("Z")


def parse_cputime(text: str) -> float:
    """``ps`` TIME (``[[dd-]hh:]mm:ss.cc``) in seconds."""
    days = 0
    if "-" in text:
        day_text, text = text.split("-", 1)
        days = int(day_text)
    seconds = 0.0
    for part in text.split(":"):
        seconds = seconds * 60 + float(part)
    return days * 86400 + seconds


def snapshot(resolve: Callable[[int, str], Optional[str]] = executable_path) -> List[Proc]:
    """The whole process table: pid, ppid, %cpu, cumulative CPU time, state, executable."""
    out = subprocess.run(["ps", "-Ao", "pid=,ppid=,pcpu=,time=,stat=,comm="],
                         capture_output=True, text=True, env=C_ENV).stdout
    rows: List[Proc] = []
    for line in out.splitlines():
        parts = line.split(None, 5)
        if len(parts) != 6:
            continue
        pid, ppid = int(parts[0]), int(parts[1])
        rows.append(Proc(pid, ppid, float(parts[2]), parts[5], resolve(pid, parts[5]),
                         parse_cputime(parts[3]), parts[4]))
    return rows


class ForegroundUnavailable(RuntimeError):
    """``lsappinfo`` failed or returned no application; the foreground rule cannot be applied."""


def foreground_pids() -> Dict[int, str]:
    """PID -> executable of every registered foreground app (``lsappinfo``).

    Raises ``ForegroundUnavailable`` if ``lsappinfo`` fails or lists nothing
    (there is always at least the login window); the monitor counts that as a
    failure, which the gate treats like a violation.
    """
    proc = subprocess.run(["lsappinfo", "list"], capture_output=True, text=True, env=C_ENV)
    if proc.returncode != 0 or "pid = " not in proc.stdout:
        raise ForegroundUnavailable(f"lsappinfo exit {proc.returncode}: {proc.stderr.strip()[:200]}")
    found: Dict[int, str] = {}
    path = ""
    for line in proc.stdout.splitlines():
        match = re.search(r'executable path="([^"]*)"', line)
        if match:
            path = match.group(1)
            continue
        match = re.search(r'pid = (\d+) ', line)
        if match:
            if 'type="Foreground"' in line:
                found[int(match.group(1))] = path
            path = ""
    return found


@dataclass
class Policy:
    """What is allowed during measurement (written by the chain before the quiet period)."""

    chain_pid: int
    controller_pid: Optional[int] = None
    controller_children: Set[int] = field(default_factory=set)
    baseline_paths: Set[str] = field(default_factory=set)
    controller_kind: str = "claude-cli"
    controller_paths: Dict[int, str] = field(default_factory=dict)
    background_allowed: bool = False

    @staticmethod
    def load(path: Path) -> "Policy":
        data = json.loads(path.read_text())
        kind = data.get("controller_kind", "claude-cli")
        if kind not in KINDS:
            raise ValueError(f"unknown controller_kind {kind!r}")
        paths = {int(k): v for k, v in data.get("controller_paths", {}).items()}
        background = bool(data.get("background_allowed", False))
        if background and kind != "terminal":
            raise ValueError("background_allowed needs controller_kind terminal")
        return Policy(int(data["chain_pid"]), data.get("controller_pid"),
                      set(data.get("controller_children", [])), set(data.get("baseline_paths", [])), kind, paths, background)

    def to_json(self) -> Dict[str, object]:
        return {"chain_pid": self.chain_pid, "controller_pid": self.controller_pid,
                "controller_children": sorted(self.controller_children),
                "baseline_paths": sorted(self.baseline_paths), "controller_kind": self.controller_kind,
                "controller_paths": {str(k): v for k, v in sorted(self.controller_paths.items())},
                "background_allowed": self.background_allowed}


class PolicyError(Exception):
    """The chain cannot be launched with this controller."""


def descendants(procs: Iterable[Proc], root: Optional[int]) -> Set[int]:
    """PIDs of ``root`` and every process descending from it."""
    if root is None:
        return set()
    children: Dict[int, List[int]] = {}
    for p in procs:
        children.setdefault(p.ppid, []).append(p.pid)
    found: Set[int] = set()
    stack = [root]
    while stack:
        pid = stack.pop()
        if pid in found:
            continue
        found.add(pid)
        stack.extend(children.get(pid, []))
    return found


def ancestors(procs: Iterable[Proc], pid: int) -> List[int]:
    """``pid`` and its ancestors up to (excluding) PID 1."""
    parent = {p.pid: p.ppid for p in procs}
    chain: List[int] = []
    while pid in parent and pid > 1 and pid not in chain:
        chain.append(pid)
        pid = parent[pid]
    return chain


def build_policy(procs: List[Proc], chain_pid: int, controller_pid: int, baseline_paths: Iterable[str]) -> Policy:
    """Validated policy (PROTOCOL §3.2).

    The controller must be a Claude Code CLI and an ancestor of the chain. Its
    only allowed descendants are the chain's ancestors below it (for example
    the shell and ``caffeinate``). Any other live descendant of the
    controller refuses the launch.
    """
    by_pid = {p.pid: p for p in procs}
    lineage = ancestors(procs, chain_pid)
    if controller_pid not in by_pid:
        raise PolicyError(f"controller PID {controller_pid} is not running")
    if controller_pid not in lineage[1:]:
        raise PolicyError(f"controller PID {controller_pid} is not an ancestor of the chain {chain_pid}")
    path = by_pid[controller_pid].path or ""
    if not CONTROLLER_CLI.search(path):
        raise PolicyError(f"controller PID {controller_pid} is not a Claude Code CLI: {path!r}")
    between = set(lineage[1:lineage.index(controller_pid)])
    others = descendants(procs, controller_pid) - descendants(procs, chain_pid) - between - {controller_pid}
    others = {pid for pid in others if not by_pid[pid].zombie}
    if others:
        listing = [(pid, by_pid[pid].path or by_pid[pid].comm) for pid in sorted(others)]
        raise PolicyError(f"the controller has other live descendants: {listing}")
    return Policy(chain_pid, controller_pid, between, set(baseline_paths))


def is_claude(proc: Proc) -> bool:
    """Any Claude executable: the desktop app, the Claude Code CLI, or a process named ``claude``."""
    path = proc.path or ""
    name = os.path.basename(path if path else proc.comm)
    return (path.startswith(CONTROLLER_APP) or bool(CONTROLLER_CLI.search(path)) or bool(CLAUDE_NATIVE.search(path))
            or name.lower() == "claude")


def claude_cmdlines() -> List[Tuple[int, str]]:
    """Processes whose command line names the Claude Code CLI (for example a node-based install)."""
    out = subprocess.run(["ps", "-Ao", "pid=,args="], capture_output=True, text=True, env=C_ENV).stdout
    found = []
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and CLAUDE_CMDLINE.search(parts[1]) and int(parts[0]) != os.getpid():
            found.append((int(parts[0]), parts[1][:160]))
    return found


def build_policy_terminal(procs: List[Proc], chain_pid: int, baseline_paths: Iterable[str],
                          cmdlines: Iterable[Tuple[int, str]] = ()) -> Policy:
    """Validated policy for a chain launched from Terminal.app with Claude quit (amendment 2).

    Terminal.app must be the chain's topmost ancestor below launchd, the
    ancestors in between must be exactly ``TERMINAL_LINEAGE``, the chain must
    have a live ``/usr/bin/caffeinate`` child, Terminal must
    have no other live descendant, no other Terminal process may exist, and no
    Claude process may be running (``is_claude`` or a ``cmdlines`` entry).
    """
    by_pid = {p.pid: p for p in procs}
    claude = sorted({(p.pid, p.path or p.comm) for p in procs if is_claude(p) and not p.zombie}
                    | {(pid, args) for pid, args in cmdlines if pid in by_pid and not by_pid[pid].zombie})
    if claude:
        raise PolicyError(f"Claude processes are running (quit Claude completely): {claude}")
    lineage = ancestors(procs, chain_pid)
    if len(lineage) < 2:
        raise PolicyError(f"chain {chain_pid} has no ancestors below launchd")
    top = by_pid[lineage[-1]]
    if top.path != TERMINAL_EXE or top.ppid != 1:
        raise PolicyError(f"the chain's topmost ancestor is not Terminal.app under launchd: {top.pid} {top.path!r}")
    terminals = sorted(p.pid for p in procs if p.path == TERMINAL_EXE and not p.zombie)
    if terminals != [top.pid]:
        raise PolicyError(f"more than one Terminal process: {terminals}")
    between = lineage[1:-1]
    found = tuple(by_pid[pid].path or "" for pid in reversed(between))
    if found != TERMINAL_LINEAGE:
        raise PolicyError(f"the chain's ancestors below Terminal must be exactly {list(TERMINAL_LINEAGE)}, found {list(found)}")
    if not any(p.ppid == chain_pid and p.path == CAFFEINATE and not p.zombie for p in procs):
        raise PolicyError(f"the chain {chain_pid} has no {CAFFEINATE} child (launch it as /usr/bin/caffeinate -dimsu /bin/sh ...)")
    others = descendants(procs, top.pid) - descendants(procs, chain_pid) - set(between) - {top.pid}
    others = {pid for pid in others if not by_pid[pid].zombie}
    if others:
        listing = [(pid, by_pid[pid].path or by_pid[pid].comm) for pid in sorted(others)]
        raise PolicyError(f"Terminal has other live descendants (close every other window and tab): {listing}")
    paths = {pid: by_pid[pid].path or "" for pid in [top.pid] + between}
    return Policy(chain_pid, top.pid, set(between), set(baseline_paths), "terminal", paths)


def _bare(name: str) -> str:
    """``ps`` comm without the parentheses of a starting or exiting process."""
    return name[1:-1] if len(name) >= 2 and name.startswith("(") and name.endswith(")") else name


def _denied_terminal(name: str) -> bool:
    """Amendment 3 deny test: parentheses stripped, a name cut to COMM_MAX matches by prefix."""
    bare = _bare(name)
    names = DENY_BASENAMES | TERMINAL_EXTRA_DENY
    if bare in names or bare.startswith(DENY_BASENAME_PREFIXES):
        return True
    return len(bare) >= COMM_MAX - 2 and any(n.startswith(bare) for n in names)


def claude_pids_cached(max_age_s: float = 1.0) -> Set[int]:
    """PIDs whose command line names the Claude Code CLI, refreshed at most once per second."""
    now = time.monotonic()
    if now - float(_CLAUDE_PIDS["t"]) >= max_age_s:  # type: ignore[arg-type]
        _CLAUDE_PIDS["pids"] = {pid for pid, _ in claude_cmdlines()}
        _CLAUDE_PIDS["t"] = now
    return _CLAUDE_PIDS["pids"]  # type: ignore[return-value]


def _denied(name: str) -> bool:
    return name in DENY_BASENAMES or name.startswith(DENY_BASENAME_PREFIXES)


def classify_one(proc: Proc, policy: Policy, campaign: Set[int], controller_tree: Set[int],
                 foreground: Dict[int, str], by_pid: Dict[int, Proc], depth: int = 0,
                 lineage: Optional[Set[int]] = None, claude_pids: Optional[Set[int]] = None) -> str:
    """Class of one process (module docstring, rules 1-11)."""
    if proc.pid in campaign:
        return "campaign"
    terminal = policy.controller_kind == "terminal"
    lineage = lineage or set()
    claude_pids = claude_pids or set()
    # Amendment 2: a recorded lineage PID counts as the controller's only while it runs the
    # recorded executable and is still an ancestor of the chain in this sample.
    is_lineage = (terminal and (proc.pid == policy.controller_pid or proc.pid in policy.controller_children)
                  and proc.path is not None and proc.path == policy.controller_paths.get(proc.pid)
                  and proc.pid in lineage)
    if (proc.pid in controller_tree and proc.pid != policy.controller_pid
            and (proc.pid not in policy.controller_children or (terminal and not is_lineage))):
        return "forbidden"
    if is_lineage:
        return "baseline"
    if proc.zombie and depth < 8:
        parent = by_pid.get(proc.ppid)
        if parent is None or parent.pid <= 1:
            return "system"
        return classify_one(parent, policy, campaign, controller_tree, foreground, by_pid, depth + 1, lineage, claude_pids)
    if proc.pid == 0:
        return "system"
    path = proc.path
    if _denied(os.path.basename(path if path else proc.comm)):
        return "forbidden"
    allowed_fg = ALLOWED_FOREGROUND_TERMINAL if terminal else ALLOWED_FOREGROUND
    if proc.pid in foreground and not (path or foreground[proc.pid]).startswith(allowed_fg):
        return "forbidden"
    if terminal and is_claude(proc):
        return "forbidden"
    if not terminal and (proc.pid == policy.controller_pid or proc.pid in policy.controller_children):
        return "baseline"
    background = terminal and policy.background_allowed
    if background:
        # Amendment 3: what stays forbidden must not slip into background through an unresolved
        # path, a "(name)" comm, an interpreter path, or a Claude CLI known only by its command line.
        name = _bare(os.path.basename(path)) if path else _bare(proc.comm)
        if (_denied_terminal(os.path.basename(path) if path else proc.comm) or name.lower().startswith("claude")
                or proc.pid in claude_pids):
            return "forbidden"
    if path is None:
        return "background" if background else "forbidden"
    if path.startswith(CONTROLLER_APP) and not terminal:
        return "baseline"
    if path.startswith(SYSTEM_PREFIXES) or SYSTEM_APPEX.match(path):
        return "system"
    if path in policy.baseline_paths:
        return "baseline"
    return "background" if background else "forbidden"


def classify(procs: List[Proc], policy: Policy, foreground: Optional[Dict[int, str]] = None,
             claude_pids: Optional[Set[int]] = None) -> List[Tuple[Proc, str]]:
    campaign = descendants(procs, policy.chain_pid)
    tree = descendants(procs, policy.controller_pid)
    by_pid = {p.pid: p for p in procs}
    fg = foreground or {}
    # Amendment 2: lineage baseline only for PIDs that are still the chain's ancestors in this sample.
    lineage = set(ancestors(procs, policy.chain_pid)) if policy.controller_kind == "terminal" else set()
    if claude_pids is None:
        claude_pids = claude_pids_cached() if (policy.controller_kind == "terminal" and policy.background_allowed) else set()
    return [(p, classify_one(p, policy, campaign, tree, fg, by_pid, 0, lineage, claude_pids)) for p in procs]


def forbidden(procs: List[Proc], policy: Policy, alive: Callable[[int], bool] = lambda pid: True,
              foreground: Optional[Dict[int, str]] = None) -> List[Dict[str, object]]:
    """Forbidden processes.

    A process whose path is unavailable and that has already exited is ignored
    unless its ``comm`` names a deny-listed program.
    """
    out = []
    for proc, cls in classify(procs, policy, foreground):
        if cls != "forbidden":
            continue
        if proc.path is None and not alive(proc.pid) and not _denied(os.path.basename(proc.comm)):
            continue
        out.append({"pid": proc.pid, "ppid": proc.ppid, "pcpu": proc.pcpu,
                    "path": proc.path or f"unresolved:{proc.comm}"})
    return out


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def hid_idle_seconds() -> Optional[float]:
    """Seconds since the last keyboard, mouse or trackpad input (macOS)."""
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-r", "-d", "1", "-k", "HIDIdleTime"],
                         capture_output=True, text=True, env=C_ENV).stdout
    match = re.search(r'"HIDIdleTime" = (\d+)', out)
    return int(match.group(1)) / 1e9 if match else None


def hid_read() -> Tuple[Optional[float], float]:
    """(HID idle seconds, monotonic time of the read): the midpoint of the ``ioreg`` call."""
    before = time.monotonic()
    idle = hid_idle_seconds()
    return idle, (before + time.monotonic()) / 2


def hid_reset(previous_idle: float, previous_t: float, idle: float, t: float,
              tolerance: float = HID_TOLERANCE_S) -> bool:
    """True if input happened between two HID readings (times from one monotonic clock)."""
    return idle + tolerance < previous_idle + (t - previous_t)


def write_atomic(path: Path, data: Dict[str, object]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)


def run_monitor(policy_path: Path, out: Path, status: Path, interval: float) -> int:
    policy = Policy.load(policy_path)
    running = True
    reason = "signal"

    def stop(*_: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    seq = violations_total = hid_resets_total = hid_failures = foreground_failures = 0
    last_violation: Optional[Dict[str, object]] = None
    last_top = last_hid_wall = 0.0
    last_hid: Optional[Tuple[float, float]] = None
    foreground: Dict[int, str] = {}
    with open(out, "a", buffering=1) as handle:
        handle.write(json.dumps({"kind": "start", "utc": utc(), "pid": os.getpid(), "interval_s": interval,
                                 "policy": policy.to_json(), "system_prefixes": SYSTEM_PREFIXES,
                                 "deny_basenames": sorted(DENY_BASENAMES), "hid_tolerance_s": HID_TOLERANCE_S}) + "\n")
        while running:
            t = time.time()
            if not pid_alive(policy.chain_pid):
                reason = "chain_gone"
                break
            if t - last_hid_wall >= 1.0:
                try:
                    foreground = foreground_pids()
                except ForegroundUnavailable:
                    foreground_failures += 1
            procs = snapshot()
            found = forbidden(procs, policy, pid_alive, foreground)
            seq += 1
            if found:
                violations_total += 1
                last_violation = {"t": t, "processes": found}
            handle.write(json.dumps({"k": "s", "t": round(t, 3), "seq": seq, "v": found}) + "\n")
            if t - last_hid_wall >= 1.0:
                last_hid_wall = t
                idle, mono = hid_read()
                reset = False
                if idle is None:
                    hid_failures += 1
                else:
                    if last_hid is not None:
                        reset = hid_reset(last_hid[0], last_hid[1], idle, mono)
                    last_hid = (idle, mono)
                if reset:
                    hid_resets_total += 1
                handle.write(json.dumps({"k": "h", "t": round(time.time(), 3), "idle": idle, "reset": reset}) + "\n")
            if t - last_top >= 1.0:
                last_top = t
                rows = [(p, c) for p, c in classify(procs, policy, foreground) if c != "campaign"]
                rows.sort(key=lambda pc: -pc[0].pcpu)
                bg_pcpu = round(sum(p.pcpu for p, c in rows if c == "background"), 1)
                handle.write(json.dumps({"k": "top", "t": round(t, 3), "background_pcpu_sum": bg_pcpu, "processes": [
                    {"pid": p.pid, "pcpu": p.pcpu, "class": c, "path": (p.path or p.comm)[:160]}
                    for p, c in rows[:5]]}) + "\n")
            write_atomic(status, {"pid": os.getpid(), "t": t, "seq": seq, "violations_total": violations_total,
                                  "hid_resets_total": hid_resets_total, "hid_failures": hid_failures,
                                  "foreground_failures": foreground_failures, "hid_idle": last_hid[0] if last_hid else None, "last_violation": last_violation})
            time.sleep(max(0.0, interval - (time.time() - t)))
        handle.write(json.dumps({"kind": "stop", "utc": utc(), "reason": reason, "samples": seq,
                                 "violations_total": violations_total, "hid_resets_total": hid_resets_total,
                                 "hid_failures": hid_failures, "foreground_failures": foreground_failures}) + "\n")
    return 0


def git_snapshot(root: Path) -> Dict[str, Dict[str, object]]:
    """Read-only state of every Git directory under ``root`` (no symlinks followed)."""
    state: Dict[str, Dict[str, object]] = {}
    for dirpath, dirnames, _ in os.walk(root, followlinks=False):
        has_git = ".git" in dirnames
        dirnames[:] = [d for d in dirnames if d not in SNAPSHOT_SKIP]
        if has_git:
            git_dir = Path(dirpath) / ".git"
            if git_dir.is_dir() and not git_dir.is_symlink():
                fetch_head = git_dir / "FETCH_HEAD"
                reflogs = {}
                remotes = git_dir / "logs" / "refs" / "remotes"
                if remotes.is_dir():
                    for log in sorted(remotes.rglob("*")):
                        if log.is_file():
                            reflogs[str(log.relative_to(git_dir))] = log.stat().st_size
                state[str(git_dir)] = {"fetch_head_mtime": fetch_head.stat().st_mtime if fetch_head.exists() else None,
                                       "remote_reflog_bytes": reflogs}
    return state


def session_state(transcript: Path) -> Dict[str, Tuple[int, int]]:
    """Size and mtime of the controller's transcript and of every file in its session directory.

    Claude Code writes a session's transcript to ``<id>.jsonl`` and its
    subagents' transcripts under ``<id>/`` (``subagents/*.jsonl``). Any change
    means the session or one of its subagents acted.
    """
    state: Dict[str, Tuple[int, int]] = {}
    paths = [transcript]
    session_dir = transcript.with_suffix("")
    if session_dir.is_dir():
        paths += sorted(p for p in session_dir.rglob("*") if p.is_file())
    for path in paths:
        st = path.stat()
        state[str(path)] = (st.st_size, st.st_mtime_ns)
    return state


def tree_state(root: Path) -> Dict[str, Tuple[int, int]]:
    """Size and mtime of every file under ``root`` (amendment 2: ``~/.claude/projects``).

    With Claude quit nothing writes there; any change means a Claude session acted.
    """
    state: Dict[str, Tuple[int, int]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        st = path.stat()
        state[str(path)] = (st.st_size, st.st_mtime_ns)
    return state


def validate_transcript(transcript: Path, campaign: str, now: float, max_age_s: float = 600.0) -> List[str]:
    """Reasons the file is not the launching session's transcript (empty if it is)."""
    reasons: List[str] = []
    projects = Path.home() / ".claude" / "projects"
    resolved = transcript.resolve()
    if projects.resolve() not in resolved.parents or resolved.suffix != ".jsonl":
        reasons.append(f"{transcript} is not a session transcript under {projects}")
        return reasons
    if now - resolved.stat().st_mtime > max_age_s:
        reasons.append(f"{transcript} was not modified in the last {max_age_s:.0f} s")
    text = resolved.read_text(errors="replace")
    if "run_final_chain.sh" not in text or campaign not in text:
        reasons.append(f"{transcript} does not contain the launch of run_final_chain.sh for {campaign}")
    return reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    mon = sub.add_parser("monitor")
    mon.add_argument("--policy", type=Path, required=True)
    mon.add_argument("--out", type=Path, required=True)
    mon.add_argument("--status", type=Path, required=True)
    mon.add_argument("--interval", type=float, default=0.2)
    for name in ("check", "inventory"):
        p = sub.add_parser(name)
        p.add_argument("--policy", type=Path, required=True)
    pol = sub.add_parser("policy")
    pol.add_argument("--chain", type=int, required=True)
    pol.add_argument("--controller", type=int)
    pol.add_argument("--controller-kind", choices=KINDS, default="claude-cli")
    pol.add_argument("--matrix", type=Path, required=True)
    pol.add_argument("--out", type=Path, required=True)
    snap = sub.add_parser("git-snapshot")
    snap.add_argument("root", type=Path)
    sess = sub.add_parser("session-state")
    sess.add_argument("transcript", type=Path)
    vt = sub.add_parser("validate-transcript")
    vt.add_argument("transcript", type=Path)
    vt.add_argument("campaign")
    hid = sub.add_parser("hid-idle")
    tree = sub.add_parser("tree-state")
    tree.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "tree-state":
        print(json.dumps(tree_state(args.root), sort_keys=True))
        return 0
    if args.command == "session-state":
        print(json.dumps(session_state(args.transcript), sort_keys=True))
        return 0
    if args.command == "validate-transcript":
        reasons = validate_transcript(args.transcript, args.campaign, time.time())
        for reason in reasons:
            print(reason, file=sys.stderr)
        return 1 if reasons else 0
    if args.command == "hid-idle":
        idle = hid_idle_seconds()
        print("" if idle is None else f"{idle:.1f}")
        return 0 if idle is not None else 1
    if args.command == "monitor":
        return run_monitor(args.policy, args.out, args.status, args.interval)
    if args.command == "git-snapshot":
        print(json.dumps(git_snapshot(args.root), indent=1, sort_keys=True))
        return 0
    if args.command == "policy":
        baseline = json.loads(args.matrix.read_text())["conformance"]["host_baseline"]
        try:
            if args.controller_kind == "terminal":
                if args.controller is not None:
                    raise PolicyError("--controller is not used with --controller-kind terminal (Terminal.app is found from the chain)")
                policy = build_policy_terminal(snapshot(), args.chain, baseline, claude_cmdlines())
                policy.background_allowed = bool(json.loads(args.matrix.read_text())["conformance"].get("background_allowed", False))
            else:
                if args.controller is None:
                    raise PolicyError("--controller is required with --controller-kind claude-cli")
                policy = build_policy(snapshot(), args.chain, args.controller, baseline)
        except PolicyError as error:
            print(f"policy refused: {error}", file=sys.stderr)
            return 1
        args.out.write_text(json.dumps({**policy.to_json(), "written_utc": utc()}, indent=1))
        return 0
    policy = Policy.load(args.policy)
    procs, fg = snapshot(), foreground_pids()
    if args.command == "check":
        found = forbidden(procs, policy, pid_alive, fg)
        for row in found:
            print(json.dumps(row))
        return 1 if found else 0
    rows = sorted({(c, p.path or f"unresolved:{p.comm}") for p, c in classify(procs, policy, fg) if c != "campaign"})
    for cls, path in rows:
        print(f"{cls}\t{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
