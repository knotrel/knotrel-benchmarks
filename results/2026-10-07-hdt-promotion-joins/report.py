"""Render measured before/after results without pooling earlier experiments."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
c=json.loads((H/'comparison.json').read_text());g=json.loads((H/'gate.json').read_text())
rows=['| Workload | Nodes | Query % | Regime | Before ms | After ms | Change | Faster pairs |','|---|---:|---:|---|---:|---:|---:|---:|']
for r in c['rows']:
 if not r['complete']:rows.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | incomplete | incomplete | — | — |");continue
 m=r['metrics']['runtime_ns'];rows.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {m['before']['median']/1e6:.3f} | {m['after']['median']/1e6:.3f} | {m['delta_percent']:+.2f}% | {r['pairs_faster']}/4 |")
b=json.loads((H.parent/(H.name+'-path-before-probe')/'results.json').read_text())['results'][0]
a=json.loads((H.parent/(H.name+'-path-after-probe')/'results.json').read_text())['results'][0]
for k in ('trace_sha256','trace_fingerprint_fnv1a64','promotions_by_source_level'):assert b[k]==a[k]
path_equal=b['counts']==a['counts']
(H/'path-structural-comparison.json').write_text(json.dumps({'counts_identical':path_equal,'before':b['counts'],'after':a['counts'],'scope':'Separate instrumented replays, two identical repetitions per variant; setup excluded. Counts are not time shares.'},indent=2)+'\n')
s=json.loads((H/'structural-comparison.json').read_text())
struct=[]
for r in s['rows']:
 d=r['scopes']['promote_tree'];struct.append(f"- {r['nodes']:,} vertices: promotion pull entries {d['pull']['delta_percent']:+.2f}%, join entries {d['join']['delta_percent']:+.2f}%, split entries {d['split']['delta_percent']:+.2f}%.")
decision=('The pilot gate passed. This qualifies the candidate for a full reference-matrix comparison; it does not justify production integration yet.' if g['passed'] else 'The pilot gate was not met. Keep the candidate experimental and do not integrate it or declare a general improvement.')
(H/'README.md').write_text('''# HDT promotion-only join association

## Decision

'''+decision+f" Qualifying block cells: {g['qualifying_blocks']}/4 (required 3). Control regressions meeting the screen: {len(g['control_regressions'])}.\n"+'''
The candidate is saved separately; production core code is unchanged. No earlier
candidate patches are combined. No commit or staging action is implied.

## Change

[Patch](candidate.patch): ordinary `Forest::link` retains left association through
`link_ordered::<false>`. Only tree-edge promotion in `HdtGraph::promote` calls
`link_promoted`, which uses right association at destination level `i+1 > 0`.
Both preserve the exact sequence `left, ab, right, ba`, AVL balance, parent links
and aggregates, with O(log V) worst-case link cost. Replacement links use the
ordinary route. No public configuration or API changes.

This targets the promotion benefit in the [previous global-association experiment](../2026-10-07-hdt-join-order/README.md)
while preserving ordinary level-zero construction. Compile-time selection avoids
a runtime configuration check, but code layout can still affect measured timing.

## Paired pilot

[Protocol](protocol.md): 72 sequential processes, nine cells, four pairs per cell,
2/2 before-first/after-first order, seed 42 shuffle. Includes the original eight
pilot cells plus warmed path at one million vertices, predeclared before timing.

'''+ '\n'.join(rows)+'''

Negative change means less runtime. Percentage is `100*(after median/before
median-1)`, not median paired percentage. Runtime is workload wall time, excluding
setup and including harness checking/timer overhead. Warmed performs an untimed
replay on a separate graph; no answer cache or hardware-cache flush. Whole-process
RSS, setup and operation latency tails are retained in [comparison.json](comparison.json).
This small pilot is an engineering screen, not statistical significance. Do not
pool these samples with earlier experiments or infer competitor performance.

All successful replays are checked against reference fingerprints and expected
answers, with identical operation and HDT counters. Failures are retained by the
analyzer; inspect its `failed` list. See [gate](gate.json) for the unchanged screen.

## Structural evidence

Separate instrumented executions, two identical repeats per variant/trace:

'''+ '\n'.join(struct)+f'''

Path1M,q50 replay counters identical before/after: **{path_equal}**. See
[path counters](path-structural-comparison.json). This checks the expected absence
of extra structural work on the non-promoting control, not equality of runtime.
Promotion counts, endpoint materialization and link-side sizes match in the block
probes. Function-entry counts include recursion and are not CPU-time shares.
See [block counters](structural-comparison.json) and sibling probe directories.

## Correctness and preservation

The explicit cyclic-order/aggregate tests exercise ordinary and promoted links,
reversed relinks and recycled tokens. The initial red log records the missing new
entry point, not a correctness defect in the baseline. Core tests/doctests pass.
Saved before/after sources include both `hdt_forest.rs` and `hdt.rs`; builds record
source/compiler/binary hashes. Reconstruct with [verify.py](verify.py), then inspect
[verification](reconstruction-verification.json) and [audit](audit.json).
All historical results and patches remain separate.
''')
print(decision)
