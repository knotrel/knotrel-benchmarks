#!/usr/bin/env python3
"""Third-party autonomous launchers: inventory, audit and quiesce/restore (amendment 1).

Amendment 1 to the v0.7.0 re-qualification (``results/v0.7.0-requalification/
AMENDMENT-1-PROPOSAL.md``, PROTOCOL.md section 8). Nothing here changes how a running
process is classified; it is host preparation (A1) and a pre-launch precondition (A2).

Third-party criterion (A1 and A2): a launchd job or app extension is *Apple* only when its
plist path (if it has one) and its program path both lie in an Apple-controlled location:
``conformance_monitor.SYSTEM_PREFIXES`` (the frozen rule 9) plus ``/System/Applications/``
(sealed system volume; used here only, not by the process classification). Labels are never
trusted: a user job can call itself ``com.apple.*``.

Subcommands (all as the user, no root):

    launcher_audit.py audit    --matrix M [--out F]   exit 1 if the A2 audit fails
    launcher_audit.py quiesce  --matrix M --camp DIR  A1 boot-out and parking (manifest first)
    launcher_audit.py restore  --camp DIR             inverses of the manifest, verified
    launcher_audit.py pending  [--root EVIDENCE]      exit 1 if any manifest lacks a good restore
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conformance_monitor as cm  # noqa: E402

APPLE_LOCATIONS: Tuple[str, ...] = cm.SYSTEM_PREFIXES + ("/System/Applications/",)
AUTONOMOUS_KEYS = ("RunAtLoad", "KeepAlive", "StartInterval", "StartCalendarInterval",
                   "WatchPaths", "QueueDirectories", "StartOnMount", "LaunchEvents")
GATED_DOMAINS = ("gui/{uid}", "user/{uid}")
RECORDED_DOMAINS = ("system",)
PARK_SUFFIX = ".parked-qualification"
EVIDENCE_ROOT = Path("/Users/rt/workspace/knotrel/evidence")
MANIFEST = "quiesce-restore.json"
RESULT = "quiesce-restore-result.json"

Runner = Callable[[Sequence[str]], Tuple[int, str]]


def run(cmd: Sequence[str]) -> Tuple[int, str]:
    """(exit code, stdout); on failure stderr is appended so callers can read the reason.
    Callers must parse the output as data only when the exit code is 0 (crontab -l reads the
    failure text on purpose)."""
    proc = subprocess.run(list(cmd), capture_output=True, text=True, env=cm.C_ENV)
    return proc.returncode, proc.stdout if proc.returncode == 0 else proc.stdout + proc.stderr


def utc() -> str:
    return cm.utc()


def is_apple_path(path: Optional[str]) -> bool:
    return bool(path) and path.startswith(APPLE_LOCATIONS)


# --- launchd ---------------------------------------------------------------------------

def domain_labels(domain: str, runner: Runner = run) -> List[str]:
    """Labels of the services loaded in a launchd domain (``launchctl print <domain>``)."""
    rc, out = runner(["launchctl", "print", domain])
    if rc != 0:
        raise RuntimeError(f"launchctl print {domain} failed ({rc})")
    match = re.search(r"^\tservices = \{\n(.*?)^\t\}", out, re.S | re.M)
    if not match:
        raise RuntimeError(f"launchctl print {domain}: no services block")
    return [line.split()[-1] for line in match.group(1).splitlines() if line.strip()]


def parse_service(text: str) -> Dict[str, Optional[str]]:
    """``path`` and ``program`` of one ``launchctl print <domain>/<label>`` output."""
    path = re.search(r"^\tpath = (.*)$", text, re.M)
    program = re.search(r"^\tprogram = (.*)$", text, re.M)
    args = re.search(r"^\targuments = \{\n\t\t(.*)$", text, re.M)
    prog = program.group(1).strip() if program else (args.group(1).strip() if args else None)
    p = path.group(1).strip() if path else None
    return {"path": p, "program": prog}


def plist_triggers(path: str) -> Optional[List[str]]:
    """Autonomous triggers declared in a plist, or None when it cannot be read."""
    try:
        with open(path, "rb") as fh:
            data = plistlib.load(fh)
    except Exception:  # unreadable, missing or unparsable: unknown
        return None
    if not isinstance(data, dict):
        return None
    found = []
    for key in AUTONOMOUS_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key == "RunAtLoad" and value is not True:
            continue
        if key == "KeepAlive" and value is False:
            continue
        if key in ("StartOnMount",) and value is not True:
            continue
        found.append(key)
    return found


def describe_job(domain: str, label: str, runner: Runner = run,
                 triggers: Callable[[str], Optional[List[str]]] = plist_triggers) -> Dict[str, object]:
    rc, out = runner(["launchctl", "print", f"{domain}/{label}"])
    info: Dict[str, object] = {"domain": domain, "label": label, "path": None, "program": None,
                               "print_ok": rc == 0}
    if rc == 0:
        info.update(parse_service(out))
    path = info["path"]
    plist = path if isinstance(path, str) and path.startswith("/") else None
    info["plist"] = plist
    # Apple only with a plist and a program both in Apple locations; a job without a plist
    # ("(submitted by …)") or with an unreadable print is third-party (fail closed).
    info["apple"] = bool(info["print_ok"]) and is_apple_path(plist) and is_apple_path(info["program"])  # type: ignore[arg-type]
    info["triggers"] = triggers(plist) if plist else None
    return info


def allow_entry(label: str, allow: Dict[str, Dict[str, object]],
                allow_prefix: Dict[str, Dict[str, object]]) -> Optional[Dict[str, object]]:
    if label in allow:
        return allow[label]
    for prefix, entry in allow_prefix.items():
        if label.startswith(prefix):
            return entry
    return None


def allowed(job: Dict[str, object], entry: Dict[str, object]) -> Optional[str]:
    """None if the job matches its allow-list entry, else why not. An entry names the program
    prefix the job must run (None: the job must have no program line), the autonomous triggers
    it may declare, and whether undeterminable triggers are acceptable."""
    prog, prefix = job.get("program"), entry.get("program_prefix")
    if prefix is None:
        if prog is not None:
            return f"program {prog!r} present, entry expects none"
    elif not (isinstance(prog, str) and prog.startswith(str(prefix))):
        return f"program {prog!r} outside {prefix!r}"
    trig = job.get("triggers")
    if trig is None:
        return None if entry.get("unreadable_ok") else "triggers undeterminable"
    extra = sorted(set(trig) - set(entry.get("triggers", [])))  # type: ignore[arg-type]
    return f"triggers {extra} not permitted by its entry" if extra else None


def audit_jobs(jobs: List[Dict[str, object]], allow: Dict[str, Dict[str, object]],
               allow_prefix: Dict[str, Dict[str, object]]) -> List[str]:
    """A2 rule 1: third-party, not matching an allow-list entry, autonomous or unknown triggers."""
    reasons = []
    for job in jobs:
        if job["apple"]:
            continue
        label = str(job["label"])
        entry = allow_entry(label, allow, allow_prefix)
        if entry is not None:
            why = allowed(job, entry)
            if why:
                reasons.append(f"{job['domain']}/{label}: allow-listed but {why}")
            continue
        trig = job["triggers"]
        if trig is None:
            reasons.append(f"{job['domain']}/{label}: third-party job with undeterminable triggers "
                           f"(path {job['path']!r})")
        elif trig:
            reasons.append(f"{job['domain']}/{label}: third-party job with autonomous triggers {trig}")
    return reasons


# --- app extensions --------------------------------------------------------------------

def extensions(runner: Runner = run) -> List[Dict[str, object]]:
    """Every app extension pluginkit knows (``pluginkit -m -A -v``): id and bundle path."""
    rc, out = runner(["pluginkit", "-m", "-A", "-v"])
    if rc != 0:
        raise RuntimeError(f"pluginkit failed ({rc})")
    rows = []
    footer = None
    for line in out.splitlines():
        m = re.match(r"^\s*\((\d+) plug-ins?\)\s*$", line)
        if m:
            footer = int(m.group(1))
            continue
        if not line.strip():
            continue
        parts = line.strip().split("\t")
        if len(parts) < 4 or not parts[-1].startswith("/"):
            raise RuntimeError(f"pluginkit: unparsable line {line!r}")
        ident = re.sub(r"\(.*\)$", "", parts[0]).lstrip("+-=! ").strip()
        rows.append({"id": ident, "path": parts[-1]})
    if footer is None or footer != len(rows) or not rows:
        raise RuntimeError(f"pluginkit: parsed {len(rows)} extensions, footer {footer}")
    return rows


def audit_extensions(rows: List[Dict[str, object]], allow: Sequence[str],
                     exists: Callable[[str], bool] = os.path.exists) -> List[str]:
    """A2 rule 2: a third-party extension resolving to an existing bundle path."""
    return [f"extension {r['id']}: third-party, resolves to existing {r['path']}"
            for r in rows if not is_apple_path(str(r["path"])) and r["id"] not in allow
            and exists(str(r["path"]))]


def user_crontab(runner: Runner = run) -> str:
    rc, out = runner(["crontab", "-l"])
    if rc == 0:
        return out
    if "no crontab for" in out:
        return ""
    raise RuntimeError(f"crontab -l failed ({rc}): {out.strip()!r}")


# --- inventory and audit ---------------------------------------------------------------

def inventory(runner: Runner = run, uid: Optional[int] = None) -> Dict[str, object]:
    uid = os.getuid() if uid is None else uid
    jobs: List[Dict[str, object]] = []
    recorded: List[Dict[str, object]] = []
    for template in GATED_DOMAINS:
        domain = template.format(uid=uid)
        for label in domain_labels(domain, runner):
            jobs.append(describe_job(domain, label, runner))
    for domain in RECORDED_DOMAINS:
        try:
            labels = domain_labels(domain, runner)
        except RuntimeError as error:
            recorded.append({"domain": domain, "error": str(error)})
            continue
        for label in labels:
            info = describe_job(domain, label, runner)
            if not info["apple"]:
                recorded.append(info)
    return {"utc": utc(), "uid": uid, "apple_locations": list(APPLE_LOCATIONS),
            "jobs": jobs, "system_third_party": recorded,
            "extensions": extensions(runner), "user_crontab": user_crontab(runner)}


def audit(inv: Dict[str, object], quiesce: Dict[str, object],
          exists: Callable[[str], bool] = os.path.exists) -> List[str]:
    reasons = audit_jobs(inv["jobs"], quiesce.get("allow_jobs", {}),  # type: ignore[arg-type]
                         quiesce.get("allow_jobs_prefix", {}))  # type: ignore[arg-type]
    reasons += audit_extensions(inv["extensions"], quiesce.get("allow_extensions", []), exists)  # type: ignore[arg-type]
    cron = str(inv.get("user_crontab", ""))
    if any(line.strip() and not line.lstrip().startswith("#") for line in cron.splitlines()):
        reasons.append("user crontab is not empty")
    return reasons


# --- quiesce and restore ---------------------------------------------------------------

def _write(path: Path, data: Dict[str, object]) -> None:
    """Atomic and durable: write, fsync, rename, fsync the directory."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def manual_commands(manifest: Dict[str, object]) -> List[str]:
    """Commands for every action that was started (intent recorded), quoted for sh."""
    cmds = []
    for job in manifest.get("jobs", []):  # type: ignore[union-attr]
        if job.get("intent") == "bootout":
            cmds.append(f"launchctl bootstrap {job['domain']} {shlex.quote(str(job['plist']))}")
    for app in manifest.get("apps", []):  # type: ignore[union-attr]
        if app.get("intent") == "rename":
            cmds.append(f"mv -n {shlex.quote(str(app['parked_path']))} {shlex.quote(str(app['path']))}")
    if cmds:
        cmds.append("python3 scripts/launcher_audit.py restore --camp <CAMP>  # records the restore and clears 'pending'")
    return cmds


