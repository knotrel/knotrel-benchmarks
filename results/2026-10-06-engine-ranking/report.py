"""Render the measured ranking without averaging cross-scenario latencies."""
import json
from pathlib import Path
from collections import Counter
H=Path(__file__).resolve().parent
D=json.loads((H/'comparison.json').read_text())
rows=D['rows'];main=[r for r in rows if r['family'] in ('sparse','dense','cogentco') and r['complete']]
E=['compact-bfs','compact-workspace','ett-scan','hdt','petgraph-dfs']
N=dict(zip(E,['Compact (default)','Workspace (opt-in)','ETT (experimental)','HDT (experimental)','petgraph (external)']))
def metric(r,e,k):
 v=r['engines'][e]['metrics'][k]
 return None if v is None else v['median']
def count_table(rs):
 c=Counter(r['winner'] for r in rs)
 return ['| Engine | Wins | Share of cells | Faster than petgraph |','|---|---:|---:|---:|']+[f'| {N[e]} | {c[e]} / {len(rs)} | {100*c[e]/max(1,len(rs)):.1f}% | '+('—' if e=='petgraph-dfs' else f"{sum(metric(r,e,'runtime_ns')<metric(r,'petgraph-dfs','runtime_ns') for r in rs)} / {len(rs)}")+' |' for e in E]
lines=['# Current engine ranking — 2026-10-06','',
'This campaign compares five engines in the same executable on identical operation traces. It includes the optimized HDT implementation and the caller-owned Compact workspace. No production algorithm was changed for this campaign.','',
'## Main ranking','',f"{len(main)} of 74 planned cells are complete. Each cell has three independent process trials per engine; its score is median workload runtime. Fresh and warmed regimes count separately. Repeated-query and ten-million-node supplements do not enter this ranking. Each cell has equal weight; these percentages describe this workload selection, not market share or a universal performance score.",'']
lines+=count_table(main)
lines+=['',f"{sum(r['winner_range_separated'] for r in main)} / {len(main)} winners have all three runtimes below every competitor's three runtimes. This range check is descriptive, not a significance test.",'','## Topology and scale','', '| Scope | Cells | Compact | Workspace | ETT | HDT | petgraph |','|---|---:|---:|---:|---:|---:|---:|']
scopes=[('Sparse '+f'{n:,}',[r for r in main if r['family']=='sparse' and r['nodes']==n]) for n in (1024,10000,100000,1000000)]
scopes += [(f,[r for r in main if r['family']==f]) for f in ('dense','cogentco')]
for label,rs in scopes:
 c=Counter(r['winner'] for r in rs);lines.append(f'| {label} | {len(rs)} | '+' | '.join(str(c[e]) for e in E)+' |')
lines+=['','## Representative warmed cells','', 'Runtime is the complete measured workload in milliseconds; parentheses show the percentage above the fastest engine in that cell. These are not individual query latencies.','', '| Workload | Nodes | Query mix | Compact | Workspace | ETT | HDT | petgraph |','|---|---:|---:|---:|---:|---:|---:|---:|']
for r in main:
 if r['regime']!='warmed':continue
 if not (r['family']=='cogentco' or (r['family']=='sparse' and r['nodes'] in (100000,1000000) and r['query_percent'] in (10,90)) or (r['family']=='dense' and r['nodes']==512 and r['query_percent']==90)):continue
 lines.append(f"| {r['workload']} | {r['nodes']:,} | {r['query_percent'] if r['query_percent'] is not None else 'import'} | "+' | '.join(f"{metric(r,e,'runtime_ns')/1e6:.3f} (+{r['engines'][e]['slower_than_best_percent']:.1f}%)" for e in E)+' |')
lines+=['','## Decision and next experiment','',
'Keep the current default and explicit engine choices. ETT leads the count of wins, but Workspace beats petgraph in more cells; winner count and head-to-head coverage answer different questions. No engine dominates this matrix. The broad labels sparse/dense and vertex count alone are insufficient for an automatic selector: query mix and mutation structure also change the winner.',
'', 'Prioritize a structural profile of HDT on the preserved blocks-with-cycles traces. On the warmed one-million-node, 90% query cell, HDT takes about 3.41 seconds versus ETT 47.47 milliseconds (about 71.8 times the runtime), while HDT wins the one-million-node path at the same query ratio. This contrast makes replacement search and level promotions concrete profiling targets; it does not yet prove which internal step dominates.',
'', 'Run counters outside the timed campaign, distinguish tree/non-tree cuts, replacement candidates, promotions by level, forest updates and allocation pressure. Start at 100,000 nodes, reproduce the pattern at one million, then test one targeted change with interleaved before/after trials on exactly these traces. Retain path, dense and Cogentco controls so a blocks improvement cannot conceal regressions elsewhere. No default switch or speculative optimization is part of this ranking.']
lines+=['','## Memory and setup at one million vertices','', 'Maximum observed process RSS and maximum available cell-median setup time across the one-million-node sparse cases, including successful observations from incomplete cells. RSS includes the harness, trace, setup and warmup; it is not engine heap usage. Maxima can come from different cells.','', '| Engine | Peak process RSS (MiB) | Largest median setup (s) | Successful trials |','|---|---:|---:|---:|']
large=[r for r in rows if r['family']=='sparse' and r['nodes']==1000000]
for e in E:
 available=[r for r in large if e in r['engines']]
 if available:
  lines.append(f"| {N[e]} | {max(r['engines'][e]['metrics']['rss_bytes']['max'] for r in available)/2**20:.1f} | {max(metric(r,e,'setup_ns') for r in available)/1e9:.3f} | {sum(r['engines'][e]['trials'] for r in available)} |")
 else:lines.append(f"| {N[e]} | — | — | 0 |")
