"""D3b summary: whole-window replay times, per-type time (median over replays of per-type
sums) and work counters per type (deterministic)."""
import json, statistics as st, sys
D = sys.argv[1]
rows = [json.loads(l) for l in open(f"{D}/time.jsonl")]
setup = rows[0]; reps = [r for r in rows[1:] if not r["warmup"]]
L = [r["window_ns"]["lifecycle"] / 1e3 for r in reps]; P = [r["window_ns"]["plain"] / 1e3 for r in reps]
q = [a / b for a, b in zip(L, P)]; d = [a - b for a, b in zip(L, P)]
print(f"ops: lifecycle {setup['lifecycle_ops']}, plain {setup['plain_ops']}; replays {len(reps)}")
print(f"whole window (uninstrumented): lifecycle {st.median(L):.1f} us, plain {st.median(P):.1f} us; ratio {st.median(q):.3f} ({min(q):.3f}-{max(q):.3f}); difference {st.median(d):+.1f} us ({min(d):+.1f} to {max(d):+.1f})")
cnt = {r["arm"]: r["per_type"] for r in map(json.loads, open(f"{D}/counters.jsonl")) if r["kind"] == "counters"}
names = ["engine_link", "engine_cut", "engine_shift_elems", "engine_new_vertex", "incident_scanned", "neighbor_catalog_probes", "incident_shift_elems", "incident_binary_searches", "compactions", "compaction_vertices"]
tot_time = {}
for arm in ("lifecycle", "plain"):
    kinds = sorted({k for r in reps for k in r["per_op"][arm]})
    timed_total = st.median(sum(v["ns"] for v in r["per_op"][arm].values()) / 1e3 for r in reps)
    tot_time[arm] = timed_total
    print(f"\n[{arm}] per-op pass total (one clock read per op): {timed_total:.1f} us")
    print(f"  {'type':26s} {'count':>6s} {'no-op':>6s} {'time us':>9s} {'ns/op':>7s} | " + " ".join(f"{n[:14]:>14s}" for n in names))
    for k in kinds:
        c = reps[0]["per_op"][arm][k]["count"]; noop = reps[0]["per_op"][arm][k]["noop"]
        t = st.median(r["per_op"][arm][k]["ns"] for r in reps) / 1e3
        w = cnt[arm][k]["counters"]
        print(f"  {k:26s} {c:6d} {noop:6d} {t:9.1f} {t*1e3/c:7.0f} | " + " ".join(f"{w[n]:14d}" for n in names))
    tw = {n: sum(cnt[arm][k]["counters"][n] for k in cnt[arm]) for n in names}
    print(f"  {'TOTAL':26s} {'':6s} {'':6s} {'':9s} {'':7s} | " + " ".join(f"{tw[n]:14d}" for n in names))
