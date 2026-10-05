"""Render all paired results and audit preserved collection artifacts."""
import hashlib
import json
import statistics
from pathlib import Path
HERE = Path(__file__).resolve().parent
m = json.loads((HERE / 'manifest.json').read_text())
rows = json.loads((HERE / 'comparison.json').read_text())['cells']
pairs = {}
for c in m['cases']:
    pairs.setdefault(c['reference'], {})[c['variant']] = c['hdt_stats']
changed = sum(v['before'] != v['after'] for v in pairs.values())
text = '''# HDT direct joins — paired before/after

Knotrel's experimental HDT forest now links two tours with two direct AVL joins,
using the newly allocated directed edge tokens as pivots. Previously it used
three concatenations, each splitting a tour to obtain a pivot. Both constructions
preserve the sequence `left, ab, right, ba`, stable handles, incidence flags,
vertex counts and logarithmic worst-case link complexity. AVL shape can differ,
which may change marked-vertex traversal and replacement selection. This is
Knotrel versus its previous implementation, not a comparison with an external
product. Default engine and public configuration remain unchanged.

## Protocol

All 136 HDT reference cases from the preserved October 4 sparse, dense, repeated
query and Cogentco campaigns were run on both frozen executables: 272 processes,
66 scenario cells, two trials per synthetic cell and four per Cogentco cell.
Order is shuffled with seed 42; adjacent before/after order alternates. Each
process validates expected query and mutation results; every trace fingerprint
matches its historical reference. Work counters are recorded, not required to
match, because forest shape may affect edge selection.

Before includes the previously accepted local-ID reuse. Both variants retain
engine identity `knotrel-core/hdt-sparse-levels-v3`; identify them through manifest
variant and binary hashes. Manifest snapshots capture source hashes, revisions,
build commands and Rust/Cargo environment variables. `core-after.patch` preserves
the change. Runtime checkout metadata is not the source identity of the frozen
before executable. No answer cache is introduced. Fresh means no deliberate
warmup, warmed means one untimed replay on another fresh graph; hardware caches
are not flushed. Whole-process peak RSS includes setup, validation and traces.

## Results

Delta is `100 * (after / before - 1)`: negative is lower cost. Baseline timings
come from this paired collection, not the historical campaign. Full operation
p50/p95/p99, totals, setup, RSS, sample ranges and historical drift are retained
in `comparison.json`. Percentiles are medians of per-process percentiles, not
pooled samples. Small trial counts do not establish statistical significance.

'''
text += f'HDT work counters differ in **{changed}/{len(pairs)} paired cases**.\n\n'
text += '| Family | Lower runtime / cells | Runtime delta range | Median cell delta |\n|---|---:|---:|---:|\n'
for family in ['sparse', 'dense', 'repeats', 'cogentco']:
    ds = [r['metrics']['runtime_ns']['delta_percent'] for r in rows if r['family'] == family]
    text += f'| {family} | {sum(d < 0 for d in ds)}/{len(ds)} | {min(ds):+.2f}% to {max(ds):+.2f}% | {statistics.median(ds):+.2f}% |\n'
text += '\nCell counts are descriptive, not a production-weighted score.\n\n'
text += '| Family / workload | Nodes | Query % | Regime | Before ms | After ms | Runtime delta | Cut p95 delta | RSS delta |\n|---|---:|---:|---|---:|---:|---:|---:|---:|\n'
for r in rows:
    metrics = r['metrics']; w = metrics['runtime_ns']
    text += f"| {r['family']} / {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {w['before']/1e6:.3f} | {w['after']/1e6:.3f} | {w['delta_percent']:+.2f}% | {metrics['cut_p95_ns']['delta_percent']:+.2f}% | {metrics['rss_bytes']['delta_percent']:+.2f}% |\n"
text += '''
## Reproduction

From the benchmark repository, `build.py before` and `build.py after` freeze the
respective checked-out sources into `/private/tmp/knotrel-hdt-joins`; execute
before building/modifying the next variant. `collect.py` requires those snapshots
and the Cogentco trace at its documented temporary path. Use a new result
directory for every collection; existing manifests are never overwritten.
Run `compare.py`, then `report.py` to regenerate this table and audit. Raw trace
exports and binaries are local/ignored; reconstruct the source with recorded
revisions and patch. The original source trace import provenance remains in the
reference Cogentco campaign. Keep the
[before/after policy](../../docs/experiments/2026-10-04-before-after-policy.md).
'''
text += '\n## Acceptance and validation\n\nThe [48-process adaptive confirmation](../2026-10-05-hdt-joins-confirmation/README.md)\nrepeats all six cells with initial runtime regression above 15%, four new paired\ntrials each. The +161% and +289% outliers do not reproduce, but warmed 100k path /\n50% queries remains **11.62% slower**. Original and confirmation measurements are\nkept separate. Total experimental processes: **320**.\n\nRetain the direct-join change in the experimental HDT backend: warmed 100k cyclic\nblocks improve by 26.01%, 35.79% and 14.75% for 10%, 50%, 90% queries in the full\ncampaign; Cogentco improves by 9.65–12.25%. This is not a universal improvement,\nand the confirmed path regression remains a follow-up target. Default engine\nselection is unchanged. The work counters happen to match in every paired run,\nso measured differences here are not explained by fewer promotions/candidates.\n\nFormatting, all-target Clippy with warnings denied, full workspace tests and\ndoctests, and Rustdoc with warnings denied passed in both repositories; four\nPython adapter tests passed. Existing forest tests validate rotations, repeated\ncut/relink, reversed endpoints, recycled tokens, sizes and both candidate marks.\nIndependent read-only review found no correctness issue. This is a refactoring\nwith unchanged semantics; the existing invariant suite was run before and after.\n'
(HERE / 'README.md').write_text(text)
audit = {}
for directory in [HERE] + [HERE.parent / f'2026-10-04-{f}-campaign' for f in ['sparse','dense','repeats','cogentco']]:
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, expected in manifest['artifact_sha256'].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected, name
    audit[directory.name] = len(manifest['artifact_sha256'])
(HERE / 'audit.json').write_text(json.dumps({'verified_artifact_counts': audit, 'paired_cases': len(pairs), 'changed_work_counters': changed}, indent=2) + '\n')
