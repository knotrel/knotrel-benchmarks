#!/usr/bin/env python3
"""HTTP pagination cells P3 and P4 of the knotrel#151 comparison.

    http_pages_151.py --server-bin S --emit-bin C --engine E --nodes N --degree D
                      --seed SEED --cell p3|p4 [--cursors 100]

knotrel ``docs/design/compact-node-index.md``, section 6.4. The method of knotrel
``scripts/measure-inspection-costs.py``: a fresh ``knotrel-server`` process on a free
loopback port (lifecycle and inspection on, unlimited graph limits), one persistent
HTTP/1.1 connection (``http.client``), client-side latency with ``perf_counter_ns``.
Standard library only.

The graph and the cursors come from the arm's own ``compact-cells emit`` (the
``hub-in-sparse`` workload, ``lifecycle_probes::compact``), so both arms load exactly
the same input: ``add_node`` in the scrambled order, every ``link``, then every ghost is
registered and linked to the hub, and finally every ghost is removed (cursors naming
removed nodes), all through ``POST /v1/batch`` (1024 operations per request, bodies
prebuilt by ``emit``). Every batch item must report a change; ``GET /v1/stats`` must
then equal the workload. A ``next_after_target`` of ``null`` with a non-null
``next_after_source`` continues after that source (only ``after_source`` is sent).

- ``p3``: ``GET /v1/nodes/{hub}/edges?limit=1000&after=C`` at the 3 x ``--cursors``
  shuffled cursors (registered neighbors, removed ghosts, never-registered IDs);
  ``median_ns``, ``p99_ns`` (nearest rank) of the client latencies.
- ``p4``: ``GET /v1/edges?limit=1000``: one full traversal following
  ``next_after_source``/``next_after_target`` (``traversal_ns``: summed request
  latencies; cursor extraction is untimed), then single pages at the 3 x ``--cursors``
  shuffled ``(after_source, after_target)`` cursors (registered edges, a removed ghost
  as source or target, a never-registered ID as source or target): ``page_p99_ns``,
  ``page_median_ns``.

Output: one JSON line with the metrics, ``errors`` (non-200 answers and batch items
without a change) and ``gate``: workload fingerprint, ``/v1/stats`` counts, page count
and a digest over the SHA-256 of every page body (``page_digests`` lists them). Exit
status 1 on any error.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_paths import confined_executable  # noqa: E402

BATCH = 1024
PAGE = 1000


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Client:
    def __init__(self, port: int) -> None:
        self.conn = http.client.HTTPConnection("127.0.0.1", port, timeout=600)

    def get(self, path: str) -> Tuple[int, bytes, int]:
        start = time.perf_counter_ns()
        self.conn.request("GET", path)
        response = self.conn.getresponse()
        body = response.read()
        return response.status, body, time.perf_counter_ns() - start

    def post_raw(self, path: str, body: bytes) -> Tuple[int, bytes]:
        self.conn.request("POST", path, body=body, headers={"content-type": "application/json"})
        response = self.conn.getresponse()
        return response.status, response.read()


class Server:
    def __init__(self, binary: str, engine: str) -> None:
        self.port = free_port()
        env = dict(os.environ)
        env.update({"KNOTREL_ADDR": f"127.0.0.1:{self.port}", "KNOTREL_ENGINE": engine,
                    "KNOTREL_TOPOLOGY_LIFECYCLE": "true", "KNOTREL_INSPECTION": "true",
                    "KNOTREL_MAX_NODES": "unlimited", "KNOTREL_MAX_EDGES": "unlimited",
                    "KNOTREL_METRICS_ENABLED": "false",
                    "KNOTREL_REQUEST_TIMEOUT_MS": "600000"})
        self.proc = subprocess.Popen([binary], env=env, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if Client(self.port).get("/health")[0] == 200:
                    return
            except OSError:
                time.sleep(0.05)
        self.stop()
        raise RuntimeError("server did not start")

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def emitted(emit_bin: str, args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    done = subprocess.run([emit_bin, "emit", "--workload", "hub-in-sparse",
                           "--nodes", str(args.nodes), "--degree", str(args.degree),
                           "--seed", str(args.seed), "--cursors", str(args.cursors)],
                          capture_output=True, text=True, check=True)
    lines = done.stdout.splitlines()
    return json.loads(lines[0]), lines[1:]


def load(client: Client, lines: List[str]) -> int:
    """Posts the prebuilt batches; returns the number of errors (non-200 answers and items
    that do not report a change)."""
    errors = 0
    for line in lines:
        _tag, count, body = line.split(" ", 2)
        status, reply = client.post_raw("/v1/batch", body.encode())
        if status != 200:
            errors += 1
            continue
        errors += int(count) - reply.count(b'"changed":true')
    return errors


def nearest_rank(values: List[int], q: float) -> int:
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * int(q * 100) // 100))
    return ordered[rank - 1]


def lower_median(values: List[int]) -> int:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:16]


def combined(digests: List[str]) -> str:
    h = hashlib.sha256()
    for d in digests:
        h.update(d.encode())
    return h.hexdigest()[:16]


def run(args: argparse.Namespace) -> Dict[str, Any]:
    header, lines = emitted(args.emit_bin, args)
    server = Server(args.server_bin, args.engine)
    try:
        client = Client(server.port)
        load_start = time.monotonic()
        errors = load(client, lines)
        load_s = time.monotonic() - load_start
        status, body, _ = client.get("/v1/stats")
        stats = json.loads(body) if status == 200 else {}
        counts = [stats.get(k) for k in ("node_count", "edge_count", "active_node_count",
                                         "enabled_edge_count", "effective_edge_count")]
        expected = [header["nodes"], header["edges"], header["nodes"], header["edges"],
                    header["edges"]]
        if counts != expected:
            errors += 1
        out: Dict[str, Any] = {"kind": "http-pages", "cell": args.cell, "engine": args.engine,
                               "workload": header["workload"], "load_s": round(load_s, 3)}
        digests: List[str] = []
        if args.cell == "p3":
            times = []
            for _kind, cursor in header["cursors"]:
                status, body, ns = client.get(
                    f"/v1/nodes/{header['hub']}/edges?limit={PAGE}&after={cursor}")
                errors += status != 200
                times.append(ns)
                digests.append(digest(body))
            out.update({"median_ns": lower_median(times), "p99_ns": nearest_rank(times, 0.99),
                        "times_ns": times})
        else:
            traversal, pages, edges_seen = 0, 0, 0
            source = target = None
            while True:
                path = f"/v1/edges?limit={PAGE}"
                if source is not None:
                    path += f"&after_source={source}"
                if target is not None:
                    path += f"&after_target={target}"
                status, body, ns = client.get(path)
                traversal += ns
                pages += 1
                if status != 200:
                    errors += 1
                    break
                digests.append(digest(body))
                page = json.loads(body)
                edges_seen += len(page["edges"])
                source, target = page["next_after_source"], page["next_after_target"]
                if source is None:
                    break
            errors += edges_seen != header["edges"]
            times = []
            for _kind, s, t in header["edge_cursors"]:
                status, body, ns = client.get(
                    f"/v1/edges?limit={PAGE}&after_source={s}&after_target={t}")
                errors += status != 200
                times.append(ns)
                digests.append(digest(body))
            out.update({"traversal_ns": traversal, "traversal_pages": pages,
                        "page_p99_ns": nearest_rank(times, 0.99),
                        "page_median_ns": lower_median(times), "times_ns": times})
        out["errors"] = errors
        out["page_digests"] = digests
        out["gate"] = {"fingerprint": header["fingerprint"], "logical": counts,
                       "pages": len(digests), "pages_digest": combined(digests)}
        return out
    finally:
        server.stop()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server-bin", required=True)
    parser.add_argument("--emit-bin", required=True)
    parser.add_argument("--engine", required=True, choices=["compact-bfs", "cluster-forest"])
    parser.add_argument("--workload", default="hub-in-sparse", choices=["hub-in-sparse"])
    parser.add_argument("--nodes", type=int, required=True)
    parser.add_argument("--degree", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--cell", choices=["p3", "p4"], required=True)
    parser.add_argument("--cursors", type=int, default=100)
    args = parser.parse_args(argv)
    args.server_bin = str(confined_executable(args.server_bin, "--server-bin"))
    args.emit_bin = str(confined_executable(args.emit_bin, "--emit-bin"))
    result = run(args)
    print(json.dumps(result))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
