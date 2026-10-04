"""Compare replay wall time per scenario without modifying historical aggregates.

Runtime = workload_wall_ns: dispatch, timer calls, assertions and sampling included;
setup, parsing and offline validation excluded. Trials are summarized, not pooled.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ENGINES = ['compact-bfs', 'ett-scan', 'hdt', 'petgraph-dfs']
LABELS = ['Knotrel compact', 'Knotrel ETT', 'Knotrel HDT', 'External petgraph']


def compare(times):
    """Return observed minima and percentage deltas; ranges are not uncertainty CIs."""
    medians = {engine: statistics.median(values) for engine, values in times.items()}
    best = min(medians.values())
    assert best > 0
    winners = [engine for engine in ENGINES if medians[engine] == best]
    clear = len(winners) == 1 and max(times[winners[0]]) < min(
        value for engine, values in times.items() if engine != winners[0] for value in values)
    return {
        'winners': winners, 'best_ns': best, 'winner_range_separated': clear,
        'engines': {engine: {
            'runtime_ns': {'min': min(values), 'median': medians[engine], 'max': max(values)},
            'slower_than_best_percent': 100 * (medians[engine] / best - 1),
            'delta_vs_compact_percent': 100 * (medians[engine] / medians['compact-bfs'] - 1),
        } for engine, values in times.items()},
    }


def build():
    groups = defaultdict(lambda: defaultdict(list))
    fingerprints = defaultdict(set)
    for family in ['sparse', 'dense', 'cogentco', 'repeats']:
        directory = HERE.parent / f'2026-10-04-{family}-campaign'
        manifest = json.loads((directory / 'manifest.json').read_text())
        for case in manifest['cases']:
            path = directory / (case['name'] + '.json')
            assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['artifact_sha256'][path.name]
            report = json.loads(path.read_text())
            assert len(report['repetitions']) == 1
            key = (family, case.get('workload', report['workload']),
                   case.get('nodes', report.get('import', {}).get('node_count')),
                   case.get('query_percent'), case['regime'])
            groups[key][case['engine']].append(report['repetitions'][0]['workload_wall_ns'])
            fingerprints[key].add(report['trace_fingerprint_fnv1a64'])
    rows = []
    for key, times in sorted(groups.items()):
        assert set(times) == set(ENGINES) and len(fingerprints[key]) == 1
        assert len({len(v) for v in times.values()}) == 1
        row = dict(zip(['family', 'workload', 'nodes', 'query_percent', 'regime'], key))
        rows.append(row | {'trials': len(next(iter(times.values())))} | compare(times))
    counts = {}
    for family in ['overall', 'sparse', 'dense', 'cogentco', 'repeats']:
        selected = [r for r in rows if (r['family'] != 'repeats' if family == 'overall' else r['family'] == family)]
        wins = Counter(e for r in selected for e in r['winners'])
        counts[family] = {'scenarios': len(selected), 'ties': sum(len(r['winners']) > 1 for r in selected),
                         'range_separated_winners': sum(r['winner_range_separated'] for r in selected),
                         'wins': {e: wins[e] for e in ENGINES},
                         'win_percent': {e: 100 * wins[e] / len(selected) for e in ENGINES}}
    return {'metric': 'median workload_wall_ns across process trials',
            'formula_best': '100*(runtime/best_runtime-1)',
            'formula_compact': '100*(runtime/compact_runtime-1)',
            'counting': 'equal weight per scenario including separate fresh/warmed regimes; repeats excluded from overall',
            'counts': counts, 'scenarios': rows}


def markdown(data):
    lines = ['# Runtime percentages by scenario — 2026-10-04', '',
             'Runtime is `workload_wall_ns`, including dispatch, clock calls, assertions and',
             'sample recording, but excluding setup, parsing and offline validation. This',
             'differs from the sum of operation intervals in the main report.', '',
             'The lowest median runtime in each scenario is the local baseline (0%).',
             '`+100%` means twice its runtime; `+900%` means ten times its runtime.',
             'The JSON also gives signed deltas against Knotrel compact, the default:',
             'negative means less runtime. A 90% time reduction is not a 90% speedup.', '',
             'Each scenario has equal weight, including separate fresh/warmed regimes.',
             'Win counts reflect this chosen matrix, not production workload prevalence.',
             'Repeated-query scenarios are reported separately and excluded from overall.',
             'Observed trial-range separation is descriptive, not statistical significance.', '',
             '| Family | Scenarios | Knotrel compact wins | Knotrel ETT wins | Knotrel HDT wins | External petgraph wins |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for family, counts in data['counts'].items():
        cells = [f"{counts['wins'][e]} ({counts['win_percent'][e]:.1f}%)" for e in ENGINES]
        lines.append(f"| {family} | {counts['scenarios']} | " + ' | '.join(cells) + ' |')
    lines += ['', f"Overall, {data['counts']['overall']['range_separated_winners']} of {data['counts']['overall']['scenarios']} winners have runtime trial ranges below all other engines' ranges; no confidence interval is inferred.", '',
              'Each table row: workload / nodes / query percentage / cache regime. Entries',
              'are percentage **more runtime than the row winner**. `overlap` means the',
              "winner's observed range overlaps at least one competitor; rankings may be fragile."]
    for family in ['sparse', 'dense', 'cogentco', 'repeats']:
        lines += ['', '## ' + family, '',
                  '| Scenario | Winner | Best runtime ms | Compact Δ% | ETT Δ% | HDT Δ% | Petgraph Δ% | Range check |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for row in data['scenarios']:
            if row['family'] != family:
                continue
            scenario = f"{row['workload']} / {row['nodes']} / {row['query_percent'] if row['query_percent'] is not None else 'domain schedule'} / {row['regime']}"
            winners = ', '.join(LABELS[ENGINES.index(e)] for e in row['winners'])
            cells = [f"+{row['engines'][e]['slower_than_best_percent']:.1f}%" for e in ENGINES]
            lines.append(f"| {scenario} | {winners} | {row['best_ns']/1e6:.3f} | " + ' | '.join(cells) + f" | {'separated' if row['winner_range_separated'] else 'overlap'} |")
    lines += ['', 'Raw medians, trial ranges and signed deltas against Knotrel compact are in',
              '[runtime-percentages.json](runtime-percentages.json). Rebuild both with',
              '`python3 results/2026-10-04-connectivity-campaign/percentages.py`.', '',
              'See the [main report](README.md) for memory, operation tails, provenance and',
              'limitations. Runtime winners are not necessarily memory or startup winners.',
              'No historical measurement, source hash or original aggregate was changed.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    data = build()
    (HERE / 'runtime-percentages.json').write_text(json.dumps(data, indent=2) + '\n')
    (HERE / 'runtime-percentages.md').write_text(markdown(data))
