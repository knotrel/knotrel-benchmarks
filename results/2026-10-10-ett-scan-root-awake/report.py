"""Publish the fixed-budget confirmation with an explicit environmental gate."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
x=json.loads((H/'comparison.json').read_text());e=json.loads((H/'environment.json').read_text())
valid=e['collector_exit_code']==0 and e['no_sleep_observed'] and not x['failed'] and all(r['complete'] for r in x['rows'])
lines=['# ETT scan-root awake-host confirmation','',
'Exact frozen binaries from the [original pilot](../2026-10-10-ett-scan-root/README.md).',
'This campaign preserves the [sleep-affected confirmation](../2026-10-10-ett-scan-root-regression/README.md).',
'Twelve matched pairs per cell, six AB and six BA, 72 sequential processes.',
'No rebuild, source change, cache flush or petgraph rerun. [Protocol](protocol.md).','',
f'Collection: {e["start_utc"]} to {e["end_utc"]}.',
f'No sleep observed: **{e["no_sleep_observed"]}**. Successful complete campaign: **{valid}**.',
'Process-scoped `caffeinate -is` assertions were captured at both boundaries.',
'The inhibitor ends with collection. [Environment](environment.json) and [power events](power-events.txt).',
'No observed sleep does not guarantee CPU isolation or identical cache state.','',
'| Case | Before ms | After ms | Runtime change | Faster pairs | Setup change | RSS change | Flag |',
'|---|---:|---:|---:|---:|---:|---:|---|']
for r in x['rows']:
 if not r['complete']:lines.append(f'Incomplete: {r["reference"]}');continue
 m=r['metrics'];v=m['runtime_ns']['median'];name=Path(r['reference']).stem
 lines.append(f'| {name} | {v["before"]/1e6:.3f} | {v["after"]/1e6:.3f} | {m["runtime_ns"]["change_percent"]:+.2f}% | {r["faster_pairs"]}/12 | {m["setup_ns"]["change_percent"]:+.2f}% | {m["process_maximum_resident_set_size"]["change_percent"]:+.2f}% | {r["flag"]} |')
lines+=['','A screening flag requires >5% median runtime increase and at least 8/12 adverse pairs.',
'This is not a significance test. All failures, outliers and paired values are retained in',
'[comparison.json](comparison.json), with operation totals/tails and whole-process resources.',
'Whole-process resource counts include construction, warmup and destruction; they cannot',
'attribute a replay-local slowdown to scheduling, page faults or compiler layout.','',
'## Structural and provenance checks','',
'Both repeated structural path runs and complete before/after outputs match exactly.',
'No candidate edges are scanned on the path. Root counters match the prior diagnosis.',
'Analysis checks trace fingerprints, reference answer/operation counts, unchanged forest',
'stats, raw artifact hashes and balanced engine order. The collector verifies frozen binary',
'hashes before every run. Production code was not modified; the previous full candidate',
'workspace checks remain historical evidence and were not rerun for this measurement-only task.',
'','Reproduce: `python3 analyze.py` then `python3 report.py`. No automatic core integration.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
print('Environmental validity:',valid)
