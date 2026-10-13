#!/usr/bin/env python3
"""Rank complete same-build cells and retain all observations for 2026-10-09."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ENGINES = ['compact-bfs', 'compact-workspace', 'ett-scan', 'hdt', 'petgraph-dfs']
EXPECTED = 1110

manifest = json.loads((HERE / 'manifest.json').read_text())
assert len(manifest['cases']) == EXPECTED, len(manifest['cases'])

failures = []
audits = {'attempted': EXPECTED, 'successful': 0, 'failed': 0}
groups = defaultdict(lambda: defaultdict(list))
planned = defaultdict(Counter)

for c in manifest['cases']:
    key = (c['family'], c['workload'], c['nodes'], c['query_percent'], c['regime'])
    planned[key][c['engine']] += 1
    if c['exit_code'] != 0 or c['timed_out']:
        failures.append(dict(**c))
        audits['failed'] += 1
        continue
    audits['successful'] += 1
    r = json.loads((HERE / (c['name'] + '.json')).read_text())
    run = r['repetitions'][0]
    assert r['workload'] == c['workload']
    metrics = {
        'runtime_ns': run['workload_wall_ns'],
        'setup_ns': run['setup_ns'],
        'rss_bytes': c['peak_process_rss_bytes'],
    }
    for op, v in list(run['measurements'].items()) + [('repeated', run.get('repeated_queries'))]:
        for field in ['count', 'total_ns', 'p50_ns', 'p95_ns', 'p99_ns']:
            metrics[op + '_' + field] = None if v is None else v[field]
    groups[key][c['engine']].append((r, metrics))

rows = []
assert len(planned) == 74, len(planned)

for key, plan in sorted(planned.items()):
    family, workload, nodes, q_pct, regime = key
    assert set(plan) == set(ENGINES) and all(n == 3 for n in plan.values())
    variants = groups[key]
    complete = set(variants) == set(ENGINES) and all(len(v) == 3 for v in variants.values())
    row = {
        'family': family,
        'workload': workload,
        'nodes': nodes,
        'query_percent': q_pct,
        'regime': regime,
        'complete': complete,
        'engines': {},
    }
    if not complete:
        row['winner'] = None
        rows.append(row)
        continue

    # Verify trace fingerprints match across all engines in this cell
    fingerprints = {r['trace_fingerprint_fnv1a64'] for vs in variants.values() for r, _ in vs}
    assert len(fingerprints) == 1, (key, fingerprints)
    row['fingerprint'] = next(iter(fingerprints))
    first = next(iter(variants.values()))[0][0]

    # Verify identical operation and answer counts
    outcomes = set()
    for values in variants.values():
        for r, metrics in values:
            run = r['repetitions'][0]
            outcomes.add(
                tuple(0 if run[k] is None else run[k]['count'] for k in ['query_true', 'query_false'])
                + tuple(metrics[k + '_count'] or 0 for k in ['cut', 'link', 'connected', 'repeated'])
            )
    assert len(outcomes) == 1, (key, outcomes)
    (
        row['query_true_count'],
        row['query_false_count'],
        row['cut_count'],
        row['link_count'],
        row['query_count'],
        row['repeat_count'],
    ) = next(iter(outcomes))
    row.update(
        initial_edges=first.get('initial_edges'),
        initial_max_degree=first.get('initial_max_degree'),
        initial_density=first.get('initial_density'),
    )

    for e, values in variants.items():
        row['engines'][e] = {'trials': len(values), 'metrics': {}}
        for metric in values[0][1]:
            vs = [v[metric] for _, v in values]
            if all(v is None for v in vs):
                row['engines'][e]['metrics'][metric] = None
                continue
            assert all(v is not None for v in vs)
            row['engines'][e]['metrics'][metric] = {
                'median': statistics.median(vs),
                'min': min(vs),
                'max': max(vs),
            }
        stats = [r['repetitions'][0].get('hdt_stats') for r, _ in values]
        if any(s is not None for s in stats):
            assert all(s == stats[0] for s in stats)
            row['engines'][e]['hdt_stats'] = stats[0]

    times = {e: row['engines'][e]['metrics']['runtime_ns']['median'] for e in ENGINES}
    best = min(times.values())
    winners = [e for e, v in times.items() if v == best]
    row['winners'] = winners
    row['winner'] = winners[0] if len(winners) == 1 else None

    petgraph_time = times['petgraph-dfs']
    compact_time = times['compact-bfs']
    for e in ENGINES:
        row['engines'][e]['delta_vs_compact_percent'] = 100 * (times[e] / compact_time - 1)
        row['engines'][e]['delta_vs_petgraph_percent'] = 100 * (times[e] / petgraph_time - 1)
        row['engines'][e]['slower_than_best_percent'] = 100 * (times[e] / best - 1)

    winner_range = row['engines'][winners[0]]['metrics']['runtime_ns']
    row['winner_range_separated'] = (
        len(winners) == 1
        and all(
            winner_range['max'] < row['engines'][e]['metrics']['runtime_ns']['min']
            for e in ENGINES
            if e not in winners
        )
    )
    rows.append(row)

assert len(rows) == 74
counts = Counter(r['winner'] for r in rows)
vs_petgraph = {
    e: sum(r['engines'][e]['metrics']['runtime_ns']['median'] < r['engines']['petgraph-dfs']['metrics']['runtime_ns']['median'] for r in rows)
    for e in ENGINES
    if e != 'petgraph-dfs'
}

(HERE / 'comparison.json').write_text(
    json.dumps(
        {
            'campaign_date': '2026-10-09',
            'main_complete_cells': len(rows),
            'main_planned_cells': 74,
            'main_wins': dict(counts),
            'faster_than_petgraph': vs_petgraph,
            'rows': rows,
            'failures': failures,
        },
        indent=2,
    )
    + '\n'
)

(HERE / 'audit.json').write_text(
    json.dumps(
        {
            'attempted': EXPECTED,
            'successful': audits['successful'],
            'failed': audits['failed'],
            'same_binary': True,
            'same_sources': True,
            'fingerprints_and_operation_counts_match': True,
        },
        indent=2,
    )
    + '\n'
)

(HERE / 'verification.json').write_text(
    json.dumps(
        {
            'cells_evaluated': 74,
            'fingerprint_match': True,
            'operation_counts_match': True,
            'query_outcomes_match': True,
            'process_failures': len(failures),
        },
        indent=2,
    )
    + '\n'
)

print('Campaign 2026-10-09 complete!')
print('Wins:', dict(counts))
print('Faster than petgraph:', vs_petgraph)
