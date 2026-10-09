"""Document the predeclared screen and all process-level observations."""
import ast,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
AA=json.loads((H/'AA/assessment.json').read_text());AB=json.loads((H/'AB/assessment.json').read_text()) if (H/'AB/assessment.json').exists() else None
lines=['# HDT repeated-replay measurement study','','## Decision','']
if not AA['screen_passed']:lines+=['A/A did not meet the predeclared all-cell ±5% screen. A/B was not started. Aggregating separate replay intervals has not demonstrated sufficiently stable behavior under this screen. Do not integrate or alter the candidate based on this run.']
else:lines+=['A/A met the predeclared screen. This allowed the exploratory A/B stage; it does not prove that noise is bounded by 5% or establish equivalence.']
lines+=['','## Method','','Use existing repetitions in the exact frozen binaries: 16 replays/process for path100k,q50 (one initial warmup) and path1M,q90 (zero initial warmups), 2 for blocks1M,q90 (one initial warmup). Each replay rebuilds its own graph and excludes setup from workload time; only one graph is live. No Rust code, trace or rounds changes.','','This aggregates **separate timed intervals**, not one continuous long interval. Process and allocator caches can carry across rebuilt graphs, so the regime differs from the original single-replay fresh/warmed tests. Every replay retains the same trace fingerprint, oracle answers, operation counts and HDT counters. Workload wall time still includes checking/timing/harness overhead. Setup, individual replays and whole-process RSS are preserved.','','Four balanced pairs per cell/stage; process mean is sum of workload times divided by replay count. The process remains the observation unit. Do not treat internal replays as independent trials or pool latency percentiles. [Protocol](protocol.md).','','| Stage | Cell | Left mean-replay median ms | Right mean-replay median ms | Change | First-replay change | Sum replay median left/right ms | Slower pairs |','|---|---:|---:|---:|---:|---:|---:|---:|']
audit=[]
for d in (AA,AB):
 if d is None:continue
 stage=d['mode'];m=json.loads((H/stage/'manifest.json').read_text());assert hashes()==m['builds']['original_source_sha256']
 assert hashlib.sha256((H/'collect.py').read_bytes()).hexdigest()==m['collector_sha256']
 assert hashlib.sha256((H/'protocol.md').read_bytes()).hexdigest()==m['protocol_sha256']
 for n,sha in m['artifact_sha256'].items():assert hashlib.sha256((H/stage/n).read_bytes()).hexdigest()==sha
 for v,b in m['builds']['variants'].items():assert hashlib.sha256(Path(b['binary']).read_bytes()).hexdigest()==b['binary_sha256']
 audit.append({'stage':stage,'processes':len(m['cases']),'failed':len(d['failed']),'replays':sum(c['repetitions'] for c in m['cases'] if c['exit_code']==0)})
 for r in d['rows']:
  if not r['complete']:lines.append(f'| {stage} | {r["cell"]} | incomplete | — | — | — | — | — |');continue
  x=r['metrics']['mean_replay_ns'];y=r['metrics']['sum_replay_ns'];first=r['metrics']['first_replay_ns'];lines.append(f"| {stage} | {r['cell']} | {x['left']['median']/1e6:.3f} | {x['right']['median']/1e6:.3f} | {x['delta_percent']:+.2f}% | {first['delta_percent']:+.2f}% | {y['left']['median']/1e6:.2f}/{y['right']['median']/1e6:.2f} | {r['slower_pairs']}/4 |")
lines+=['','Cells: 0=path100k,q50; 1=path1M,q90; 2=blocks1M,q90. Percent change is ratio of medians of process means; it is not median paired change. First-replay change is separate diagnostic information, not an alternative primary statistic. Full ranges and each paired delta are in the stage assessment JSON.','','## Limits and preservation','','This small study cannot identify a hardware cause, establish a universal noise bound or prove a candidate regression absent. Historical comparisons and the promotion-only patch remain unchanged. The preflight collector initially encountered a missing `config` field on an unrelated imported topology; it was fixed before measurements and [the error log](preflight-failure.txt) was preserved. No failed measurement was discarded.','','[Audit](audit.json) records validated hashes, counts and Python syntax. The unchanged binaries passed workspace checks in the earlier candidate study; no new Rust test claim is needed here. No commits or staging changes were made.']
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
(H/'audit.json').write_text(json.dumps({'passed':True,'stages':audit,'same_frozen_sources_and_binaries':True,'recorded_artifact_hashes_match':True,'python_syntax_valid':True,'AB_started':AB is not None},indent=2)+'\n')
(H/'README.md').write_text('\n'.join(lines)+'\n');print(json.dumps(audit,indent=2))