def pending(root: Path = EVIDENCE_ROOT) -> List[str]:
    """Manifests under ``root`` without a successful restore result next to them."""
    out = []
    for manifest in sorted(root.glob(f"*/logs/{MANIFEST}")):
        result = manifest.with_name(RESULT)
        ok = False
        if result.exists():
            try:
                ok = bool(json.loads(result.read_text()).get("ok"))
            except ValueError:
                ok = False
        if not ok:
            out.append(str(manifest))
    return out


def job_loaded(domain: str, label: str, runner: Runner = run) -> bool:
    return runner(["launchctl", "print", f"{domain}/{label}"])[0] == 0


def quiesce(camp: Path, conf: Dict[str, object], runner: Runner = run,
            uid: Optional[int] = None, root: Path = EVIDENCE_ROOT,
            take_inventory: Optional[Callable[[], Dict[str, object]]] = None,
            exists: Callable[[str], bool] = os.path.exists) -> Tuple[bool, Dict[str, object]]:
    """A1. Inventory first; the manifest records each action's intent (and its manual inverse)
    before the action and its outcome after it."""
    uid = os.getuid() if uid is None else uid
    logs = camp / "logs"
    stale = pending(root)
    if stale:
        return False, {"refused": "unrestored quiesce manifest(s)", "manifests": stale}
    take_inventory = take_inventory or (lambda: inventory(runner, uid))
    try:
        _write(logs / "quiesce-inventory.json", take_inventory())
    except RuntimeError as error:
        return False, {"refused": f"inventory failed: {error}"}
    domain = f"gui/{uid}"
    manifest: Dict[str, object] = {"utc": utc(), "camp": str(camp), "jobs": [], "apps": [], "errors": [],
                                   "manual_restore": []}
    path = logs / MANIFEST
    _write(path, manifest)
    ok = True

    def record() -> None:
        manifest["manual_restore"] = manual_commands(manifest)
        _write(path, manifest)

    for label in conf.get("launchd", []):  # type: ignore[union-attr]
        job: Dict[str, object] = {"domain": domain, "label": label, "booted_out": False}
        manifest["jobs"].append(job)  # type: ignore[union-attr]
        rc, out = runner(["launchctl", "print", f"{domain}/{label}"])
        if rc != 0:
            job["loaded_before"] = False
            record()
            continue
        info = parse_service(out)
        job.update({"loaded_before": True, "plist": info["path"]})
        if not (isinstance(info["path"], str) and info["path"].startswith("/")):
            manifest["errors"].append(f"{label}: no plist to restore from; not booted out")  # type: ignore[union-attr]
            ok = False
            record()
            continue
        job["intent"] = "bootout"
        record()
        runner(["launchctl", "bootout", f"{domain}/{label}"])
        gone = not job_loaded(domain, label, runner)
        job["booted_out"] = gone
        if not gone:
            manifest["errors"].append(f"{label}: still loaded after bootout")  # type: ignore[union-attr]
            ok = False
        record()
    for app_path in conf.get("park_apps", []):  # type: ignore[union-attr]
        parked = app_path + PARK_SUFFIX
        app: Dict[str, object] = {"path": app_path, "parked_path": parked, "parked": False}
        manifest["apps"].append(app)  # type: ignore[union-attr]
        if not os.path.exists(app_path):
            app["present_before"] = False
            record()
            continue
        app["present_before"] = True
        if os.path.exists(parked):
            manifest["errors"].append(f"{parked} already exists; not parked")  # type: ignore[union-attr]
            ok = False
            record()
            continue
        app["intent"] = "rename"
        record()
        try:
            os.rename(app_path, parked)
            app["parked"] = True
        except OSError as error:
            manifest["errors"].append(f"{app_path}: rename failed: {error}")  # type: ignore[union-attr]
            ok = False
        record()
    # Parked bundles must no longer resolve for any extension pluginkit knows.
    try:
        rows = extensions(runner)
        prefixes = tuple(str(a["path"]).rstrip("/") + "/" for a in manifest["apps"] if a.get("parked"))  # type: ignore[union-attr]
        still = [r for r in rows if prefixes and str(r["path"]).startswith(prefixes) and exists(str(r["path"]))]
        manifest["extensions_after_park"] = still
        if still:
            manifest["errors"].append(f"extensions still resolve after parking: {still}")  # type: ignore[union-attr]
            ok = False
    except RuntimeError as error:
        manifest["errors"].append(f"pluginkit check after parking failed: {error}")  # type: ignore[union-attr]
        ok = False
    manifest["quiesce_ok"] = ok
    manifest["finished_utc"] = utc()
    record()
    return ok, manifest


