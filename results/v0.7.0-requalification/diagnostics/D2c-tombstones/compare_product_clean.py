"""Addendum 1, A3 (clean checkouts): the product T1 (frozen probe, stats_alloc) against the diagnostic T1 (cap).
Every checkpoint's net_heap_bytes, logical counts and catalog/engine counts must be equal."""
import json, sys
D = sys.argv[1]
def cps(p): return [r for r in map(json.loads, open(p)) if r.get("kind") == "checkpoint"]
ok = True
pairs = [(f"product-clean/{t}-30.jsonl", f"{t}-30-T1.jsonl") for t in ("sparse", "ring", "hub")]
pairs += [(f"product-clean/{t}-6000.jsonl", f"{t}-6000-T1.jsonl") for t in ("sparse", "ring", "hub")]
pairs += [(f"product-clean/B5-lifecycle-{t}.jsonl", f"B5-lifecycle-{t}-T1.jsonl") for t in ("sparse", "hub")]
for prod, diag in pairs:
    a, b = cps(f"{D}/{prod}"), cps(f"{D}/{diag}")
    heap = [x["net_heap_bytes"] for x in a] == [x["net_heap_bytes"] for x in b]
    counts = [x["counts"] for x in a] == [x["counts"] for x in b]
    exp = all(x["counts"]["logical"] == x["expected"] for x in a)
    ok &= heap and counts and exp
    print(f"{prod:32s} vs {diag:28s} checkpoints {len(a)}/{len(b)} net_heap identical {heap} counts identical {counts} model {exp}")
print("A3:", "REPRODUCED (byte for byte)" if ok else "NOT REPRODUCED")
