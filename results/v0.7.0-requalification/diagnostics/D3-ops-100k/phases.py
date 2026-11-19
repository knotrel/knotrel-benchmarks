"""D3/D4 phase summary from an instrumented http-lifecycle run (median over analyzed pairs)."""
import json, statistics, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
pairs = {r["pair"]: r for r in rows if r.get("kind") == "pair"}
ph = {r["index"]: r for r in rows if r.get("kind") == "d3_phases"}
warm = sum(1 for r in rows if r.get("kind") == "warmup")
keys = ["handler_ns", "exec_await_ns", "queue_hop_ns", "lock_wait_ns", "work_ns", "apply_ns", "post_work_ns", "serialize_ns"]
cand = {k: [] for k in keys + ["window_ns", "outside_handler_ns", "dispatch_ns"]}; ref = {k: [] for k in cand}
ratio = []
for p, r in pairs.items():
    x = ph[p + warm]
    ratio.append(r["candidate_ns"] / r["reference_ns"])
    for arm, out, w in (("candidate", cand, r["candidate_ns"]), ("reference", ref, r["reference_ns"])):
        v = x[arm]
        for k in keys: out[k].append(v[k])
        out["window_ns"].append(w)
        out["outside_handler_ns"].append(w - v["handler_ns"])       # router, body parse, extractor, probe loop
        out["dispatch_ns"].append(v["exec_await_ns"] - v["work_ns"])  # admission, blocking hop, lock, post-work, join
ops = (ph[warm]["candidate"]["operations"], ph[warm]["reference"]["operations"], ph[warm]["candidate"]["requests"], ph[warm]["reference"]["requests"])
print(f"pairs {len(pairs)}; median window ratio candidate/reference {statistics.median(ratio):.3f} (min {min(ratio):.3f}, max {max(ratio):.3f})")
print(f"operations per window: candidate {ops[0]}, reference {ops[1]}; requests {ops[2]} / {ops[3]}")
print(f"{'phase (median per window, us)':34s} {'candidate':>10s} {'reference':>10s} {'diff':>9s}  share of window diff")
md = statistics.median(cand["window_ns"]) - statistics.median(ref["window_ns"])
for k in ["window_ns", "outside_handler_ns", "handler_ns", "exec_await_ns", "dispatch_ns", "queue_hop_ns", "lock_wait_ns", "work_ns", "apply_ns", "post_work_ns", "serialize_ns"]:
    c, r_ = statistics.median(cand[k]), statistics.median(ref[k])
    print(f"  {k:32s} {c/1e3:10.1f} {r_/1e3:10.1f} {(c-r_)/1e3:+9.1f}  {((c-r_)/md*100 if md else 0):6.1f}%")
