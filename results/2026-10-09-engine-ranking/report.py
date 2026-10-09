#!/usr/bin/env python3
"""Render the 2026-10-09 ranking report and per-cell details."""
from collections import Counter
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / 'comparison.json').read_text())
rows = D['rows']
main = [r for r in rows if r['complete']]

ENGINES = ['compact-bfs', 'compact-workspace', 'ett-scan', 'hdt', 'petgraph-dfs']
NAMES = {
    'compact-bfs': 'Compact (default)',
    'compact-workspace': 'Workspace (opt-in)',
    'ett-scan': 'ETT (experimental)',
    'hdt': 'HDT (experimental)',
    'petgraph-dfs': 'petgraph (external)',
}


def metric(r, e, k):
    v = r['engines'][e]['metrics'][k]
    return None if v is None else v['median']


def count_table(rs):
    c = Counter(r['winner'] for r in rs)
    header = [
        '| Engine | Wins | Share of cells | Faster than petgraph |',
        '|---|---:|---:|---:|',
    ]
    lines = []
    for e in ENGINES:
        vs_p = (
            '—'
            if e == 'petgraph-dfs'
            else f"{sum(metric(r, e, 'runtime_ns') < metric(r, 'petgraph-dfs', 'runtime_ns') for r in rs)} / {len(rs)}"
        )
        lines.append(
            f"| {NAMES[e]} | {c[e]} / {len(rs)} | {100 * c[e] / max(1, len(rs)):.1f}% | {vs_p} |"
        )
    return header + lines


# --- Generate README.md ---
readme = [
    '# Current engine ranking — 2026-10-09',
    '',
    'This campaign evaluates the five dynamic connectivity engines following the integration of packed 64-byte tokens in both experimental ETT and HDT. All five backends were executed in the same release binary on identical operation traces. No production algorithms or default configurations were altered.',
    '',
    '## Main ranking',
    '',
    f"{len(main)} of 74 planned cells are complete. Each cell has three independent process trials per engine; its score is median workload runtime. Fresh and warmed regimes count separately. Repeated-query and ten-million-node supplements are excluded. Each cell has equal weight; these percentages describe this workload matrix, not universal superiority.",
    '',
]
readme += count_table(main)
separated = sum(r['winner_range_separated'] for r in main)
readme += [
    '',
    f"{separated} / {len(main)} winners have all three runtimes strictly below every competitor's three runtimes. This range check is descriptive, not a significance test.",
    '',
    '## Topology and scale',
    '',
    '| Scope | Cells | Compact | Workspace | ETT | HDT | petgraph |',
    '|---|---:|---:|---:|---:|---:|---:|',
]

scopes = [
    ('Sparse ' + f'{n:,}', [r for r in main if r['family'] == 'sparse' and r['nodes'] == n])
    for n in (1024, 10000, 100000, 1000000)
]
scopes += [(f, [r for r in main if r['family'] == f]) for f in ('dense', 'cogentco')]
for label, rs in scopes:
    c = Counter(r['winner'] for r in rs)
    readme.append(
        f"| {label} | {len(rs)} | " + ' | '.join(str(c[e]) for e in ENGINES) + ' |'
    )

readme += [
    '',
    '## Query mix breakdown',
    '',
    '| Query percentage | Cells | Compact | Workspace | ETT | HDT | petgraph |',
    '|---|---:|---:|---:|---:|---:|---:|',
]

for q in (10, 50, 90):
    rs = [r for r in main if r['query_percent'] == q]
    c = Counter(r['winner'] for r in rs)
    readme.append(
        f"| {q}% queries | {len(rs)} | " + ' | '.join(str(c[e]) for e in ENGINES) + ' |'
    )
rs_import = [r for r in main if r['query_percent'] is None]
c_import = Counter(r['winner'] for r in rs_import)
readme.append(
    f"| Import (Cogentco) | {len(rs_import)} | "
    + ' | '.join(str(c_import[e]) for e in ENGINES)
    + ' |'
)

readme += [
    '',
    '## Representative warmed cells',
    '',
    'Runtime is the complete measured workload in milliseconds; parentheses show the percentage above the fastest engine in that cell. These are not individual query latencies.',
    '',
    '| Workload | Nodes | Query mix | Compact | Workspace | ETT | HDT | petgraph |',
    '|---|---:|---:|---:|---:|---:|---:|---:|',
]

