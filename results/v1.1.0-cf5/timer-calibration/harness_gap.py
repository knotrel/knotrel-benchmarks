import json, subprocess, sys
def run(binary, engine, workload, nodes, rounds):
    out = subprocess.run([binary, "--workload", workload, "--nodes", str(nodes), "--rounds", str(rounds),
                          "--seed", "42", "--engine", engine, "--warmup", "1", "--repetitions", "1"],
                         capture_output=True, text=True, check=True).stdout
    r = json.loads(out)["repetitions"][0]
    m = r["measurements"]
    k = sum(v["count"] for v in m.values() if isinstance(v, dict) and "count" in v)
    s = sum(v["total_ns"] for v in m.values() if isinstance(v, dict) and "total_ns" in v)
    rq = r.get("repeated_queries")
    if rq: k += rq["count"]; s += rq["total_ns"]
    return k, r["workload_wall_ns"], s
binary, engine = sys.argv[1], sys.argv[2]
for spec in sys.argv[3:]:
    w, n, rd = spec.split(":")
    gaps = []
    for _ in range(5):
        k, wall, s = run(binary, engine, w, int(n), int(rd))
        gaps.append((wall - s) / k)
    print(f"{binary.split('/targets/')[1]:45s} {engine:22s} {w:28s} n={n:>6} k={k:6d} gap/op min {min(gaps):6.1f} max {max(gaps):6.1f} ns")
