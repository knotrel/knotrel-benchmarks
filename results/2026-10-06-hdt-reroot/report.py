"""Render complete cells and expose failure counts without filtering regressions."""
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;data=json.loads((H/'comparison.json').read_text());rows=data['rows'];complete=[r for r in rows if r['complete']]
lines=['# HDT rank-zero reroot experiment — 2026-10-06','',
'An isolated candidate returns the existing tour when `reroot` computes rank zero, avoiding an unnecessary split/concat. The in-order sequence is already correct, so keeping its AVL structure preserves connectivity, sizes and incidence aggregates. [candidate.patch](candidate.patch) is the only algorithm change between the two builds.','',
'The [structural probe](../2026-10-06-hdt-reroot-probe/results.json) finds 212,366 rank-zero calls among 424,544 promotion reroots at 100k vertices, and 2,279,820 among 4,559,450 at 1M (both block traces, 90% queries). Roughly half the calls qualify, but this does not imply halving runtime: trivial tours already cost little.','',
f"## Paired results\n\n{len(complete)} / 38 cells complete; {len(data['failed'])} / 228 processes failed. Each cell uses three sequential pairs, with alternating before/after execution order and a seeded shuffle. Negative runtime change means improvement. Runtime excludes setup; per-operation timing includes timer granularity. Fresh/warmed are separate cells, without hardware-cache flushing.", '',
'| Family | Cells | Faster cells | Median of cell changes | Range of cell changes |','|---|---:|---:|---:|---:|']
for f in ('sparse','dense','cogentco'):
 rs=[r for r in complete if r['family']==f];ds=[r['metrics']['runtime_ns']['delta_percent'] for r in rs]
 if ds:lines.append(f"| {f} | {len(rs)} | {sum(v<0 for v in ds)} | {statistics.median(ds):+.2f}% | {min(ds):+.2f}% to {max(ds):+.2f}% |")
lines+=['','A median of percentage changes describes this selected matrix, not an aggregate throughput gain. Three pairs are a screening experiment, not a confidence interval. Setup, tails and RSS remain separate in [comparison.json](comparison.json). Whole-process RSS includes the trace and harness, not only engine storage.','',
'## Every scenario','', '| Workload | Vertices | Query mix | Regime | Before ms | After ms | Runtime change | Faster pairs / 3 | Setup change | RSS change |','|---|---:|---:|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
 if not r['complete']:
  lines.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | incomplete | — | — | — | — | — |");continue
 m=r['metrics'];t=m['runtime_ns'];lines.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {t['before']['median']/1e6:.3f} | {t['after']['median']/1e6:.3f} | {t['delta_percent']:+.2f}% | {r['pairs_faster']} | {m['setup_ns']['delta_percent']:+.2f}% | {m['rss_bytes']['delta_percent']:+.2f}% |")
lines+=['','## Audit and reproduction','',
'Both optimized binaries were built in the same temporary workspace with the same Cargo configuration and compiler, changing only the HDT forest source. Neither contains the structural probe instrumentation. The temporary copies omit the toolchain pin files; the effective compiler was independently verified after building as the same Rust 1.98.1 (see source-isolation-audit.json). All Rust/Cargo files match the preserved snapshot except the candidate forest. Build commands, relevant build environment and binary hashes are in [builds.json](builds.json); complete original source hashes point to the preserved current-ranking snapshot. The candidate core passed its unit/integration tests and doctests before measurement; [candidate-tests.txt](candidate-tests.txt) retains the output.','',
'Commands and all raw results are in [manifest.json](manifest.json). Every successful replay checks the workload oracle. Analysis verifies artifact hashes, trace fingerprints, actual mutation/query counts and answer counts, and equal HDT counters between paired variants. Collection preserves failures; incomplete cells are not ranked. Production sources were unchanged throughout collection.','',
'Reproduce in a new destination by running build.py, collect.py, analyze.py, then report.py. Build and final collection outputs refuse overwrite. The preserved [five-engine ranking](../2026-10-06-engine-ranking/README.md) and [promotion diagnosis](../2026-10-06-hdt-blocks-profile/README.md) remain reference results. See [decision.md](decision.md) for the decision after reviewing this experiment.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
