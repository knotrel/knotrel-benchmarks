"""D5c summary: probe revision 4 background-import accounting of c64-import per run."""
import json, glob, os, sys
for p in sorted(glob.glob(f"{sys.argv[1]}/run*-*.stdout")):
    for l in open(p):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if r.get("kind") == "start":
            rev = r.get("probe_revision")
        if r.get("config", {}).get("id") != "read100-b8-c64-import":
            continue
        b = r["background"]; i = b.get("imports", {})
        print(f"{os.path.basename(p):18s} rev {rev} | attempted {i.get('imports_attempted')} completed {i.get('imports_completed')} | 412 {i.get('precondition_412')} retries {i.get('retries')} after-refresh {i.get('precondition_after_refresh')} | stats attempts {i.get('stats_attempts')} refused {i.get('stats_refused_503')} | exhausted {i.get('refresh_exhausted')} (deadline {i.get('refresh_exhausted_deadline')}, attempts {i.get('refresh_exhausted_attempts')}) failed-status {i.get('refresh_failed_status')} | refresh p50/max {i.get('refresh_latency_p50_ns',0)/1e6:.1f}/{i.get('refresh_latency_max_ns',0)/1e6:.1f} ms | import p50/max {b['p50_ns']/1e6:.0f}/{b['max_ns']/1e6:.0f} ms | failures {b['failures']} {b['failure_kinds']} | starved {i.get('import_starved')}")
