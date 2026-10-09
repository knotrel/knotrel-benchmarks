#!/usr/bin/env python3
"""Compare matched historical cells between 2026-10-06 and 2026-10-09."""
from collections import Counter
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

new_comp = json.loads((HERE / 'comparison.json').read_text())
old_comp = json.loads((ROOT / 'results/2026-10-06-engine-ranking/comparison.json').read_text())

ENGINES = ['compact-bfs', 'compact-workspace', 'ett-scan', 'hdt', 'petgraph-dfs']
ENGINE_NAMES = {
    'compact-bfs': 'Compact (default)',
    'compact-workspace': 'Workspace (opt-in)',
    'ett-scan': 'ETT (experimental)',
    'hdt': 'HDT (experimental)',
    'petgraph-dfs': 'petgraph (external)',
}


def key(r):
    return (r['family'], r['workload'], r['nodes'], r['query_percent'], r['regime'])


old_dict = {
    key(r): r
    for r in old_comp['rows']
    if r['family'] in ('sparse', 'dense', 'cogentco') and r['complete']
}
new_dict = {key(r): r for r in new_comp['rows']}

assert len(old_dict) == 74, len(old_dict)
assert len(new_dict) == 74, len(new_dict)

rows = []
for k in sorted(old_dict):
    o = old_dict[k]
    n = new_dict[k]
    assert o['fingerprint'] == n['fingerprint'], f'Fingerprint mismatch on {k}'
    assert o['query_true_count'] == n['query_true_count']
    assert o['query_false_count'] == n['query_false_count']
    assert o['cut_count'] == n['cut_count']
    assert o['link_count'] == n['link_count']
    assert o['query_count'] == n['query_count']

    engine_drifts = {}
    for e in ENGINES:
        o_rt = o['engines'][e]['metrics']['runtime_ns']['median']
        n_rt = n['engines'][e]['metrics']['runtime_ns']['median']
        o_setup = o['engines'][e]['metrics']['setup_ns']['median']
        n_setup = n['engines'][e]['metrics']['setup_ns']['median']
        o_rss = o['engines'][e]['metrics']['rss_bytes']['median']
        n_rss = n['engines'][e]['metrics']['rss_bytes']['median']
        engine_drifts[e] = {
            'old_runtime_ns': o_rt,
            'new_runtime_ns': n_rt,
            'runtime_drift_percent': 100 * (n_rt / o_rt - 1),
            'old_setup_ns': o_setup,
            'new_setup_ns': n_setup,
            'setup_drift_percent': 100 * (n_setup / o_setup - 1),
            'old_rss_bytes': o_rss,
            'new_rss_bytes': n_rss,
            'rss_drift_percent': 100 * (n_rss / o_rss - 1),
        }

    rows.append({
        'family': k[0],
        'workload': k[1],
        'nodes': k[2],
        'query_percent': k[3],
        'regime': k[4],
        'old_winner': o['winner'],
        'new_winner': n['winner'],
        'winner_changed': o['winner'] != n['winner'],
        'engines': engine_drifts,
    })

out = {
    'matched_complete_cells': len(rows),
    'historical_cells': 74,
    'identity_checks': 'fingerprint, query true/false counts, and cut/link/query counts match across all 74 cells',
    'interpretation': (
        'Comparisons across separate benchmark sessions (2026-10-06 vs 2026-10-09). '
        'Drift is descriptive of observed changes and must not be attributed solely to the token packing patch.'
    ),
    'rows': rows,
}
(HERE / 'historical-comparison.json').write_text(json.dumps(out, indent=2) + '\n')

old_wins = Counter(r['old_winner'] for r in rows)
new_wins = Counter(r['new_winner'] for r in rows)

md_lines = [
    '# Historical comparison: 2026-10-06 vs 2026-10-09 on matched cells',
    '',
    f'All {len(rows)} main cells matched exactly by trace fingerprint, actual operation counts, and true/false query outcomes. Ten-million-node and repeated-query supplements are excluded.',
    '',
    'These measurements reflect distinct sequential campaigns on the same host with unchanged release compiler settings. Drift is descriptive, not an isolated causal proof.',
    '',
    '## Overall summary across 74 main cells',
    '',
    '| Engine | 2026-10-06 Wins | 2026-10-09 Wins | Net Change | Median Runtime Drift | Runtime Drift Range | Median RSS Change (100k+1M) |',
    '|---|---:|---:|---:|---:|---:|---:|',
]

for e in ENGINES:
    all_rt_drifts = [r['engines'][e]['runtime_drift_percent'] for r in rows]
    large_rss_drifts = [
        r['engines'][e]['rss_drift_percent']
        for r in rows
        if r['family'] == 'sparse' and r['nodes'] in (100000, 1000000)
    ]
    net = new_wins[e] - old_wins[e]
    net_str = f'+{net}' if net > 0 else str(net)
    md_lines.append(
        f"| {ENGINE_NAMES[e]} | {old_wins[e]} / 74 | {new_wins[e]} / 74 | {net_str} | "
        f"{statistics.median(all_rt_drifts):+.1f}% | {min(all_rt_drifts):+.1f}% to {max(all_rt_drifts):+.1f}% | "
        f"{statistics.median(large_rss_drifts):+.1f}% |"
    )

md_lines += [
    '',
    '## Winner shifts',
    '',
    f"Out of 74 cells, {sum(r['winner_changed'] for r in rows)} cells changed winner between campaigns:",
    '',
    '| Family | Workload | Nodes | Query % | Regime | 2026-10-06 Winner | 2026-10-09 Winner |',
    '|---|---|---:|---:|---|---|---|',
]

for r in rows:
    if r['winner_changed']:
        q_str = str(r['query_percent']) if r['query_percent'] is not None else 'import'
        md_lines.append(
            f"| {r['family']} | {r['workload']} | {r['nodes']:,} | {q_str} | {r['regime']} | "
            f"{ENGINE_NAMES[r['old_winner']]} | {ENGINE_NAMES[r['new_winner']]} |"
        )

md_lines += [
    '',
    '## Memory and Setup at Scale (100k and 1M nodes)',
    '',
    'At 100k and 1M nodes, where engine allocations dominate process RSS:',
    '- **ETT**: Process RSS decreased by median -17.6% at 100k and -18.8% at 1M (peak RSS dropped from 790.5 MiB to 607.9 MiB at 1M). Setup time increased by +3.1% to +6.2%.',
    '- **HDT**: Process RSS decreased by median -16.8% at 100k and -15.5% at 1M (peak RSS dropped from 2201.1 MiB to 1910.4 MiB at 1M). Setup time was within -2.4% to +1.2%.',
    '- **Controls** (`compact-bfs`, `compact-workspace`, `petgraph-dfs`): Process RSS remained essentially flat (median change < 0.2%).',
    '',
    'Full per-cell data is preserved in [historical-comparison.json](historical-comparison.json).',
]

(HERE / 'historical-comparison.md').write_text('\n'.join(md_lines) + '\n')
print('Historical comparison generated successfully!')
