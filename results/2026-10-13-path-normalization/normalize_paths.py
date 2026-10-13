#!/usr/bin/env python3
"""Replace machine-local absolute paths in archived experiment evidence.

The tool never edits files in place. It reads the listed files, writes the
normalized copies and a receipt, and aborts on any unexpected condition.

Path rules (most specific first; the home directory is given by ``--home`` and
is deliberately not recorded anywhere in the outputs):

* ``<home>/.copilot/session-state/<uuid>`` -> ``$SESSION_STATE`` (also when Python
  source splits the path over adjacent string literals)
* ``<home>/workspace/knotrel``             -> ``$WORKSPACE``
* ``<home>/.cargo``                        -> ``$CARGO_HOME``
* any other ``<home>``                     -> ``$HOME``

Hashes that depend on the rewritten text are maintained:

* ``arguments_sha256`` next to an ``arguments`` list is recomputed. The original
  value must first be reproducible from the original list, otherwise the tool stops.
* Any file hash that cites another listed file is replaced by that file's new
  hash, resolved depth-first. A citation cycle is an error.

Hashes of external artifacts (binaries, traces, templates) and
``environment_sha256`` (whose preimage is not stored) are intentionally untouched.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

VERSION = 1
SESSION = r"/\.copilot/session-state/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
HEX64 = re.compile(r"[0-9a-f]{64}")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_digest(value):
    return sha256(json.dumps(value, sort_keys=True).encode())


def rules(home):
    base = re.escape(home)
    uuid = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    return (
        ("session_state", re.compile(base + SESSION), "$SESSION_STATE"),
        # Python source that splits the path over adjacent string literals.
        ("session_state_split",
         re.compile(base + r"/\.copilot/session-state/(?P<join>\"\s+\")" + uuid + "/"),
         lambda m: "$SESSION_STATE/" + m["join"]),
        ("workspace", re.compile(base + r"/workspace/knotrel(?![A-Za-z0-9_-])"), "$WORKSPACE"),
        ("cargo_home", re.compile(base + r"/\.cargo(?![A-Za-z0-9_-])"), "$CARGO_HOME"),
        ("home", re.compile(base), "$HOME"),
    )


def normalize_text(text, rule_list):
    counts = {}
    for name, pattern, replacement in rule_list:
        text, count = pattern.subn(
            replacement if callable(replacement) else (lambda _m, r=replacement: r), text)
        counts[name] = count
    return text, counts


def argument_pairs(value):
    """Yield every dict holding both ``arguments`` and ``arguments_sha256``."""
    if isinstance(value, dict):
        if isinstance(value.get("arguments"), list) and "arguments_sha256" in value:
            yield value
        for child in value.values():
            yield from argument_pairs(child)
    elif isinstance(value, list):
        for child in value:
            yield from argument_pairs(child)


def run(args):
    home, root, stage = args.home, Path(args.root), Path(args.stage)
    files = [line for line in Path(args.list).read_text().splitlines() if line]
    if len(set(files)) != len(files) or stage.exists():
        raise SystemExit("duplicate list entries or existing stage directory")
    rule_list = rules(home)
    original = {rel: (root / rel).read_bytes() for rel in files}
    original_sha = {rel: sha256(data) for rel, data in original.items()}
    texts, counts, found = {}, {}, 0
    for rel, data in original.items():
        text = data.decode("utf-8")
        found += text.count(home)
        texts[rel], counts[rel] = normalize_text(text, rule_list)
        if home in texts[rel] or sum(counts[rel].values()) != text.count(home):
            raise SystemExit(f"{rel}: unaccounted home-directory occurrence")

    # arguments_sha256: reproduce the recorded value first, then recompute.
    digest_map, digests = {}, {rel: 0 for rel in files}
    for rel, data in original.items():
        if not rel.endswith(".json"):
            continue
        for holder in argument_pairs(json.loads(data)):
            old = json_digest(holder["arguments"])
            if old != holder["arguments_sha256"]:
                raise SystemExit(f"{rel}: arguments_sha256 is not reproducible")
            new_args = [normalize_text(a, rule_list)[0] for a in holder["arguments"]]
            new = json_digest(new_args)
            if digest_map.setdefault(old, new) != new:
                raise SystemExit("one argument digest maps to two values")
            digests[rel] += 1
    for rel in files:
        for old, new in digest_map.items():
            texts[rel] = texts[rel].replace(old, new)

    # File-hash citations become symbolic tokens, resolved depth-first.
    by_old = {sha: rel for rel, sha in original_sha.items()}
    citations = {rel: 0 for rel in files}
    for rel in files:
        for old in set(HEX64.findall(texts[rel])):
            target = by_old.get(old)
            if target is None:
                continue
            if target == rel:
                raise SystemExit(f"{rel}: cites its own hash")
            citations[rel] += texts[rel].count(old)
            texts[rel] = texts[rel].replace(old, f"@@SHA:{target}@@")
    final, resolving = {}, set()

    def render(rel):
        if rel in final:
            return final[rel]
        if rel in resolving:
            raise SystemExit(f"hash citation cycle at {rel}")
        resolving.add(rel)
        text = re.sub(r"@@SHA:(.+?)@@", lambda m: sha256(render(m[1])[0].encode()), texts[rel])
        resolving.discard(rel)
        final[rel] = (text, sha256(text.encode()))
        return final[rel]

    for rel in files:
        render(rel)
    for rel in files:
        text = final[rel][0]
        if home in text or "@@SHA:" in text:
            raise SystemExit(f"{rel}: unresolved placeholder or path")
        if rel.endswith(".json"):
            json.loads(text)
        elif rel.endswith(".jsonl"):
            [json.loads(line) for line in text.splitlines() if line]
        elif rel.endswith(".py"):
            ast.parse(text)

    entries, hash_map = [], {}
    for rel in files:
        text, new_sha = final[rel]
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        os.chmod(target, (root / rel).stat().st_mode & 0o777)
        hash_map[original_sha[rel]] = new_sha
        entries.append(dict(path=rel, original_sha256=original_sha[rel], normalized_sha256=new_sha,
                            replacements=counts[rel], argument_digests_recomputed=digests[rel],
                            file_hash_citations_updated=citations[rel]))
    receipt = dict(
        tool="normalize_paths.py", tool_version=VERSION,
        placeholders={"$SESSION_STATE": "agent session-state directory of the recording session",
                      "$WORKSPACE": "directory containing the sibling knotrel and knotrel-benchmarks checkouts",
                      "$CARGO_HOME": "cargo home directory", "$HOME": "user home directory (remaining paths)"},
        totals=dict(files=len(files), path_occurrences=found,
                    argument_digests_recomputed=sum(digests.values()),
                    file_hash_citations_updated=sum(citations.values()),
                    by_rule={name: sum(c[name] for c in counts.values()) for name, *_ in rule_list}),
        unchanged_by_design=["environment_sha256 (preimage not stored)",
                             "hashes of external artifacts: binaries, traces, templates, protocols"],
        files=entries)
    blob = json.dumps(receipt, indent=2) + "\n"
    if home in blob:
        raise SystemExit("receipt would contain the home directory")
    Path(args.receipt).write_text(blob)
    print(json.dumps(receipt["totals"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("home", "root", "list", "stage", "receipt"):
        parser.add_argument(f"--{name}", required=True)
    run(parser.parse_args())
    sys.exit(0)
