"""D2b import cost: paired import-time ratios (variant/frozen) and post-import net heap."""
import json, statistics, sys
D = sys.argv[1]
heap = {r["variant"]: r["net_heap_bytes"] for r in map(json.loads, open(f"{D}/import-heap.jsonl"))}
pairs = [r for r in map(json.loads, open(f"{D}/import-time.jsonl")) if not r["warmup"]]
print("variant    import time frozen/variant median ms | ratio variant/frozen median (pair min-max) | post-import net heap MiB (delta vs frozen)")
print(f"{'frozen':10s} {'':41s} | {'':41s} | {heap['frozen']/1048576:.2f}")
for v in [k for k in heap if k != "frozen"]:
    p = [r for r in pairs if r["variant"] == v]
    f = statistics.median(r["ns"]["frozen"] for r in p) / 1e6; x = statistics.median(r["ns"]["variant"] for r in p) / 1e6
    q = [r["ns"]["variant"] / r["ns"]["frozen"] for r in p]
    print(f"{v:10s} {f:8.2f} / {x:8.2f} (n={len(p)}){'':17s} | {statistics.median(q):.3f} ({min(q):.3f}-{max(q):.3f}){'':20s} | {heap[v]/1048576:.2f} ({(heap[v]-heap['frozen'])/1048576:+.2f})")