def restore(camp: Path, runner: Runner = run) -> Tuple[bool, Dict[str, object]]:
    """Inverse of every action whose intent was recorded, verified; never overwrites an
    occupied path. Actions never started (no intent) are not touched."""
    path = camp / "logs" / MANIFEST
    if not path.exists():
        return True, {"utc": utc(), "ok": True, "note": "no manifest"}
    try:
        manifest = json.loads(path.read_text())
    except ValueError as error:
        result = {"utc": utc(), "ok": False, "error": f"manifest unreadable ({error}); use the manual procedure "
                  "in PROTOCOL.md section 8.5, then re-run restore after replacing the manifest"}
        _write(camp / "logs" / RESULT, result)
        return False, result
    actions: List[Dict[str, object]] = []
    ok = True
    for job in manifest.get("jobs", []):
        plist = job.get("plist")
        if job.get("intent") != "bootout" or not (isinstance(plist, str) and plist.startswith("/")):
            continue
        domain, label = job["domain"], job["label"]
        row: Dict[str, object] = {"label": label}
        if job_loaded(domain, label, runner):
            row["result"] = "already loaded"
        else:
            rc, _ = runner(["launchctl", "bootstrap", domain, plist])
            row["bootstrap_rc"] = rc
            row["result"] = "restored" if job_loaded(domain, label, runner) else "FAILED"
        ok &= row["result"] != "FAILED"
        actions.append(row)
    for app in manifest.get("apps", []):
        if app.get("intent") != "rename":
            continue
        orig, parked = app["path"], app["parked_path"]
        row = {"path": orig}
        if os.path.exists(orig) and not os.path.exists(parked):
            row["result"] = "already in place"
        elif os.path.exists(orig):
            row["result"] = "FAILED: original path occupied; parked bundle left in place"
        elif os.path.exists(parked):
            try:
                os.rename(parked, orig)
                row["result"] = "restored" if os.path.exists(orig) else "FAILED"
            except OSError as error:
                row["result"] = f"FAILED: {error}"
        else:
            row["result"] = "FAILED: neither path exists"
        ok &= not str(row["result"]).startswith("FAILED")
        actions.append(row)
    result = {"utc": utc(), "ok": ok, "actions": actions,
              "manual_restore": manifest.get("manual_restore", [])}
    _write(camp / "logs" / RESULT, result)
    return ok, result


