"""D3c summary (DIAGNOSTICS-PLAN-3.md): per-arm medians, the declared fidelity check, and the
descriptive ratios L/P and L/PP with the frozen order-statistic interval at n = 24."""
import json, math, statistics as st, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
setup = rows[0]; pairs = [r for r in rows[1:] if not r["warmup"]]
n = len(pairs); med = st.median
print(f"pairs {n}; ops: lifecycle {setup['lifecycle_ops']}, plain {setup['plain_ops']}; requests {setup['lifecycle_requests']} / {setup['plain_requests']}")
def arm(a, key): return [p["arms"][a][key] for p in pairs]
def cnt(a, i): return [p["arms"][a]["counters"][i] for p in pairs]
us = lambda v: med(v) / 1e3
for a in ("L", "P", "PP"):
    extra = f", planning {us(arm(a, 'planning_ns')):.1f}" if a == "PP" else ""
    print(f"{a:3s} window {us(arm(a, 'window_ns')):9.1f} us | apply {us(cnt(a, 0)):8.1f} | in-call {us(cnt(a, 1)):8.1f} | handling (apply - in-call) {us([x - y for x, y in zip(cnt(a, 0), cnt(a, 1))]):8.1f} | ops/window {med(cnt(a, 2)):.0f}{extra}")
print(f"core-L per-call {us(arm('core-L', 'per_call_ns')):.1f} us; core-P per-call {us(arm('core-P', 'per_call_ns')):.1f} us")
print("Fidelity check 1 (core per-call within +-10% of server in-call, medians):")
ok1 = True
for core, server in (("core-L", "L"), ("core-P", "P")):
    c, s = med(arm(core, "per_call_ns")), med(cnt(server, 1)); dev = c / s - 1; ok = abs(dev) <= 0.10; ok1 &= ok
    print(f"  {core} {c/1e3:.1f} vs {server} in-call {s/1e3:.1f} us: {dev*100:+.1f}% -> {'within' if ok else 'OUTSIDE'}")
apply_d = med(cnt("L", 0)) - med(cnt("P", 0)); incall_d = med(cnt("L", 1)) - med(cnt("P", 1))
hand_d = med([x - y for x, y in zip(cnt("L", 0), cnt("L", 1))]) - med([x - y for x, y in zip(cnt("P", 0), cnt("P", 1))])
resid = apply_d - incall_d - hand_d; ok2 = abs(resid) <= 0.10 * abs(apply_d)
print(f"Fidelity check 2: apply difference {apply_d/1e3:+.1f} us = in-call {incall_d/1e3:+.1f} + handling {hand_d/1e3:+.1f}; residual {resid/1e3:+.1f} us ({resid/apply_d*100:+.1f}% of the apply difference) -> {'within 10%' if ok2 else 'OUTSIDE 10%'}")
print(f"FIDELITY: {'RESTORED' if ok1 and ok2 else 'NOT RESTORED'}")
def ratio(x, y):
    r = sorted(math.log(a / b) for a, b in zip(arm(x, "window_ns"), arm(y, "window_ns")))
    pct = lambda v: (math.exp(v) - 1) * 100
    lo, hi = (r[6], r[17]) if n == 24 else (r[0], r[-1])
    return f"median {pct(st.median(r)):+.2f}% [r(7) {pct(lo):+.2f}%, r(18) {pct(hi):+.2f}%] (pair min {pct(r[0]):+.2f}%, max {pct(r[-1]):+.2f}%)"
print(f"L/P  (frozen reference, planning untimed): {ratio('L', 'P')}")
print(f"L/PP (planner in the window):              {ratio('L', 'PP')}")
print("Descriptive only: no verdict; the future cell is evaluated only in qualification 3.")
