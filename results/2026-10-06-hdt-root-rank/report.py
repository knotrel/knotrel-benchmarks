"""Render the paired single-pass lookup experiment."""
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;d=json.loads((H/'comparison.json').read_text());rows=d['rows'];complete=[r for r in rows if r['complete']]
lines=['# HDT single-pass root/rank experiment — 2026-10-06','',
'`reroot` previously walked parent links once to find the tour root and again to compute the token rank. The candidate returns both from one read-only walk. It preserves split/concat and the exact tour sequence, and does not include the earlier rank-zero shortcut. [candidate.patch](candidate.patch) and the full before/after forest files are retained in this checkout.','',
f"{len(complete)} / 38 cells complete; {len(d['failed'])} / 304 timed processes failed. Each cell has four sequential before/after pairs, two in each execution order. Pairs were shuffled with seed42. Fresh and warmed runs remain separate; hardware caches were not flushed. The warmed run replays a fresh graph after one untimed warmup.", '',
'## Runtime results','', '| Family | Complete cells | Faster cells | Median cell change | Cell change range |','|---|---:|---:|---:|---:|']
for f in ('sparse','dense','cogentco'):
 rs=[r for r in complete if r['family']==f];ds=[r['metrics']['runtime_ns']['delta_percent'] for r in rs]
 if ds:lines.append(f"| {f} | {len(rs)} | {sum(x<0 for x in ds)} | {statistics.median(ds):+.2f}% | {min(ds):+.2f}% to {max(ds):+.2f}% |")
lines+=['', 'Negative change means lower runtime: `100*(after/before-1)`. These are per-cell median workload wall times, excluding setup but including harness checking and sampling. The median of cell changes is descriptive, not an aggregate throughput gain. Four pairs do not establish a statistical confidence interval.','',
'| Workload | Vertices | Query mix | Regime | Before ms | After ms | Change | Faster pairs / 4 | Setup change | RSS change |','|---|---:|---:|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
 if not r['complete']:
  lines.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | incomplete | — | — | — | — | — |");continue
 m=r['metrics'];t=m['runtime_ns'];lines.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {t['before']['median']/1e6:.3f} | {t['after']['median']/1e6:.3f} | {t['delta_percent']:+.2f}% | {r['pairs_faster']} | {m['setup_ns']['delta_percent']:+.2f}% | {m['rss_bytes']['delta_percent']:+.2f}% |")
lines+=['','## Correctness and structural evidence','',
'The isolated candidate passed complete core tests/doctests and an additional lookup test that enumerates the tour in order independently, checking every live vertex/arc token after singleton registration, links, cuts, relinks and mark updates. The before source fails that new test to compile because the fused helper does not exist; the after source passes. This is an API-availability red check, not an observed correctness failure in the original implementation. See candidate-test.rs.txt and test-results.json.','',
'Structural probes on preserved 100k/1M block traces with 90% queries run separately from timing, twice per variant per trace. [structural-comparison.json](structural-comparison.json) checks that promotion counts by level, forest restructuring calls and endpoint materialization are unchanged, while comparing parent steps. These counters cannot be interpreted as runtime shares.','',
'## Reproduction and preservation','',
'Run build.py, test.py and collect.py in a fresh result destination, then analyze.py and report.py. Probe scripts are in the sibling before-probe and after-probe directories; run them after timings, then structural-comparison.py. Collectors refuse to overwrite completed results. Both temporary builds copy toolchain pins and use identical Rust/Cargo inputs except the candidate forest. Source-isolation-audit.json checks these inputs and the compiler. Manifests retain commands, hashes, raw outputs, failures and whole-process RSS, which is not engine-only heap.','',
'Analysis verifies fingerprints, answer counts, mutation counts and paired HDT counters. Operation percentiles, setup, RSS and paired directions are preserved in [comparison.json](comparison.json); percentile summaries are not pooled samples. No failed process is silently omitted from the report.','',
'The [candidate inventory](../../docs/experiments/2026-10-06-hdt-candidates.md) preserves the previous rank-zero patch separately with its SHA-256. The [current five-engine ranking](../2026-10-06-engine-ranking/README.md) remains the historical timing reference; no inter-day performance claim is inferred from it. See [decision.md](decision.md) for the integration decision and remaining limitations.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
