#!/usr/bin/env python3
"""D4 of the knotrel#182 BFS regression diagnosis (PROTOCOL.md): 12 alternating pairs of
``--engine compact-workspace`` on chain-split-rejoin 10k (--rounds 100, seed 42) for two
binary pairs that contain the same unchanged ``connected_with_workspace``.

    layout_control.py OUT.json NAME=OLD_BIN,NEW_BIN [...]
"""
import json
import statistics as st
import subprocess
import sys

ARGS = ["--workload", "chain-split-rejoin-v1", "--nodes", "10000", "--rounds", "100",
        "--seed", "42", "--engine", "compact-workspace", "--warmup", "1", "--repetitions", "1"]
out_path, specs = sys.argv[1], sys.argv[2:]


def run(binary):
    rep = json.loads(subprocess.run([binary] + ARGS, capture_output=True, check=True,
                                    text=True).stdout)["repetitions"][0]
    return {k: rep[k]["total_ns"] for k in ("query_true", "query_false")}


result = {}
for spec in specs:
    name, bins = spec.split("=")
    old, new = bins.split(",")
    pairs = []
    for i in range(12):
        order = [("old", old), ("new", new)] if i % 2 == 0 else [("new", new), ("old", old)]
        pair = {arm: run(b) for arm, b in order}
        pairs.append(pair)
    summary = {}
    for k in ("query_true", "query_false"):
        ratios = sorted(p["new"][k] / p["old"][k] for p in pairs)
        summary[k] = {"old_median_ms": st.median(p["old"][k] for p in pairs) / 1e6,
                      "new_median_ms": st.median(p["new"][k] for p in pairs) / 1e6,
                      "median_ratio": st.median(ratios), "ratio_r3_r10": [ratios[2], ratios[9]]}
    result[name] = {"old": old, "new": new, "pairs": pairs, "summary": summary}
    print(name, json.dumps(summary), file=sys.stderr)
json.dump(result, open(out_path, "w"), indent=1)
