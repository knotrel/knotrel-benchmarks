#!/usr/bin/env python3
"""Exports the v1.1.0 release entry of the benchmark site from the CF5 regression checks.

The CF5 campaign (``results/v1.1.0-cf5``) checked the candidate's existing engines against the
published v1.0.0 in two blocks; this adapter turns them into the 1.1.0 entry of
``docs/data/releases.json`` (site schema 2). It reads only the committed analyzer outputs,
never raw data, and recomputes no class:

- **V1** (``analysis-session1-V1.json``, ``analyze_v100q_a.py``, frozen v1.0.0 experiment A
  protocol): one row per cell for the primary metric with the cell's class, and one row per
  gated supporting metric with that metric's class, exactly as ``export_v100q_site.a_rows``
  exports experiment A. Supporting metrics the analyzer marks REPORT_ONLY have no class and stay
  in the campaign report.
- **V2** (``analysis-session1.json``, ``analyze_cf5.py``, section 6.1 rule): one row per metric of
  every ``V2`` cell with its class. A TIMER_LIMITED row also carries ``class_without_limit`` and
  the limit; it is never shown as its class without the limit.

Every row is ``decisive`` and ``completed``. The non-PASS rows of the five D3 cells carry the maintainer's
D3 disposition (``REPORT.md`` section 7), next to the class, not in place of it. Intervals are the
analyzers' order-statistic intervals of the median paired change (coverage 97.73 % at n = 24),
converted to percent: not 95 % intervals.

The ``cluster-forest`` comparison with the other engines is not a release comparison; it is the
engine comparison exported by ``export_cf5_site.py``.

**Fail closed.** A class unknown to the site schema stops the export (``export_v100q_site``'s
``measured_class``); so do a V1 analysis that is not the fixed n = 24 final decision, a V2 cell
that is not COMPLETE or not against v1.0.0, a D3 cell that does not exist or is PASS, and a
non-PASS cell without a D3 disposition. The whole dataset is validated with
``build_site.validate`` before it is written.

Takes no arguments. Writes ``docs/data/releases.json`` with the 1.1.0 entry replaced or added
first; every other entry is kept unchanged. Run ``build_site.py`` afterwards.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import build_site  # noqa: E402
import export_v100q_site as v100q  # noqa: E402

VERSION = '1.1.0'
CAMPAIGN = REPO / 'results/v1.1.0-cf5'
ANALYSIS = CAMPAIGN / 'analysis/attempt1'
RELEASES = REPO / 'docs/data/releases.json'
CANDIDATE_SHA = '02cba6825f9ad9ef769f4006428ccad5509076e9'
REFERENCE_SHA = 'd38df5f9fb935e95de6f7195d8bb1d5d9a458be9'  # tag v1.0.0
#: The squash commit of knotrel-benchmarks#41 on main, which published the report.
REPORT_COMMIT = '926e9c86a8a4b5e315154852525d77cb9b2ca16e'
BASE = f'https://github.com/knotrel/knotrel-benchmarks/tree/{REPORT_COMMIT}/results/v1.1.0-cf5'
CAMPAIGN_URL = BASE
EVIDENCE_URL = f'{BASE}/analysis/attempt1'
DECISION_URL = 'https://github.com/knotrel/knotrel-benchmarks/blob/main/results/v1.1.0-cf5/DECISION.md'
DECISION = 'accepted with exceptions'
ENVIRONMENT = ('Apple M3 (8 cores), 16 GB, macOS 26.5.2, toolchain 1.100.0; server and load generator on the '
               'same machine; host swap activity not verifiable (D1)')
BASELINE_POLICY = ('Measured against v1.0.0 (d38df5f), the latest release at campaign freeze, built from source '
                   'and measured again alongside the candidate. Regression checks of the existing engines only: '
                   'V1 under the frozen v1.0.0 experiment A protocol, V2 under the CF5 rules. The new '
                   'cluster-forest engine is compared with the other engines on the Engines page.')
NOTE = ('Measured on candidate 02cba68 (crate version 1.0.0 on main, never released) in CF5 attempt 1; the '
        'qualification decision applies to those results. 1.1.0 differs by documentation, CI, release checks, '
        'version metadata, console development tooling and a server dependency patch update (sonic-rs 0.5.11 '
        'to 0.5.12); the transfer of the results to the 1.1.0 build is an open maintainer decision (decision '
        'record). Binary identity with the measured build and a new measurement of 1.1.0 are not claimed. '
        'Host swap activity not verifiable; results accepted by the maintainer with this limitation.')
D3 = ('Maintainer disposition 2026-11-25 (REPORT.md section 7, D3): left open on performance; original class '
      'kept; no further measurement; neither a regression nor a pass')
#: The five cells D3 leaves open: V1 cell ids and V2 cell keys.
D3_CELLS = ('http_standalone_batch_b1_compact_bfs', 'http_standalone_batch_b64_compact_bfs',
            'http_lifecycle_compact_bfs_small', 'V2-chain-split-rejoin-v1-100000-ett-scan',
            'V2-sustained-churn-path-v1-100000-ett-scan')
HIGHER = ' (higher-is-better metric: analyzed as ln(reference/candidate), shown as candidate/reference)'


class ExportError(ValueError):
    """The inputs cannot be exported without changing a class or inventing a value."""


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def v1_rows(a: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        rows = v100q.a_rows(a, EVIDENCE_URL)
    except v100q.ExportError as error:
        raise ExportError(str(error)) from error
    for r in rows:
        r['experiment'] = 'V1'
    return rows


def v2_rows(cells: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    v2 = {k: c for k, c in sorted(cells.items()) if c.get('block') == 'V2'}
    if not v2:
        raise ExportError('no V2 cell in the CF5 analysis')
    for key, cell in v2.items():
        if cell.get('state') != 'COMPLETE' or cell.get('reference') != 'v1.0.0':
            raise ExportError(f'{key}: not a COMPLETE comparison against v1.0.0')
        for metric, m in sorted(cell['metrics'].items()):
            if m.get('n') != 24:
                raise ExportError(f'{key} {metric}: n = {m.get("n")}, not 24')
            lo, hi = m['interval_log']
            higher = metric == 'requests_per_s'
            ci = [v100q.pct(-hi), v100q.pct(-lo)] if higher else [v100q.pct(lo), v100q.pct(hi)]
            extra: Dict[str, Any] = {'experiment': 'V2', 'role': 'deciding'}
            if m['class'] == 'TIMER_LIMITED':
                extra['class_without_limit'] = m['class_without_limit']
                extra['measurement_limit_log'] = m['limit_log']
            rows.append(v100q.row(key, metric, v100q.unit_of(metric), 'higher' if higher else 'lower',
                                  m['cf_median'], m['ref_median'], m['n'], m['class'],
                                  v100q.CI_24 + (HIGHER if higher else ''), EVIDENCE_URL, ci, **extra))
    return rows


def cell_of(r: Dict[str, Any]) -> str:
    return r['scenario'].removesuffix(' (supporting)')


def add_dispositions(rows: List[Dict[str, Any]]) -> None:
    by_cell: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_cell.setdefault(cell_of(r), []).append(r)
    for cell in D3_CELLS:
        if cell not in by_cell:
            raise ExportError(f'D3 cell {cell} is not in the analyses')
        if all(r['verdict'] == 'PASS' for r in by_cell[cell]):
            raise ExportError(f'D3 cell {cell} has no non-PASS row')
        for r in by_cell[cell]:
            if r['verdict'] != 'PASS':
                r['disposition'] = D3
    for r in rows:
        if r['verdict'] != 'PASS' and 'disposition' not in r:
            raise ExportError(f'{r["scenario"]} {r["metric"]}: {r["verdict"]} without a recorded disposition')


def build(a: Dict[str, Any], cf5: Dict[str, Any]) -> Dict[str, Any]:
    rows = v1_rows(a) + v2_rows(cf5['cells'])
    add_dispositions(rows)
    comparison = {'candidate_sha': CANDIDATE_SHA, 'reference_version': '1.0.0', 'reference_sha': REFERENCE_SHA,
                  'campaign_url': CAMPAIGN_URL, 'environment': ENVIRONMENT, 'results': rows}
    return {'version': VERSION, 'status': 'published', 'release_label': VERSION,
            'qualification_decision': DECISION, 'decision_url': DECISION_URL, 'qualification_note': NOTE,
            'baseline_policy': BASELINE_POLICY, 'comparisons': [comparison], 'schema_version': 2}


def merge(data: Dict[str, Any], entry: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(data)
    out['schema_version'] = max(out['schema_version'], 2)
    out['releases'] = [entry] + [r for r in out['releases'] if r['version'] != VERSION]
    build_site.validate(out)
    return out


def main() -> int:
    if not (CAMPAIGN / 'DECISION.md').is_file():
        print('export refused: the decision record does not exist', file=sys.stderr)
        return 2
    try:
        entry = build(load(ANALYSIS / 'analysis-session1-V1.json'), load(ANALYSIS / 'analysis-session1.json'))
        data = merge(load(RELEASES), entry)
    except (ExportError, AssertionError, KeyError, TypeError) as error:
        print(f'export refused: {error!r}', file=sys.stderr)
        return 2
    RELEASES.write_text(json.dumps(data, indent=1) + '\n')
    counts: Dict[str, int] = {}
    for r in entry['comparisons'][0]['results']:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
    print(f'{VERSION}: {sum(counts.values())} rows {counts}; written to docs/data/releases.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
