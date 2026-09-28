#!/usr/bin/env python3
"""Summarize saved comparison reports, never averaging pooled percentiles.

Usage: python3 scripts/summarize_comparison.py RESULT_DIRECTORY
Writes summary.csv exclusively. Each row summarizes per-repetition values;
repetitions from one process are correlated, not independent trials.
"""
import csv
import json
from pathlib import Path
import statistics
import sys


def summarize(directory):
    """Group schema-3 reports by regime, family, size and versioned backend."""
    manifest = json.loads((directory / 'manifest.json').read_text())
    groups = {}
    for case in manifest['cache_protocol']['cases_in_execution_order']:
        report = json.loads((directory / (case['name'] + '.json')).read_text())
        for backend in report['comparisons']:
            key = (case['regime'], backend['config']['nodes'], backend['workload'], backend['engine'])
            groups.setdefault(key, []).extend(backend['repetitions'])
    rows = []
    for key, runs in sorted(groups.items()):
        row = dict(zip(['regime', 'nodes', 'workload', 'engine'], key))
        row['repetition_summaries'] = len(runs)
        for op in ['cut', 'link', 'connected']:
            for percentile in ['p50_ns', 'p95_ns', 'p99_ns']:
                row[f'{op}_{percentile}_median'] = statistics.median(r['measurements'][op][percentile] for r in runs if r['measurements'][op]) if any(r['measurements'][op] for r in runs) else None
        totals = [sum(r['measurements'][op]['total_ns'] for op in ['cut', 'link', 'connected'] if r['measurements'][op]) for r in runs]
        for label, values in [('base_operations_total_ns', totals),
                              ('setup_ns', [r['setup_ns'] for r in runs]),
                              ('query_repeat_p50_ns', [r['repeated_queries']['p50_ns'] for r in runs if r['repeated_queries']])]:
            if values:
                row[label + '_median'] = statistics.median(values)
                row[label + '_min'] = min(values)
                row[label + '_max'] = max(values)
        rows.append(row)
    return rows


if __name__ == '__main__':
    destination = Path(sys.argv[1])
    rows = summarize(destination)
    with (destination / 'summary.csv').open('x', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