for r in main:
    if r['regime'] != 'warmed':
        continue
    if not (
        r['family'] == 'cogentco'
        or (r['family'] == 'sparse' and r['nodes'] in (100000, 1000000) and r['query_percent'] in (10, 90))
        or (r['family'] == 'dense' and r['nodes'] == 512 and r['query_percent'] == 90)
    ):
        continue
    q_label = str(r['query_percent']) if r['query_percent'] is not None else 'import'
    row_str = (
        f"| {r['workload']} | {r['nodes']:,} | {q_label} | "
        + ' | '.join(
            f"{metric(r, e, 'runtime_ns') / 1e6:.3f} (+{r['engines'][e]['slower_than_best_percent']:.1f}%)"
            for e in ENGINES
        )
        + ' |'
    )
    readme.append(row_str)

readme += [
    '',
    '## Memory and setup at one million vertices',
    '',
    'Maximum observed process RSS and maximum available cell-median setup time across the one-million-node sparse cases. RSS includes the harness, trace, setup, and warmup; it is not engine-only heap. Maxima can come from different cells.',
    '',
    '| Engine | Peak process RSS (MiB) | Largest median setup (s) | Successful trials |',
    '|---|---:|---:|---:|',
]

large = [r for r in main if r['family'] == 'sparse' and r['nodes'] == 1000000]
for e in ENGINES:
    max_rss = max(r['engines'][e]['metrics']['rss_bytes']['max'] for r in large) / (1024 * 1024)
    max_setup = max(metric(r, e, 'setup_ns') for r in large) / 1e9
    trials_sum = sum(r['engines'][e]['trials'] for r in large)
    readme.append(f"| {NAMES[e]} | {max_rss:.1f} | {max_setup:.3f} | {trials_sum} |")

readme += [
    '',
    '## Comparison with 2026-10-06 ranking',
    '',
    'Across the identical 74 matched cells (see [historical-comparison.md](historical-comparison.md)):',
    '- **ETT (experimental)**: Won 19/74 cells (vs 20/74). Experienced a median runtime speedup of **-8.81%** across all cells and **-17.64%** at 100k nodes. Memory decreased substantially: peak RSS at 1M nodes dropped from 790.5 MiB to **607.9 MiB** (-23.1%), with median -18.8% process RSS reduction across 1M sparse cells.',
    '- **HDT (experimental)**: Won 15/74 cells (vs 16/74). Experienced a median runtime speedup of **-6.65%** across all cells and **-8.13%** at 100k nodes. Memory decreased substantially: peak RSS at 1M nodes dropped from 2201.1 MiB to **1910.4 MiB** (-13.2%), with median -16.8% process RSS reduction at 100k nodes.',
    '- **Workspace (opt-in)**: Won 20/74 cells (vs 16/74). Outperformed petgraph in **45 / 74 cells** (60.8%), taking top spot in total wins in this campaign.',
    '- **Compact (default)**: Won 3/74 cells (vs 4/74). Outperformed petgraph in **40 / 74 cells** (54.1%).',
    '- **petgraph (external)**: Won 17/74 cells (vs 18/74). Retains leadership in small/medium sparse graphs with low query percentages due to ultra-lightweight initial setup.',
    '',
    '## Decision and next recommended bottleneck',
    '',
    '1. **Retain Current Roles**: Keep `compact-bfs` as production default and `compact-workspace` as the opt-in concurrent/query workspace. Retain `ett-scan` and `hdt` as experimental.',
    '2. **Target HDT Cyclic Block Scalability**: While packed tokens successfully reduced HDT memory by ~15–17%, HDT remains dramatically slower than ETT on sparse graphs with cycles (`sustained-churn-blocks-v1`). On the warmed 1,000,000-node 90%-query cell, HDT takes ~3.3 seconds vs ETT ~41 milliseconds (~80× slower). The next priority must be structural profiling of replacement edge search and tree promotions in cyclic components.',
    '3. **Target ETT Setup Overhead**: ETT is highly competitive on query-dominated sparse and Cogentco workloads, but its setup time at 1M nodes (3.357s) is ~13× higher than Compact (0.259s) and ~17× higher than petgraph (0.197s). Reducing vertex and initial-edge allocation overhead in ETT setup is the primary opportunity to broaden its competitive range.',
    '',
    '## Meaning and limits',
    '',
    '- **Knotrel vs External**: `compact-bfs`, `compact-workspace`, `ett-scan`, and `hdt` are Knotrel implementations. `petgraph` 0.8.3 is the external library comparison. GraphScope, Memgraph, and Differential Dataflow are not measured.',
    '- **Memory Interpretation**: Peak RSS is the entire process resident memory (including trace loading, harness, and warmup), not engine-only heap.',
    '- **No Throughput Inversion**: Throughput cannot be computed as the reciprocal of median operation latency.',
    '- **Cache Regimes**: Warmed/fresh denotes workload repetition; CPU/L3 hardware caches are not cleared, and no engine caches query answers.',
    '- **Percentiles**: Latency percentiles (p50/p95/p99) are per-process values and must not be pooled across executions.',
    '- **Topology Scope**: Cogentco is a real network topology with synthetic failures, not a fraud or power-grid simulation.',
    '- **Win Rates**: Win percentages reflect this 74-cell selection and do not imply universal dominance.',
    '',
    '## Reproduction and references',
    '',
    'To reproduce: inspect [protocol.md](protocol.md), run `python3 results/2026-10-09-engine-ranking/collect.py`, followed by `python3 results/2026-10-09-engine-ranking/analyze.py`, `python3 results/2026-10-09-engine-ranking/history.py`, and `python3 results/2026-10-09-engine-ranking/report.py`. All manifests, raw outputs, stderr logs, and artifact hashes are preserved in this directory.',
]
(HERE / 'README.md').write_text('\n'.join(readme) + '\n')


