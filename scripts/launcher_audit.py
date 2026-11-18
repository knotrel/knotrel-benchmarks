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
    proc = subprocess.run(list(cmd), capture_output=True, text=True, env=cm.C_ENV)
    return proc.returncode, proc.stdout


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


def audit_jobs(jobs: List[Dict[str, object]], allow: Sequence[str], allow_prefix: Sequence[str]) -> List[str]:
    """A2 rule 1: third-party, not allowed, autonomous or unknown triggers."""
    reasons = []
    for job in jobs:
        if job["apple"]:
            continue
        label = str(job["label"])
        if label in allow or any(label.startswith(p) for p in allow_prefix):
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
    for line in out.splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 4 and parts[-1].startswith("/"):
            ident = re.sub(r"\(.*\)$", "", parts[0]).lstrip("+-=! ").strip()
            rows.append({"id": ident, "path": parts[-1]})
    return rows


def audit_extensions(rows: List[Dict[str, object]], allow: Sequence[str],
                     exists: Callable[[str], bool] = os.path.exists) -> List[str]:
    """A2 rule 2: a third-party extension resolving to an existing bundle path."""
    return [f"extension {r['id']}: third-party, resolves to existing {r['path']}"
            for r in rows if not is_apple_path(str(r["path"])) and r["id"] not in allow
            and exists(str(r["path"]))]


def user_crontab(runner: Runner = run) -> str:
    rc, out = runner(["crontab", "-l"])
    return out if rc == 0 else ""


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
    reasons = audit_jobs(inv["jobs"], quiesce.get("allow_jobs", []),  # type: ignore[arg-type]
                         quiesce.get("allow_jobs_prefix", []))  # type: ignore[arg-type]
    reasons += audit_extensions(inv["extensions"], quiesce.get("allow_extensions", []), exists)  # type: ignore[arg-type]
    cron = str(inv.get("user_crontab", ""))
    if any(line.strip() and not line.lstrip().startswith("#") for line in cron.splitlines()):
        reasons.append("user crontab is not empty")
    return reasons


# --- quiesce and restore ---------------------------------------------------------------

def _write(path: Path, data: Dict[str, object]) -> None:
    cm.write_atomic(path, data)


def manual_commands(manifest: Dict[str, object]) -> List[str]:
    cmds = []
    for job in manifest.get("jobs", []):  # type: ignore[union-attr]
        if job.get("booted_out"):
            cmds.append(f"launchctl bootstrap {job['domain']} '{job['plist']}'")
    for app in manifest.get("apps", []):  # type: ignore[union-attr]
        if app.get("parked"):
            cmds.append(f"mv '{app['parked_path']}' '{app['path']}'")
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
            uid: Optional[int] = None, root: Path = EVIDENCE_ROOT) -> Tuple[bool, Dict[str, object]]:
    """A1. The manifest is written before every action and updated after it."""
    uid = os.getuid() if uid is None else uid
    logs = camp / "logs"
    stale = pending(root)
    if stale:
        return False, {"refused": "unrestored quiesce manifest(s)", "manifests": stale}
    domain = f"gui/{uid}"
    manifest: Dict[str, object] = {"utc": utc(), "camp": str(camp), "jobs": [], "apps": [], "errors": []}
    path = logs / MANIFEST
    _write(path, manifest)
    ok = True
    for label in conf.get("launchd", []):  # type: ignore[union-attr]
        job: Dict[str, object] = {"domain": domain, "label": label, "booted_out": False}
        rc, out = runner(["launchctl", "print", f"{domain}/{label}"])
        if rc != 0:
            job["loaded_before"] = False
            manifest["jobs"].append(job)  # type: ignore[union-attr]
            _write(path, manifest)
            continue
        info = parse_service(out)
        job.update({"loaded_before": True, "plist": info["path"], "intent": "bootout"})
        manifest["jobs"].append(job)  # type: ignore[union-attr]
        manifest["manual_restore"] = manual_commands(manifest) + [
            f"launchctl bootstrap {domain} '{info['path']}'"]
        _write(path, manifest)
        if not (isinstance(info["path"], str) and info["path"].startswith("/")):
            manifest["errors"].append(f"{label}: no plist to restore from; not booted out")  # type: ignore[union-attr]
            ok = False
            _write(path, manifest)
            continue
        runner(["launchctl", "bootout", f"{domain}/{label}"])
        gone = not job_loaded(domain, label, runner)
        job["booted_out"] = gone
        if not gone:
            manifest["errors"].append(f"{label}: still loaded after bootout")  # type: ignore[union-attr]
            ok = False
        manifest["manual_restore"] = manual_commands(manifest)
        _write(path, manifest)
    for app_path in conf.get("park_apps", []):  # type: ignore[union-attr]
        parked = app_path + PARK_SUFFIX
        app: Dict[str, object] = {"path": app_path, "parked_path": parked, "parked": False}
        manifest["apps"].append(app)  # type: ignore[union-attr]
        if not os.path.exists(app_path):
            app["present_before"] = False
            _write(path, manifest)
            continue
        app["present_before"] = True
        if os.path.exists(parked):
            manifest["errors"].append(f"{parked} already exists; not parked")  # type: ignore[union-attr]
            ok = False
            _write(path, manifest)
            continue
        app["intent"] = "rename"
        _write(path, manifest)
        try:
            os.rename(app_path, parked)
            app["parked"] = True
        except OSError as error:
            manifest["errors"].append(f"{app_path}: rename failed: {error}")  # type: ignore[union-attr]
            ok = False
        manifest["manual_restore"] = manual_commands(manifest)
        _write(path, manifest)
    manifest["quiesce_ok"] = ok
    manifest["finished_utc"] = utc()
    _write(path, manifest)
    return ok, manifest


def restore(camp: Path, runner: Runner = run) -> Tuple[bool, Dict[str, object]]:
    """Inverse of every recorded action, verified; never overwrites an occupied path."""
    path = camp / "logs" / MANIFEST
    if not path.exists():
        return True, {"utc": utc(), "ok": True, "note": "no manifest"}
    manifest = json.loads(path.read_text())
    actions: List[Dict[str, object]] = []
    ok = True
    for job in manifest.get("jobs", []):
        if not job.get("loaded_before") or not job.get("plist"):
            continue
        domain, label = job["domain"], job["label"]
        row: Dict[str, object] = {"label": label}
        if job_loaded(domain, label, runner):
            row["result"] = "already loaded"
        else:
            rc, _ = runner(["launchctl", "bootstrap", domain, job["plist"]])
            row["bootstrap_rc"] = rc
            row["result"] = "restored" if job_loaded(domain, label, runner) else "FAILED"
        ok &= row["result"] != "FAILED"
        actions.append(row)
    for app in manifest.get("apps", []):
        if not app.get("present_before"):
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
