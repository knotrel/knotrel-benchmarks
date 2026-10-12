#!/usr/bin/env python3
"""Run a comprehensive performance evaluation comparing Knotrel engines against petgraph.

Covers:
- Sparse topologies (Chain, Cycle, Components, Hub with 10k nodes)
- Dense topologies (Dense bridge churn, Redundant bridge churn with 128 and 512 nodes)
- Sustained churn topologies (Path and Blocks with varying query percentages)
- Real-world topology (Cogentco from Internet Topology Zoo)
"""

import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/release/knotrel-benchmarks"
COGENTCO = Path("/private/tmp/knotrel-ett-cogentco-fp7hmtgr/cogentco.trace.json")

ENGINES = ["compact-bfs", "compact-workspace", "ett-scan", "hdt", "petgraph-dfs"]

CASES = [
    # Real-world
    {
        "category": "Real-World Topology",
        "name": "Cogentco (197 nodes, 243 links, real outage churn)",
        "args": ["--trace-in", str(COGENTCO), "--repetitions", "3", "--warmup", "1"],
    },
    # Sparse 10k
    {
        "category": "Sparse Topologies (N=10,000)",
        "name": "Chain Split/Rejoin (N=10k, 1k rounds)",
        "args": ["--workload", "chain-split-rejoin-v1", "--nodes", "10000", "--rounds", "1000", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Sparse Topologies (N=10,000)",
        "name": "Cycle Alternatives (N=10k, 1k rounds)",
        "args": ["--workload", "cycle-alternatives-v1", "--nodes", "10000", "--rounds", "1000", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Sparse Topologies (N=10,000)",
        "name": "Components Join/Split (N=10k, 1k rounds)",
        "args": ["--workload", "components-join-split-v1", "--nodes", "10000", "--rounds", "1000", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Sparse Topologies (N=10,000)",
        "name": "Hub Alternatives (N=10k, 1k rounds)",
        "args": ["--workload", "hub-alternatives-v1", "--nodes", "10000", "--rounds", "1000", "--repetitions", "3", "--warmup", "1"],
    },
    # Dense
    {
        "category": "Dense Topologies (Bridge Churn)",
        "name": "Dense Bridge Churn (N=512, q=10%)",
        "args": ["--workload", "dense-bridge-churn-v1", "--nodes", "512", "--rounds", "100", "--query-percent", "10", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Dense Topologies (Bridge Churn)",
        "name": "Dense Bridge Churn (N=512, q=50%)",
        "args": ["--workload", "dense-bridge-churn-v1", "--nodes", "512", "--rounds", "100", "--query-percent", "50", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Dense Topologies (Bridge Churn)",
        "name": "Dense Bridge Churn (N=512, q=90%)",
        "args": ["--workload", "dense-bridge-churn-v1", "--nodes", "512", "--rounds", "100", "--query-percent", "90", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Dense Topologies (Bridge Churn)",
        "name": "Redundant Bridge Churn (N=512, q=50%)",
        "args": ["--workload", "redundant-bridge-churn-v1", "--nodes", "512", "--rounds", "100", "--query-percent", "50", "--repetitions", "3", "--warmup", "1"],
    },
    # Sustained
    {
        "category": "Sustained Workloads",
        "name": "Sustained Churn Path (N=1k, q=10%)",
        "args": ["--workload", "sustained-churn-path-v1", "--nodes", "1000", "--rounds", "100", "--query-percent", "10", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Sustained Workloads",
        "name": "Sustained Churn Path (N=1k, q=50%)",
        "args": ["--workload", "sustained-churn-path-v1", "--nodes", "1000", "--rounds", "100", "--query-percent", "50", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Sustained Workloads",
        "name": "Sustained Churn Path (N=1k, q=90%)",
        "args": ["--workload", "sustained-churn-path-v1", "--nodes", "1000", "--rounds", "100", "--query-percent", "90", "--repetitions", "3", "--warmup", "1"],
    },
    {
        "category": "Sustained Workloads",
        "name": "Sustained Churn Blocks (N=1k, q=50%)",
        "args": ["--workload", "sustained-churn-blocks-v1", "--nodes", "1000", "--rounds", "100", "--query-percent", "50", "--repetitions", "3", "--warmup", "1"],
    },
]

def run_case(case):
    engine_arg = ",".join(ENGINES)
    cmd = [str(BINARY), "--engine", engine_arg] + case["args"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    
    engine_results = {}
    for entry in data["comparisons"]:
        eng_raw = entry["engine"]
        # Normalize engine name
        if "compact-bfs" in eng_raw:
            eng = "compact-bfs"
        elif "compact-workspace" in eng_raw:
            eng = "compact-workspace"
        elif "ett" in eng_raw:
            eng = "ett-scan"
        elif "hdt" in eng_raw:
            eng = "hdt"
        elif "petgraph" in eng_raw:
            eng = "petgraph-dfs"
        else:
            eng = eng_raw
            
        wall_times = [rep["workload_wall_ns"] / 1e6 for rep in entry["repetitions"]]
        med_wall = statistics.median(wall_times)
        
        # Operation p50s
        last_rep = entry["repetitions"][-1]["measurements"]
        p50_conn = last_rep.get("connected", {}).get("p50_ns")
        p50_link = last_rep.get("link", {}).get("p50_ns")
        p50_cut = last_rep.get("cut", {}).get("p50_ns")
        
        engine_results[eng] = {
            "wall_ms": med_wall,
            "p50_conn_ns": p50_conn,
            "p50_link_ns": p50_link,
            "p50_cut_ns": p50_cut,
        }
    return engine_results

def main():
    print("=" * 80)
    print("KNOTREL vs COMPETITOR PERFORMANCE EVALUATION")
    print(f"Engines: {', '.join(ENGINES)}")
    print("=" * 80)
    
    all_results = []
    for i, case in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] Running: {case['name']}...", flush=True)
        results = run_case(case)
        all_results.append({
            "category": case["category"],
            "name": case["name"],
            "results": results,
        })
        
    print("\n" + "=" * 115)
    print(f"{'Workload':<42} | {'Compact':<9} | {'Workspace':<9} | {'ETT':<9} | {'HDT':<9} | {'Petgraph':<9} | {'Winner':<10} | {'Speedup'}")
    print("-" * 115)
    
    knotrel_wins = 0
    total_cases = len(all_results)
    speedups = []
    
    for r in all_results:
        res = r["results"]
        c_bfs = res.get("compact-bfs", {}).get("wall_ms", 0)
        c_wrk = res.get("compact-workspace", {}).get("wall_ms", 0)
        ett = res.get("ett-scan", {}).get("wall_ms", 0)
        hdt = res.get("hdt", {}).get("wall_ms", 0)
        pet = res.get("petgraph-dfs", {}).get("wall_ms", 0)
        
        knotrel_times = {
            "Compact": c_bfs,
            "Workspace": c_wrk,
            "ETT": ett,
            "HDT": hdt,
        }
        best_knotrel_name = min(knotrel_times, key=knotrel_times.get)
        best_knotrel_time = knotrel_times[best_knotrel_name]
        
        if best_knotrel_time < pet:
            knotrel_wins += 1
            winner = best_knotrel_name
            speedup = pet / best_knotrel_time
            speedup_str = f"{speedup:.2f}x faster"
        else:
            winner = "Petgraph"
            speedup = best_knotrel_time / pet
            speedup_str = f"{speedup:.2f}x slower"
            
        speedups.append(pet / best_knotrel_time)
        
        print(f"{r['name']:<42} | {c_bfs:7.2f}ms | {c_wrk:7.2f}ms | {ett:7.2f}ms | {hdt:7.2f}ms | {pet:7.2f}ms | {winner:<10} | {speedup_str}")
        
    print("=" * 115)
    geomean_speedup = statistics.geometric_mean(speedups)
    print(f"SUMMARY: Knotrel won {knotrel_wins} / {total_cases} workloads ({knotrel_wins/total_cases*100:.1f}%)")
    print(f"Geometric Mean Speedup over Petgraph: {geomean_speedup:.2f}x")
    print("=" * 115)

    # Save output json
    out_file = ROOT / "results/perf_evaluation_latest.json"
    out_file.write_text(json.dumps(all_results, indent=2))
    print(f"Full metrics saved to {out_file}")

if __name__ == "__main__":
    main()
