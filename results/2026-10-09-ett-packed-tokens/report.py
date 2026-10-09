"""Render the bounded pilot without hiding adverse results."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
c=json.loads((H/'comparison.json').read_text());flags=[]
lines=['# ETT packed optional indices — pilot', '', 'Four private optional indices use checked index + 1 encoding. Tokens occupy', '64 instead of 96 bytes on this 64-bit target. No algorithm/API change. Candidate', 'is isolated; production ETT remains unchanged. [Protocol](protocol.md).', '', '## Before / after', '', 'Negative changes mean improvement. Runtime excludes setup; peak RSS covers the', 'whole process. Four paired processes per variant/cell; fresh and warmed are', 'separate. No answer cache or hardware cache flush.', '', '| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs | Peak RSS change | Setup change |', '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|']
for r in c['rows']:
 if not r['complete']:
  lines.append(f"Incomplete: {r}");continue
 m=r['metrics'];t=m['runtime_ns'];slower=sum(p['runtime_delta_percent']>0 for p in r['pairs'])
 if t['delta_percent']>5 and slower>=3:flags.append({k:r[k] for k in ['workload','nodes','query_percent','regime']})
 lines.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {t['before']['median']/1e6:.3f} | {t['after']['median']/1e6:.3f} | {t['delta_percent']:+.2f}% | {r['pairs_faster']}/4 | {m['rss_bytes']['delta_percent']:+.2f}% | {m['setup_ns']['delta_percent']:+.2f}% |")
lines+=['','## Decision screen','',f"Failed processes: {len(c['failed'])}. Runtime regression flags: {len(flags)}.", 'A flag means median runtime >5% slower with at least 3/4 adverse pairs; it is', 'a screening rule, not a significance test. See [comparison.json](comparison.json)', 'for all pairs, ranges and cut/link/query p50/p95/p99. No reciprocal-latency', 'throughput estimates or universal speedup claims are made.', '', '## Verification and provenance', '', '[Saved patch](candidate.patch), [build metadata](builds.json),', '[verification](verification.json), [audit](audit.json). Both binaries were built', 'from identical isolated sibling copies except for ETT forest.rs. Source hashes', 'and exact traces are checked; the harness validates answers against its oracle.', 'Process order is balanced within every cell. Historical rankings are not pooled', 'with these measurements. A favorable pilot only justifies a broader matrix.']
(H/'screen.json').write_text(json.dumps({'failed_processes':len(c['failed']),'regression_flags':flags},indent=2)+'\n')
(H/'README.md').write_text('\n'.join(lines)+'\n')
print('Flags:',flags)
