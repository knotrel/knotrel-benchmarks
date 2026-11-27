#!/usr/bin/env python3
"""Block D of the adaptive-BFS impact estimate (untimed, not deciding; protocol section 5).

1. Work counts: replays the K1 traces (exported with the candidate harness, ``--trace-out``)
   and hub-leaf traces with both endpoint orders through line-for-line models of v1.1.0 and of
   the frozen candidate (``adaptive_search``), counting vertices expanded, adjacency entries
   examined and side switches per query kind. Every replayed answer must equal ``expected``.
2. R10 layout: disassembles ``connected_with_workspace`` in the two V1 harness builds and
   compares instructions (branch targets relative to the function start) and addresses.

    diagnostic_d.py E OUT_DIR
"""
import bisect
import json
import re
import subprocess
import sys
from pathlib import Path

E = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True)
H = E / "targets/cand-harness/release/knotrel-benchmarks"
K1 = [(c["id"], c["arms"]["cf"]["args"]) for c in json.loads(
    (Path(__file__).resolve().parent.parent / "v1.2.0-qualification/v120q-matrix.json").read_text())["cells"]
      if c["block"] == "K1"]


class Graph:
    def __init__(self):
        self.ids, self.adj = {}, []

    def index(self, node):
        if node not in self.ids:
            self.ids[node] = len(self.adj); self.adj.append([])
        return self.ids[node]

    def link(self, s, t):
        a, b = self.index(s), self.index(t)
        i = bisect.bisect_left(self.adj[a], b)
        if i < len(self.adj[a]) and self.adj[a][i] == b:
            return
        self.adj[a].insert(i, b); bisect.insort(self.adj[b], a)

    def cut(self, s, t):
        a, b = self.ids.get(s), self.ids.get(t)
        if a is None or b is None or b not in self.adj[a]:
            return
        self.adj[a].remove(b); self.adj[b].remove(a)


def v110(adj, a, b, w):
    if a == b:
        return True
    seen, queue, cur = {a}, [a], 0
    while cur < len(queue):
        w["expanded"] += 1
        for n in adj[queue[cur]]:
            w["entries"] += 1
            if n == b:
                return True
            if n not in seen:
                seen.add(n); queue.append(n)
        cur += 1
    return False


def cand(adj, a, b, w):
    if a == b:
        return True
    if not adj[a] or not adj[b]:
        return False
    marks = {a: 0, b: 1}
    sides = [{"q": [a], "c": 0, "p": len(adj[a])}, {"q": [b], "c": 0, "p": len(adj[b])}]
    active = 1 if len(adj[a]) > len(adj[b]) else 0
    while True:
        s, o = sides[active], sides[1 - active]
        v = s["q"][s["c"]]; s["c"] += 1; s["p"] -= len(adj[v]); w["expanded"] += 1
        for n in adj[v]:
            w["entries"] += 1
            m = marks.get(n)
            if m == 1 - active:
                return True
            if m is None:
                marks[n] = active; s["q"].append(n); s["p"] += len(adj[n])
        if s["c"] == len(s["q"]):
            return False
        if s["p"] > 2 * o["p"]:
            active = 1 - active; w["switches"] += 1


def replay(trace_path, reverse=False):
    rec = json.loads(Path(trace_path).read_text())
    g = Graph()
    for s, t in rec["trace"]["initial_edges"]:
        g.link(s, t)
    out = {k: {m: {"queries": 0, "expanded": 0, "entries": 0, "switches": 0} for m in ("v110", "cand")}
           for k in ("query_true", "query_false")}
    for op in rec["trace"]["operations"]:
        if op["op"] == "link":
            g.link(op["source"], op["target"])
        elif op["op"] == "cut":
            g.cut(op["source"], op["target"])
        else:
            s, t = (op["target"], op["source"]) if reverse else (op["source"], op["target"])
            a, b = g.ids[s], g.ids[t]
            key = "query_true" if op["expected"] else "query_false"
            for name, fn in (("v110", v110), ("cand", cand)):
                w = out[key][name]; w["queries"] += 1
                if fn(g.adj, a, b, w) != op["expected"]:
                    raise SystemExit(f"VOID: {name} answer differs at {op} ({trace_path}, reverse={reverse})")
    return out


work = {}
for cell_id, args in K1:
    path = OUT / f"{cell_id}.trace.json"
    argv = [str(H)] + [x for x in args] + ["--trace-out", str(path)]
    argv[argv.index("--warmup") + 1] = "0"
    subprocess.run(argv, check=True, capture_output=True)
    work[cell_id] = {"forward": replay(path)}
    if "hub-alternatives" in cell_id:
        work[cell_id]["reversed"] = replay(path, reverse=True)
    path.unlink()
(OUT / "work.json").write_text(json.dumps(work, indent=1))


def disasm(binary):
    sym = [l.split()[2] for l in subprocess.run(["nm", str(binary)], capture_output=True, text=True).stdout.splitlines()
           if "connected_with_workspace" in l][0]
    text = subprocess.run(["objdump", "-d", "--no-show-raw-insn", f"--disassemble-symbols={sym}", str(binary)],
                          capture_output=True, text=True).stdout
    lines = [l for l in text.splitlines() if re.match(r"^\s*[0-9a-f]+:", l)]
    base = int(lines[0].split(":")[0], 16); end = int(lines[-1].split(":")[0], 16)
    def rel(m):
        v = int(m.group(0), 16)
        return f"+{v - base}" if base <= v <= end + 4 else "EXT"
    body = [re.sub(r"\s+", " ", re.sub(r"0x[0-9a-f]{5,}", rel, re.sub(r"<[^>]*>", "", l.split(":", 1)[1]))).strip()
            for l in lines]
    return base, body


bb, b_body = disasm(E / "targets/A-B-harness/release/knotrel-benchmarks")
cb, c_body = disasm(E / "targets/A-C-harness/release/knotrel-benchmarks")
layout = {"B_v110": {"address": hex(bb), "mod64": bb % 64, "instructions": len(b_body)},
          "C_cand": {"address": hex(cb), "mod64": cb % 64, "instructions": len(c_body)},
          "identical_instructions": b_body == c_body, "address_shift_bytes": cb - bb}
(OUT / "r10-layout.json").write_text(json.dumps(layout, indent=1))
print(json.dumps({"layout": layout, "cells": len(work)}))