lines+=['','## Supplements','']
for f in ('repeats','extreme'):
 rs=[r for r in rows if r['family']==f and r['complete']];c=Counter(r['winner'] for r in rs)
 lines.append(f"- **{f}:** {len(rs)} complete cells; winners: "+', '.join(f"{N.get(e,'tied')} {v}" for e,v in c.items())+'.')
lines+=['', 'Repeated queries use two additional copies of each query in the 10,000-node, 90% query workload. Fresh/warmed runs do not flush hardware caches. None of these engines caches connectivity answers. At ten million nodes only Compact, Workspace and petgraph were attempted, with one trial per cell: exploratory evidence only. ETT and HDT were not attempted at that size on this shared 16 GiB host; this is a scope restriction, not an observed timeout or capacity failure.','',
'## Meaning and limits','',
'- Compact is the production default. Workspace is an opt-in, caller-owned query workspace; this result does not make it a server configuration or an automatic selector.',
'- ETT and HDT are Knotrel experimental implementations with exact connectivity semantics, not external competitors. Experimental denotes integration/maturity status, not approximate answers.',
'- petgraph 0.8.3 is the external Rust-library adapter with a fixed vertex universe, ID translation, reused DFS space and immediate mutation visibility. This is not a network-service comparison. GraphScope, Memgraph and Differential Dataflow were not measured.',
'- Synthetic sparse traces cover paths and blocks with cycles; dense traces cover bridge churn and redundant bridges. Ten rounds contain 1,000 operations. Holding this count fixed while scaling vertices changes the fraction of the graph mutated; it is not an asymptotic proof.',
'- Cogentco is one real network topology (197 vertices, 243 simple edges), with synthetic outages. It is not a fraud detector, an electrical simulation or a validation of domain semantics.',
'- Runtime is workload wall time including harness dispatch, assertions and timer sampling, excluding graph setup. Per-operation samples exclude correctness checks. Setup, operation tails and process RSS are separate in [details.md](details.md). Percentages never use reciprocal median latency as measured throughput.',
'- Trial order was shuffled deterministically, executions were sequential, and the same release binary and source hashes were required across all collections. No hardware-cache flush, CPU isolation or statistical confidence interval is claimed.',
f"- {len(D['failures'])} failed processes ({sum(bool(c.get('timed_out')) for c in D['failures'])} timeouts) are retained in [comparison.json](comparison.json); [audit.json](audit.json) reports all 1,182 attempted processes. Incomplete cells are excluded explicitly from winner counts.",
'', '## Reproduction and references','',
'Read [protocol.md](protocol.md), run the recorded collector commands, then `python3 results/2026-10-06-engine-ranking/analyze.py` then `python3 results/2026-10-06-engine-ranking/history.py` and `python3 results/2026-10-06-engine-ranking/report.py`. Collection directories ending in `-sparse`, `-dense`, `-cogentco`, `-repeats` and `-extreme` preserve manifests, commands, raw outputs, RSS logs, source/build metadata and artifact hashes. Analysis verifies every recorded artifact hash and matches trace fingerprints and actual operation/answer counts across engines.',
'', 'The [matched historical comparison](historical-comparison.md) holds the original traces and competitor set fixed when reporting changes in ordering. The [original four-engine ranking](../2026-10-04-connectivity-campaign/ranking.md), [workspace comparison](../2026-10-04-workspace-v2-comparison/README.md), [HDT join comparison](../2026-10-05-hdt-joins/README.md), [traversal-order experiment](../2026-10-05-traversal-order/README.md) and [bitset experiment](../2026-10-05-traversal-bitset/README.md) remain separate historical references. This campaign is a current ranking, not an interleaved before/after experiment; changes relative to those days cannot be attributed solely to an optimization.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
lines=['# Per-cell results','', 'All values are medians across three processes, except the one-trial extreme supplement. p95/p99 columns are medians of each process percentile, not percentiles of pooled samples. Δ Compact = `100*(runtime/Compact-1)`; negative means faster. Above best = `100*(runtime/best-1)`. Runtime/setup are milliseconds, operation tails are microseconds and RSS is MiB. Missing operations are shown as —.','']
def fmt(v,scale):return '—' if v is None else f'{v/scale:.3f}'
for r in rows:
 lines += [f"## {r['family']} / {r['workload']} / N={r['nodes']} / q={r['query_percent']} / {r['regime']}",'',f"Complete: {r['complete']}. Winner: {r['winner'] or 'none/tied'}. Fingerprint: `{r.get('fingerprint','unavailable')}`.",'']
 if not r['complete']:continue
 lines += [f"Operations: cut {r['cut_count']}, link {r['link_count']}, query {r['query_count']} ({r['query_true_count']} true / {r['query_false_count']} false), additional repeats {r['repeat_count']}.",'', '| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for e,v in r['engines'].items():
  t=v['metrics']['runtime_ns']
  tails=[' / '.join(fmt(metric(r,e,op+'_'+p+'_ns'),1000) for p in ('p95','p99')) for op in ('cut','link','connected')]
  lines.append(f"| {N[e]} | {t['median']/1e6:.3f} [{t['min']/1e6:.3f}, {t['max']/1e6:.3f}] | {v['delta_vs_compact_percent']:+.1f}% | +{v['slower_than_best_percent']:.1f}% | {metric(r,e,'setup_ns')/1e6:.3f} | {metric(r,e,'rss_bytes')/2**20:.1f} | "+' | '.join(tails)+' |')
 lines.append('')
(H/'details.md').write_text('\n'.join(lines)+'\n')
