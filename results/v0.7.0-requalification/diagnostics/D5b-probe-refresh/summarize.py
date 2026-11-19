"""D5b summary: background-import accounting of the c64-import configuration per run."""
import json, glob, os, sys
D = sys.argv[1]
for p in sorted(glob.glob(f"{D}/run*-*.stdout")):
    for l in open(p):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if r.get("config", {}).get("id") != "read100-b8-c64-import":
            continue
        b = r["background"]; i = b.get("imports", {})
        print(f"{os.path.basename(p):22s} completed {b['completed']} failures {b['failures']} refused_503 {b['refused_503']} kinds {b['failure_kinds']} | "
              f"attempted {i.get('imports_attempted')} 412 {i.get('precondition_412')} retries {i.get('retries')} after-refresh {i.get('precondition_after_refresh')} | "
              f"stats attempts {i.get('stats_attempts')} refused {i.get('stats_refused_503')} refreshes {i.get('refreshes')} exhausted {i.get('refresh_exhausted')} "
              f"refresh p50/max {i.get('refresh_latency_p50_ns',0)/1e6:.1f}/{i.get('refresh_latency_max_ns',0)/1e6:.1f} ms | import p50/max {b['p50_ns']/1e6:.0f}/{b['max_ns']/1e6:.0f} ms | starved {i.get('import_starved')}")
