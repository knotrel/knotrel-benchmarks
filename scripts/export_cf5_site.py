#!/usr/bin/env python3
"""Exports the v1.1.0 CF5 engine comparison to the benchmark site's engine-comparison schema.

CF5 compares engines on one candidate build (``cluster-forest`` against ``compact-bfs``,
``ett`` and ``hdt`` on knotrel ``02cba68``). It is not a release-to-release comparison, so it
does not fit ``docs/data/releases.json``; it goes to ``docs/data/engine-comparisons.json``,
rendered by ``scripts/build_site.py`` as ``docs/engines/<id>.html``.

``docs/SITE.md``: "Add an adapter/export from a campaign analyzer rather than manually
transcribing measurements." This is that adapter. It reads only the analyzers' outputs
(``analysis-session1.json`` from the frozen ``analyze_cf5.py`` and ``analysis-session1-L2.json``
from the revised L2 analyzer, decision D2 of the report) and recomputes no class:

- family statements (plan section 12) are copied verbatim with the cells the analyzer named;
- per family and reference, the classes of those cells' metrics are counted as computed, and
  the range of the median paired ratio of their timed metrics is given as ``exp(median_log)``
  to three significant figures (``cluster-forest`` over reference for times and tails, reference
  over ``cluster-forest`` for throughput; below 1 favours ``cluster-forest``);
- per block and reference, every metric class is counted (blocks K, L and S only: the V blocks
  compare a build with v1.0.0, not engines, and stay in the report);
- L2 C3 FAIL and C4 EXCEEDS_BUDGET runs are listed with the analyzer's numbers.

The report's maintainer decisions (D1 limitation, D5 disposition) are passed as text by the
caller from the report; they never change a class.

Usage:
    python3 scripts/export_cf5_site.py --report-url URL --evidence-url URL [--out PATH]
"""
import argparse
import collections
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / 'results/v1.1.0-cf5/analysis/attempt1'
OUT = ROOT / 'docs/data/engine-comparisons.json'

COMPARISON_ID = 'cluster-forest-cf5-02cba68'
CANDIDATE_SHA = '02cba6825f9ad9ef769f4006428ccad5509076e9'
TOOLING_SHA = 'f4d41f19869c0a63baa0ce32d91ab02c1dd1522f'
REFERENCES = ('compact-bfs', 'ett', 'hdt')
ENGINE_BLOCKS = ('K1', 'K2', 'K2x', 'K3', 'K4', 'L1', 'L3', 'L4', 'S1')

# Workload descriptions (plan section 4 and docs/methodology.md). Text only, no measurement.
FAMILIES = [
    ('dense-bridge-churn-v1', 'Two cliques, one bridge toggled', 'core'),
    ('redundant-bridge-churn-v1', 'Two cliques, two bridges toggled independently', 'core'),
    ('components-join-split-v1', 'Two paths joined and split by a seeded bridge', 'core'),
    ('hub-alternatives-v1', 'Star plus a leaf path; a leaf is isolated and restored', 'core'),
    ('sustained-churn-blocks-v1', '16-vertex cycles joined by bridges, persistent toggling', 'core'),
    ('chain-split-rejoin-v1', 'Path; a seeded bridge is cut and relinked', 'core'),
    ('cycle-alternatives-v1', 'Ring; cuts with and without an alternative path', 'core'),
    ('sustained-churn-path-v1', 'Path edges toggled persistently, with queries', 'core'),
    ('K2-d4', 'Staged random inserts and deletes, E = 2V, with construction (K3) and memory (K4)', 'core'),
    ('K2-d16', 'Staged random inserts and deletes, E = 8V, with construction (K3) and memory (K4)', 'core'),
    ('K2x', 'Random simple graph, E = 3V, inserts, queries and deletes (exploratory provenance)', 'core'),
    ('K3-families', 'Construction from the six sparse K1 family graphs at 100 000 vertices', 'core'),
    ('L', 'Node and edge lifecycle: L1 lifecycle window, L3 import and churn, L4 memory', 'core'),
    ('S1-lifecycle-off', 'HTTP server, mixed read and write traffic, lifecycle off', 'end-to-end'),
    ('S1-lifecycle-on', 'HTTP server, mixed read and write traffic, lifecycle on', 'end-to-end'),
]

C3_WORKLOADS = {'same': 'reuse same', 'toggle': 'toggle', 'fresh': 'fresh'}


def sig3(value):
    """Round to three significant figures."""
    return float(f'{value:.3g}')


def sizes(cell_ids):
    """Vertex counts that appear in a family's cell identifiers, ascending."""
    found = set()
    for cell in cell_ids:
        found.update(int(n) for n in re.findall(r'-(\d{3,})-vs-', cell))
    return sorted(found)