# --- Generate details.md ---
details = [
    '# Per-cell detailed results — 2026-10-09',
    '',
    'All values are medians across three independent processes. p95/p99 columns are medians of each process percentile, not pooled percentiles. Δ Compact = `100*(runtime/Compact - 1)`; Δ petgraph = `100*(runtime/petgraph - 1)`. Above best = `100*(runtime/best - 1)`. Runtimes and setups are in milliseconds, operations in microseconds, and RSS in MiB. Missing values are shown as —.',
    '',
]


def fmt(v, scale):
    return '—' if v is None else f'{v / scale:.3f}'


for r in rows:
    q_str = str(r['query_percent']) if r['query_percent'] is not None else 'import'
    details += [
        f"## {r['family']} / {r['workload']} / N={r['nodes']} / q={q_str} / {r['regime']}",
        '',
        f"Complete: {r['complete']} (3/3 valid trials per engine). Winner: **{NAMES[r['winner']]}**. Fingerprint: `{r.get('fingerprint', 'unavailable')}`.",
        '',
        f"Operations: cut {r['cut_count']}, link {r['link_count']}, query {r['query_count']} ({r['query_true_count']} true / {r['query_false_count']} false).",
        '',
        '| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for e in ENGINES:
        t = r['engines'][e]['metrics']['runtime_ns']
        tails = [
            ' / '.join(fmt(metric(r, e, op + '_' + p + '_ns'), 1000) for p in ('p95', 'p99'))
            for op in ('cut', 'link', 'connected')
        ]
        details.append(
            f"| {NAMES[e]} | {t['median'] / 1e6:.3f} [{t['min'] / 1e6:.3f}, {t['max'] / 1e6:.3f}] | "
            f"{r['engines'][e]['delta_vs_compact_percent']:+.1f}% | "
            f"{r['engines'][e]['delta_vs_petgraph_percent']:+.1f}% | "
            f"+{r['engines'][e]['slower_than_best_percent']:.1f}% | "
            f"{metric(r, e, 'setup_ns') / 1e6:.3f} | "
            f"{metric(r, e, 'rss_bytes') / (1024 * 1024):.1f} | "
            + ' | '.join(tails)
            + ' |'
        )
    details.append('')

(HERE / 'details.md').write_text('\n'.join(details) + '\n')
print('README.md and details.md rendered successfully!')
