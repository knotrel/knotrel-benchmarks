#!/usr/bin/env python3
"""D1 of the knotrel#182 BFS regression diagnosis (PROTOCOL.md): replays an exported
connectivity trace with line-for-line models of v1.1.0 ``Graph::connected`` (unidirectional,
mark on enqueue, early exit on ``neighbor == b``) and 9faf168 ``Graph::connected``
(bidirectional, ``Side::expand``, smaller ``pending`` side first), counting the work.
Untimed. Every answer must equal the trace's ``expected`` or the run is void.

    replay_bfs_work.py TRACE.json [...] > work.json
"""
import bisect
import json
import sys


def load(path):
    record = json.load(open(path))
    return record, record["trace"]


class Graph:
    def __init__(self):
        self.ids, self.adj = {}, []

    def index(self, node):
        if node not in self.ids:
            self.ids[node] = len(self.adj)
            self.adj.append([])
        return self.ids[node]

    def link(self, s, t):
        a, b = self.index(s), self.index(t)
        i = bisect.bisect_left(self.adj[a], b)
        if i < len(self.adj[a]) and self.adj[a][i] == b:
            return
        self.adj[a].insert(i, b)
        bisect.insort(self.adj[b], a)

    def cut(self, s, t):
        a, b = self.ids.get(s), self.ids.get(t)
        if a is None or b is None or b not in self.adj[a]:
            return
        self.adj[a].remove(b)
        self.adj[b].remove(a)


def old_connected(adj, a, b, w):
    w["allocs_vbits"] += 1
    if a == b:
        return True
    visited = {a}
    queue = [a]
    cursor = 0
    while cursor < len(queue):
        for n in adj[queue[cursor]]:
            w["entries"] += 1
            if n == b:
                return True
            if n not in visited:
                visited.add(n)
                queue.append(n)
                w["marked"] += 1
        cursor += 1
    return False


def new_connected(adj, a, b, w):
    if a == b:
        return True
    w["allocs_vbits"] += 2
    sides = [{"marked": {a}, "frontier": [a], "pending": len(adj[a])},
             {"marked": {b}, "frontier": [b], "pending": len(adj[b])}]
    while sides[0]["frontier"] and sides[1]["frontier"]:
        e, o = (sides[0], sides[1]) if sides[0]["pending"] <= sides[1]["pending"] else (sides[1], sides[0])
        w["layers"] += 1
        nxt, pending = [], 0
        for v in e["frontier"]:
            for n in adj[v]:
                w["entries"] += 1
                if n in o["marked"]:
                    return True
                if n not in e["marked"]:
                    e["marked"].add(n)
                    nxt.append(n)
                    pending += len(adj[n])
                    w["marked"] += 1
                    w["degree_reads"] += 1
        e["frontier"], e["pending"] = nxt, pending
    return False


def replay(path):
    record, trace = load(path)
    g = Graph()
    for s, t in trace["initial_edges"]:
        g.link(s, t)
    out = {k: {"old": dict(entries=0, marked=0, allocs_vbits=0, layers=0, degree_reads=0, queries=0),
               "new": dict(entries=0, marked=0, allocs_vbits=0, layers=0, degree_reads=0, queries=0)}
           for k in ("query_true", "query_false")}
    for op in trace["operations"]:
        if op["op"] == "link":
            g.link(op["source"], op["target"])
        elif op["op"] == "cut":
            g.cut(op["source"], op["target"])
        else:
            a, b = g.ids[op["source"]], g.ids[op["target"]]
            key = "query_true" if op["expected"] else "query_false"
            for name, fn in (("old", old_connected), ("new", new_connected)):
                w = out[key][name]
                w["queries"] += 1
                if fn(g.adj, a, b, w) != op["expected"]:
                    raise SystemExit(f"VOID: {name} answer differs at {op} in {path}")
    return {"trace": path, "workload": record["workload"], "config": record["config"], "work": out}


if __name__ == "__main__":
    json.dump([replay(p) for p in sys.argv[1:]], sys.stdout, indent=1)
    print()
