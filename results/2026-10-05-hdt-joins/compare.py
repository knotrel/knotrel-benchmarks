"""Aggregate paired HDT trials without pooling operation percentiles."""
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
manifest = json.loads((HERE / 'manifest.json').read_text())
groups = defaultdict(lambda: defaultdict(list))
for case in manifest['cases']:
    path = HERE / (case['name'] + '.json')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['artifact_sha256'][path.name]
    report = json.loads(path.read_text())
    reference = json.loads((ROOT / case['reference']).read_text())
    assert report['trace_fingerprint_fnv1a64'] == reference['trace_fingerprint_fnv1a64']
    # AVL shape can change replacement selection; exact answers remain validated by the runner.
    key = (case['family'], report['workload'], report.get('config', {}).get('nodes', report.get('import', {}).get('node_count')), report.get('query_percent'), case['regime'])
    def metrics(r, rss):
        run = r['repetitions'][0]
        values = {'runtime_ns': run['workload_wall_ns'], 'setup_ns': run['setup_ns'], 'rss_bytes': rss}
        for op, measure in list(run['measurements'].items()) + [('repeated', run['repeated_queries'])]:
            for field in ['count', 'p50_ns', 'p95_ns', 'p99_ns', 'total_ns']:
                values[f'{op}_{field}'] = None if measure is None else measure[field]
        return values
    groups[key][case['variant']].append(metrics(report, case['peak_process_rss_bytes']))
    if case['variant'] == 'before':
        groups[key]['historical'].append(metrics(reference, None))
rows = []
for key, variants in sorted(groups.items()):
    row = dict(zip(['family', 'workload', 'nodes', 'query_percent', 'regime'], key))
    row.update(trials=len(variants['before']), metrics={})
    assert len(variants['before']) == len(variants['after'])
    for metric in variants['before'][0]:
        samples = [[v[metric] for v in variants[name]] for name in ['before', 'after', 'historical']]
        if samples[0][0] is None:
            row['metrics'][metric] = None
            continue
        b, a = [statistics.median(s) for s in samples[:2]]
        h = statistics.median(samples[2]) if samples[2][0] is not None else None
        row['metrics'][metric] = {'before': b, 'after': a, 'delta_percent': 100 * (a / b - 1) if b else None,
            'before_range': [min(samples[0]), max(samples[0])], 'after_range': [min(samples[1]), max(samples[1])],
            'historical': h, 'baseline_drift_percent': 100 * (b / h - 1) if h else None}
    rows.append(row)
(HERE / 'comparison.json').write_text(json.dumps({'meaning': 'After/before minus one, percent; negative improves. Medians of per-process metrics, not pooled percentiles.', 'cells': rows}, indent=2) + '\n')
for family in ['sparse', 'dense', 'repeats', 'cogentco']:
    cells = [r for r in rows if r['family'] == family]
    ds = [r['metrics']['runtime_ns']['delta_percent'] for r in cells]
    print(family, len(ds), 'improved', sum(d < 0 for d in ds), 'range', min(ds), max(ds), 'median', statistics.median(ds))
for r in rows:
    if r['regime'] == 'warmed' and (r['nodes'] == 100000 or r['family'] == 'cogentco'):
        print(r['workload'], r['nodes'], r['query_percent'], {k: round(r['metrics'][k]['delta_percent'], 2) for k in ['runtime_ns', 'cut_p95_ns', 'rss_bytes']})
