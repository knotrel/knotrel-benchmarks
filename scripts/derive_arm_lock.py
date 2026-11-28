#!/usr/bin/env python3
"""Derives a knotrel-benchmarks lockfile for one knotrel arm (v1.2.0 attempt 3, knotrel#182).

    derive_arm_lock.py LOCK_IN LOCK_OUT KNOTREL_CHECKOUT

The tooling's lockfiles serve both arms of a campaign. They differ from what each arm's
``knotrel-core`` needs in two ways only:

- the ``knotrel-core`` version line (as the A harness derivation of ``prepare_v120q.sh``);
- ``nohash-hasher``: v1.1.0's core depends on it, the candidate's does not (knotrel#210).

This script rewrites exactly those two things to match KNOTREL_CHECKOUT's
``crates/knotrel-core/Cargo.toml`` and ``Cargo.toml`` and leaves every other byte as it is, so
``cargo build --locked`` accepts the result. The ``nohash-hasher`` entry it inserts is the one
of the published 0.2.0 crate (the version every knotrel release up to v1.1.0 locks). A
lockfile that already matches is copied unchanged.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NOHASH_STANZA = ('[[package]]\nname = "nohash-hasher"\nversion = "0.2.0"\n'
                 'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
                 'checksum = "2bf50223579dc7cdcfb3bfcacf7069ff68243f8c363f62ffa99cf000a6b9c451"\n')


def core_needs_nohash(knotrel: Path) -> bool:
    manifest = (knotrel / "crates" / "knotrel-core" / "Cargo.toml").read_text()
    deps = manifest.split("[dependencies]", 1)[1].split("\n[", 1)[0]
    return re.search(r"^nohash-hasher\b", deps, re.M) is not None


def core_version(knotrel: Path) -> str:
    match = re.search(r'^version = "([^"]+)"', (knotrel / "Cargo.toml").read_text(), re.M)
    if not match:
        raise SystemExit(f"no workspace version in {knotrel}/Cargo.toml")
    return match.group(1)


def derive(text: str, version: str, nohash: bool) -> str:
    blocks = text.split("\n\n")
    out = []
    has_stanza = any(b.startswith('[[package]]\nname = "nohash-hasher"\n') for b in blocks)
    core_seen = 0
    for block in blocks:
        if block.startswith('[[package]]\nname = "nohash-hasher"\n'):
            if nohash:
                out.append(block)
            continue
        if block.startswith('[[package]]\nname = "knotrel-core"\n'):
            core_seen += 1
            block = re.sub(r'^version = "[^"]+"', f'version = "{version}"', block, count=1,
                           flags=re.M)
            head, sep, rest = block.partition("dependencies = [\n")
            if not sep:
                raise SystemExit("knotrel-core has no dependency list")
            items, _, tail = rest.partition("]")
            names = [line for line in items.split("\n") if line.strip()]
            names = [n for n in names if n.strip() != '"nohash-hasher",']
            if nohash:
                names.append(' "nohash-hasher",')
            names.sort(key=lambda n: n.strip().strip('",'))
            block = head + sep + "\n".join(names) + "\n]" + tail
        out.append(block)
    if core_seen != 1:
        raise SystemExit(f"expected one knotrel-core package, found {core_seen}")
    if nohash and not has_stanza:
        # Insert in cargo's order (packages sorted by name).
        stanza = NOHASH_STANZA.rstrip("\n")
        for index, block in enumerate(out):
            name = re.search(r'^name = "([^"]+)"', block, re.M)
            if block.startswith("[[package]]") and name and name.group(1) > "nohash-hasher":
                out.insert(index, stanza)
                break
        else:
            out.append(stanza)
    return "\n\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit(__doc__)
    lock_in, lock_out, knotrel = Path(argv[0]), Path(argv[1]), Path(argv[2])
    text = lock_in.read_text()
    lock_out.write_text(derive(text, core_version(knotrel), core_needs_nohash(knotrel)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