def family_rows(analysis):
    cells = analysis['cells']
    statements = analysis['family_statements']
    known = {name for name, _, _ in FAMILIES}
    if set(statements) != known:
        raise SystemExit(f'family set changed: {sorted(set(statements) ^ known)}')
    rows = []
    for name, description, scope in FAMILIES:
        against = []
        members = {cid: c for cid, c in cells.items() if c.get('family') == name}
        for ref in REFERENCES:
            entry = statements[name].get(ref)
            if entry is None:
                continue
            own = sorted(cid for cid, c in members.items() if c['reference'] == ref)
            classes = collections.Counter()
            changes = []
            for cell_id in own:
                for metric in cells[cell_id]['metrics'].values():
                    classes[metric['class']] += 1
                    if 'median_log' in metric:
                        changes.append(math.exp(metric['median_log']))
            against.append({
                'reference': ref,
                'statement': entry['statement'],
                'cells': len(own),
                'blocks': sorted({cells[c]['block'] for c in own}),
                'classes': dict(sorted(classes.items())),
                'median_ratio': [sig3(min(changes)), sig3(max(changes))] if changes else None,
                'named_cells': entry['named_cells'],
            })
        rows.append({'family': name, 'description': description, 'scope': scope,
                     'sizes': sizes(members), 'against': against})
    return rows


def block_counts(analysis):
    counts = collections.defaultdict(collections.Counter)
    for cell in analysis['cells'].values():
        if cell['block'] in ENGINE_BLOCKS:
            for metric in (cell.get('metrics') or {}).values():
                counts[(cell['block'], cell['reference'])][metric['class']] += 1
    return [{'block': block, 'reference': ref, 'classes': dict(sorted(counts[(block, ref)].items()))}
            for block in ENGINE_BLOCKS for ref in REFERENCES if (block, ref) in counts]


def workload(run_id):
    """Graph, workload and size of an L2 run id such as C-heap-lifecycle-cluster-forest-sparse-same-1000."""
    match = re.fullmatch(r'C-(heap|rss)-lifecycle-cluster-forest-(\w+)-(\w+)-(\d+)', run_id)
    if not match:
        raise SystemExit(f'unexpected L2 run id: {run_id}')
    _, graph, mode, nodes = match.groups()
    return graph, C3_WORKLOADS.get(mode, mode), int(nodes)


def lifecycle_rules(l2):
    runs = l2['sustained']
    rules = {}
    for rule in ('C1', 'C2', 'C3', 'C4'):
        rules[rule] = dict(sorted(collections.Counter(r[rule] for r in runs if rule in r).items()))
    def entry(run):
        graph, mode, nodes = workload(run['id'])
        return {'run': run['id'], 'graph': graph, 'workload': mode, 'nodes': nodes,
                'metric': run['metric'], 'late_over_early': round(run['late_over_early'], 3),
                'projected_growth_30_pct': round(100 * run['projected_growth_30'], 1),
                'first_bytes': run['first'], 'last_bytes': run['last']}
    return {
        'counts': rules,
        'c3_fail': [entry(r) for r in runs if r.get('C3') == 'FAIL'],
        'c4_exceeds_budget': [entry(r) for r in runs if r.get('C4') == 'EXCEEDS_BUDGET'],
    }


def build(report_url, evidence_url):
    analysis = json.loads((ANALYSIS / 'analysis-session1.json').read_text())
    l2 = json.loads((ANALYSIS / 'analysis-session1-L2.json').read_text())
    if analysis['schema'] != 'cf5-analysis-2' or analysis['campaign_failed']:
        raise SystemExit('unexpected CF5 analysis: schema or campaign_failed')
    return {
        'schema_version': 1,
        'comparisons': [{
            'id': COMPARISON_ID,
            'title': 'cluster-forest compared with compact-bfs, ETT and HDT',
            'kind': 'engine comparison on one build',
            'candidate_engine': 'cluster-forest',
            'reference_engines': list(REFERENCES),
            'candidate_sha': CANDIDATE_SHA,
            'tooling_sha': TOOLING_SHA,
            'campaign': 'v1.1.0 CF5, attempt 1, session 1 (2026-11-24 to 2026-11-25)',
            'environment': 'Apple M3 (8 cores), 16 GB, macOS 26.5.2, Rust 1.100.0, AC power; '
                           'server, PostgreSQL (S3 only) and load generator on the same machine',
            'method': 'Paired design, 24 measured pairs per timed cell, interval [r(7), r(18)] of the '
                      'paired log ratios (97.73 %); margins: time 10 %, tail 25 %, throughput 10 %, '
                      'memory 20 %. K4 and L4 are deterministic allocator counts, one run per arm.',
            'decision': 'compact-bfs stays the default engine; cluster-forest is opt-in and experimental.',
            'limitations': [
                'Host swap activity not verifiable; results accepted by the maintainer with this '
                'limitation. Swap occupancy was 738.25 MB at the start and at all 30 snapshots, and '
                '722.25 MB at the end; the 192 zero values of the per-process swap counter concern '
                'only the V1 processes observed.',
                'Statements hold only for the measured workloads, sizes and densities, this host, '
                'candidate 02cba68 and the server configurations used.',
                'The measurement limit is a calibration estimate, not a mathematical bound; '
                'per-operation timing (K1, L3 churn) is not quantified.',
            ],
            'lifecycle_disposition': 'The two C3 FAILs are accepted by the maintainer as a documented '
                                     'limitation of the cluster-forest lifecycle on the sparse '
                                     '1 000-node graph; their class stays FAIL and memory stability '
                                     'for those two workloads stays open.',
            'report_url': report_url,
            'evidence_url': evidence_url,
            'families': family_rows(analysis),
            'block_counts': block_counts(analysis),
            'lifecycle_rules': lifecycle_rules(l2),
        }],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--report-url', required=True)
    parser.add_argument('--evidence-url', required=True)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    data = build(args.report_url, args.evidence_url)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