# --- CLI -------------------------------------------------------------------------------

def _quiesce_conf(matrix: Path) -> Dict[str, object]:
    return json.loads(matrix.read_text())["conformance"]["quiesce"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--matrix", type=Path, required=True)
    a.add_argument("--out", type=Path)
    q = sub.add_parser("quiesce")
    q.add_argument("--matrix", type=Path, required=True)
    q.add_argument("--camp", type=Path, required=True)
    r = sub.add_parser("restore")
    r.add_argument("--camp", type=Path, required=True)
    p = sub.add_parser("pending")
    p.add_argument("--root", type=Path, default=EVIDENCE_ROOT)
    args = parser.parse_args(argv)
    if args.command == "pending":
        stale = pending(args.root)
        for s in stale:
            print(s)
        return 1 if stale else 0
    if args.command == "restore":
        ok, result = restore(args.camp)
        print(json.dumps(result, indent=1))
        return 0 if ok else 1
    conf = _quiesce_conf(args.matrix)
    if args.command == "quiesce":
        ok, manifest = quiesce(args.camp, conf)
        print(json.dumps(manifest, indent=1))
        return 0 if ok else 1
    try:
        inv = inventory()
    except RuntimeError as error:
        print(f"audit could not run: {error}", file=sys.stderr)
        return 1
    reasons = audit(inv, conf)
    report = {**inv, "reasons": reasons, "passed": not reasons}
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))
    for reason in reasons:
        print(reason, file=sys.stderr)
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
