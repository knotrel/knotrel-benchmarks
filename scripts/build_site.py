#!/usr/bin/env python3
"""Generate the static performance site from validated release and engine-comparison summaries."""
import argparse
import html
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
REPO = 'https://github.com/knotrel/knotrel-benchmarks'


def esc(value):
    """Escape all dataset content before rendering HTML."""
    return html.escape(str(value), quote=True)


#: Schema 1 verdicts. Schema 1 rows keep exactly these rules.
VERDICTS_V1 = ('PASS', 'FAIL', 'REGRESSION', 'INCONCLUSIVE', 'INVALID', 'NOT_EQUIVALENT')
#: Every measured class an analyzer of the v1.0.0 plan can emit (plan section 7), kept verbatim:
#: none is converted into PASS or merged into another.
MEASURED_VERDICTS = VERDICTS_V1 + ('PASS (IMPROVED)', 'INCONCLUSIVE_DISCLOSED', 'UNRESOLVED',
                                   'TIMER_LIMITED', 'EXCEEDS_BUDGET')
NOT_RUN = 'NOT_RUN'
#: Schema 2 verdict tokens. JSON null (no verdict) is valid only with status ``nonconforming``.
VERDICTS = MEASURED_VERDICTS + (NOT_RUN,)
#: Role of a row in the campaign's decision rule (docs/SITE.md).
CATEGORIES = ('decisive', 'descriptive', 'disclosure')
#: Execution status -> the verdicts it admits (None = no verdict). Closed set (docs/SITE.md).
STATUS_VERDICTS = {
    'completed': MEASURED_VERDICTS,
    'not_run': (NOT_RUN,),
    'nonconforming': (None,),
    'failed': ('FAIL', 'INVALID'),
}
STATUSES = tuple(STATUS_VERDICTS)
#: How a schema 1 row is read. Schema 1 could only express complete rows that carry a campaign
#: verdict with every estimate, so these defaults restate it; the stored row is never rewritten.
LEGACY_DEFAULTS = {'category': 'decisive', 'status': 'completed'}
#: Fields that hold measured values; a row that is not ``completed`` has none of them.
MEASUREMENTS = ('candidate', 'reference', 'delta_pct', 'candidate_ci95', 'reference_ci95', 'delta_ci95', 'runs')
EXACT_VERSION = r'\d+\.\d+\.\d+'


def row_schema(release):
    """Row schema of a release entry: its ``schema_version``, 1 when absent (older entries)."""
    return release.get('schema_version', 1)


def outcome(row, schema):
    """(verdict, category, status) of a row, applying the documented schema 1 defaults."""
    if schema == 1:
        return row['verdict'], LEGACY_DEFAULTS['category'], LEGACY_DEFAULTS['status']
    return row['verdict'], row['category'], row['status']


def nonempty(value):
    return isinstance(value, str) and value.strip() != ''


def validate_measurements(row):
    """Estimates, delta and intervals of a completed row (unchanged schema 1 rules)."""
    assert isinstance(row['ci_method'], str) and row['ci_method']
    assert isinstance(row['runs'], int) and row['runs'] > 0
    for key in ('candidate', 'reference', 'delta_pct'):
        assert isinstance(row[key], (int, float)) and math.isfinite(row[key])
    assert row['candidate'] >= 0 and row['reference'] > 0
    expected = 100 * (row['candidate'] / row['reference'] - 1)
    assert abs(expected - row['delta_pct']) < 0.05, 'Delta disagrees with estimates'
    for key in ('candidate_ci95', 'reference_ci95', 'delta_ci95'):
        interval = row.get(key)
        if interval is None:
            assert row.get('ci_unavailable_reason'), 'Explain unavailable uncertainty'
        else:
            assert len(interval) == 2 and all(math.isfinite(x) for x in interval)
            assert interval[0] <= interval[1]


def validate_row_v1(row):
    for key in ('scenario', 'metric', 'unit', 'direction', 'verdict', 'ci_method'):
        assert isinstance(row[key], str) and row[key]
    assert row['direction'] in ('lower', 'higher')
    assert row['verdict'] in VERDICTS_V1, 'Unknown schema 1 verdict'
    validate_measurements(row)


def validate_row_v2(row):
    for key in ('scenario', 'metric'):
        assert nonempty(row[key])
    verdict, category, status = row.get('verdict', 'missing'), row.get('category'), row.get('status')
    assert verdict is None or verdict in VERDICTS, f'Unknown verdict {verdict!r}'
    assert category in CATEGORIES, f'Unknown category {category!r}'
    assert status in STATUSES, f'Unknown status {status!r}'
    assert verdict in STATUS_VERDICTS[status], f'Verdict {verdict!r} is impossible with status {status}'
    if row.get('direction') is not None:
        assert row['direction'] in ('lower', 'higher')
    if status == 'completed' and row.get('estimate_unavailable_reason') is not None:
        validate_rule_row(row)
    elif status == 'completed':
        for key in ('unit', 'direction'):
            assert nonempty(row[key])
        assert not isinstance(row['runs'], bool)
        validate_measurements(row)
    else:
        assert nonempty(row.get('status_reason')), f'A {status} row requires a status_reason'
        measured = [key for key in MEASUREMENTS if row.get(key) is not None]
        assert not measured, f'A {status} row cannot carry measurements: {measured}'


def validate_rule_row(row):
    """A completed row whose verdict has no ratio or interval (a rule, or a zero reference).

    The reason is mandatory; no delta or interval may appear, and any value shown is finite."""
    assert nonempty(row['estimate_unavailable_reason']), 'Explain the missing estimate'
    present = [key for key in ('delta_pct', 'candidate_ci95', 'reference_ci95', 'delta_ci95') if row.get(key) is not None]
    assert not present, f'A row without an estimate cannot carry {present}'
    for key in ('candidate', 'reference'):
        value = row.get(key)
        if value is not None:
            assert isinstance(value, (int, float)) and not isinstance(value, bool)
            assert math.isfinite(value) and value >= 0
    runs = row.get('runs')
    if runs is not None:
        assert isinstance(runs, int) and not isinstance(runs, bool) and runs > 0
    if row.get('candidate') is not None or row.get('reference') is not None:
        assert nonempty(row.get('unit')), 'A shown value needs its unit'


def validate_comparison(comparison, schema):
    for field in ('candidate_sha', 'reference_sha'):
        assert re.fullmatch(r'[0-9a-f]{40}', comparison[field] or ''), field
    assert re.fullmatch(EXACT_VERSION, comparison['reference_version'] or '')
    assert comparison['environment'] and comparison['results']
    assert comparison['campaign_url'].startswith('https://')
    for row in comparison['results']:
        (validate_row_v1 if schema == 1 else validate_row_v2)(row)
        assert row['evidence_url'].startswith('https://')


#: Release-level qualification decisions (docs/SITE.md). Closed set; a decision never changes a row verdict.
DECISIONS = ('accepted', 'accepted with exceptions', 'not accepted')
#: The exact release a report describes, e.g. 1.0.0-rc.1 for the 1.0.0 entry.
RELEASE_LABEL = r'(\d+\.\d+\.\d+)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?'


def validate_release_decision(release):
    """A published schema 2 entry names its exact release and the maintainer's qualification decision."""
    match = re.fullmatch(RELEASE_LABEL, str(release.get('release_label', '')))
    assert match, 'A published schema 2 release requires an exact release_label'
    assert match.group(1) == release['version'], 'release_label must belong to the entry version'
    assert release.get('qualification_decision') in DECISIONS, 'Unknown or missing qualification_decision'
    url = release.get('decision_url')
    assert isinstance(url, str) and url.startswith('https://'), 'A published schema 2 release requires an HTTPS decision_url'
    note = release.get('qualification_note')
    assert note is None or (isinstance(note, str) and note.strip()), 'qualification_note must be nonempty text'


def release_label(release):
    """The exact release a report describes (the entry version for schema 1 and planned entries)."""
    return release.get('release_label') or release['version']


def is_prerelease(release):
    return '-' in release_label(release)


def validate(data):
    """Reject ambiguous identities and incomplete published evidence."""
    if not __debug__:
        raise RuntimeError('Validation requires Python without -O')
    assert data['schema_version'] in (1, 2), 'Unsupported schema'
    seen = set()
    for release in data['releases']:
        version = release['version']
        assert re.fullmatch(EXACT_VERSION, version), 'Exact version required'
        assert version not in seen, 'Duplicate version'
        seen.add(version)
        assert release['status'] in ('planned', 'published')
        assert isinstance(release['baseline_policy'], str)
        schema = row_schema(release)
        assert schema in (1, 2) and not isinstance(schema, bool), 'Unsupported release schema'
        assert schema <= data['schema_version'], 'Release schema newer than the dataset schema'
        if release['status'] == 'planned':
            assert not release.get('comparisons'), 'Planned releases cannot contain measurements'
            continue
        assert release['comparisons'], 'Published release requires comparisons'
        if schema == 2:
            validate_release_decision(release)
        references = set()
        for comparison in release['comparisons']:
            assert comparison['reference_version'] not in references, 'Duplicate reference'
            references.add(comparison['reference_version'])
            validate_comparison(comparison, schema)


def icon(name):
    """Return a decorative, dependency-free SVG with consistent stroke weight."""
    paths = {
        'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
        'moon': '<path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/>',
        'chart': '<path d="M4 3v17h17M8 16v-5m5 5V7m5 9V4"/>',
        'layers': '<path d="m3 7 9-4 9 4-9 4-9-4Zm0 5 9 4 9-4M3 17l9 4 9-4"/>',
        'compare': '<path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/>',
        'measure': '<path d="m3 15 12-12 6 6L9 21l-6-6Zm7-7 3 3m1-7 3 3M6 12l3 3"/>',
        'arrow': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
        'engine': '<path d="M5 6h4v4H5zM15 14h4v4h-4zM15 6h4v4h-4zM9 8h6M17 10v4M7 10v6a2 2 0 0 0 2 2h6"/>',
        'external': '<path d="M14 3h7v7m0-7L10 14M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-6"/>',
    }
    return f'<svg class="icon icon-{name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>'


def page(title, content, prefix='', active='Overview'):
    """Render a page with paths that also work under project Pages URLs."""
    links = [('Overview', 'index.html'), ('Releases', 'releases.html'), ('Engines', 'engines.html'),
             ('Competitors', 'competitors.html'), ('Methodology', 'methodology.html')]
    nav_icons = {'Overview': 'chart', 'Releases': 'layers', 'Engines': 'engine', 'Competitors': 'compare',
                 'Methodology': 'measure'}
    nav = ''.join(f'<a {"aria-current=page" if label == active else ""} href="{prefix}{url}">{icon(nav_icons[label])}<span>{label}</span></a>' for label, url in links)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | Knotrel Performance</title><meta name="description" content="Reproducible Knotrel release performance, uncertainty and benchmark evidence.">
<link rel="icon" href="{prefix}assets/mark.svg"><link rel="stylesheet" href="{prefix}assets/performance.css">
<script src="{prefix}assets/site.js" defer></script></head><body>
<a class="skip" href="#main">Skip to content</a><header><a class="brand" href="{prefix}index.html"><img src="{prefix}assets/mark.svg" alt="" width="30" height="30">Knotrel <span>Performance</span></a><nav aria-label="Main">{nav}</nav><button id="theme" class="theme-button" type="button" aria-label="Switch to light mode" title="Switch to light mode">{icon("sun")}{icon("moon")}</button></header>
<main id="main">{content}</main><footer><div><strong>Knotrel Performance</strong><p>Measurements with context. Evidence you can inspect.</p></div><div><a href="https://knotrel.github.io/knotrel/">Knotrel documentation ↗</a><a href="{REPO}">Benchmark repository ↗</a><a href="{prefix}data/releases.json">Release data · JSON</a><a href="{prefix}data/engine-comparisons.json">Engine data · JSON</a></div></footer></body></html>'''


def badges(r):
    """Status, prerelease and qualification decision badges of a release entry."""
    out = f'<span class="badge">{esc(r["status"])}</span>'
    if is_prerelease(r):
        out += ' <span class="badge">prerelease</span>'
    if r.get('qualification_decision'):
        out += f' <span class="badge">qualification {esc(r["qualification_decision"])}</span>'
    return out


def decision_note(r, link=True):
    """One sentence stating the release kind and the qualification decision, with its record."""
    if r['status'] != 'published' or not r.get('qualification_decision'):
        return ''
    kind = ('a release candidate (prerelease), not a stable release' if is_prerelease(r) else 'a stable release')
    return (f'<p class="note">Knotrel {esc(release_label(r))} is {kind}. Performance qualification: '
            f'<strong>{esc(r["qualification_decision"])}</strong>'
            + (f' (<a href="{esc(r["decision_url"])}">decision record ↗</a>)' if link else '') + '. '
            'Every verdict below is shown as measured; an exception does not change it.'
            + (f' {esc(r["qualification_note"])}' if r.get('qualification_note') else '') + '</p>')


def cards(releases):
    return ''.join(f'<a class="card release" href="releases/{r["version"]}.html">{badges(r)}<h3>v{esc(release_label(r))} <span>{icon("arrow")}</span></h3><p>{esc(r["baseline_policy"])}</p>{decision_note(r, link=False)}</a>' for r in releases)


def interval(value):
    return 'Not available' if value is None else f'[{value[0]:.3g}, {value[1]:.3g}]'


TONES = {'PASS': 'ok', 'PASS (IMPROVED)': 'ok', 'FAIL': 'bad', 'REGRESSION': 'bad', 'INVALID': 'bad',
         'NOT_EQUIVALENT': 'bad', 'INCONCLUSIVE': 'warn', 'INCONCLUSIVE_DISCLOSED': 'warn', 'UNRESOLVED': 'warn',
         'TIMER_LIMITED': 'info', 'EXCEEDS_BUDGET': 'info', NOT_RUN: 'none', None: 'none'}
MEASURE_COLUMNS = ('Reference', 'Reference CI', 'Candidate', 'Candidate CI', 'Change', 'Change CI', 'Runs')
COLUMNS = ('Scenario', 'Metric', 'Direction', 'Verdict', 'Category', 'Status') + MEASURE_COLUMNS + (
    'CI method', 'CI limitation', 'Disposition', 'Source')
CATEGORY_TEXT = {
    'decisive': 'Enters the campaign decision rule; a non-PASS verdict needs a recorded maintainer disposition.',
    'descriptive': 'Reported for context; it does not enter the decision rule.',
    'disclosure': 'Reported by rule and never converted; it does not block the release.',
}
STATUS_TEXT = {
    'completed': 'Measured and analyzed. Estimates are shown; a rule verdict, or a ratio with a zero reference, shows "Not available" and says why.',
    'not_run': 'Not measured (for example, after a product failure stopped its experiment). The reason is shown; there are no numbers.',
    'nonconforming': 'Its block did not conform to the protocol (for example, a time cap). No verdict and no numbers.',
    'failed': 'Ran without an analyzable result (a product failure or an invalid observation). The reason is shown; there are no numbers.',
}


def label(token):
    """Readable text for a category or status token."""
    return token.replace('_', ' ')


def verdict_badge(verdict):
    """The verdict exactly as measured; color only repeats what the text says."""
    text = 'No verdict' if verdict is None else verdict
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return f'<span class="verdict tone-{TONES[verdict]} verdict-{slug}">{esc(text)}</span>'


def result_row(x, schema):
    """One table row; a row that is not completed shows its reason instead of numbers."""
    verdict, category, status = outcome(x, schema)
    direction = f"{x['direction']} is better" if x.get('direction') else 'Not stated'
    cells = [f'<td>{esc(v)}</td>' for v in (x['scenario'], x['metric'], direction)]
    cells += [f'<td>{verdict_badge(verdict)}</td>', f'<td><span class="category">{esc(label(category))}</span></td>',
              f'<td><span class="run-status status-{status}">{esc(label(status))}</span></td>']
    if status == 'completed':
        def value(key):
            return 'Not available' if x.get(key) is None else f'{x[key]} {x["unit"]}'
        change = 'Not available' if x.get('delta_pct') is None else f'{x["delta_pct"]:+.2f}%'
        cells += [f'<td>{esc(v)}</td>' for v in (
            value('reference'), interval(x.get('reference_ci95')), value('candidate'),
            interval(x.get('candidate_ci95')), change, interval(x.get('delta_ci95')), x.get('runs') or 'Not stated')]
    else:
        cells.append(f'<td class="no-measure" colspan="{len(MEASURE_COLUMNS)}"><strong>No measurements.</strong> '
                     f'{esc(label(status).capitalize())}: {esc(x["status_reason"])}</td>')
    limitation = '; '.join(v for v in (x.get('estimate_unavailable_reason'), x.get('ci_unavailable_reason')) if v)
    cells += [f'<td>{esc(v)}</td>' for v in (x.get('ci_method', ''), limitation,
                                             x.get('disposition', 'None'))]
    cells.append(f'<td><a href="{esc(x["evidence_url"])}">Evidence</a></td>')
    return '<tr>' + ''.join(cells) + '</tr>'


def legend():
    """Definitions of the category and status labels used in the tables."""
    items = ''.join(f'<div><dt><span class="category">{esc(label(k))}</span></dt><dd>{esc(v)}</dd></div>'
                    for k, v in CATEGORY_TEXT.items())
    items += ''.join(f'<div><dt><span class="run-status status-{k}">{esc(label(k))}</span></dt><dd>{esc(v)}</dd></div>'
                     for k, v in STATUS_TEXT.items())
    return ('<h2>Reading the tables</h2><p>Each row has three separate fields: the <strong>verdict</strong> exactly as '
            'the campaign analyzer measured it, its <strong>category</strong> in the decision rule, and its '
            '<strong>execution status</strong>. No verdict is converted into another.</p>'
            f'<dl class="legend">{items}</dl>')


def confidence_plot(rows, schema=1):
    """Render each relative estimate on its own labeled symmetric percent axis."""
    plots = []
    for row in rows:
        ci = row.get('delta_ci95')
        verdict, _, status = outcome(row, schema)
        if ci is None or status != 'completed' or verdict in ('INVALID', 'NOT_EQUIVALENT'):
            continue
        bound = max(1, abs(ci[0]), abs(ci[1]), abs(row['delta_pct'])) * 1.15
        def position(value):
            return 240 + value / bound * 200
        # Schema 2 intervals need not be 95 % intervals: their coverage is in ci_method.
        name = '95% CI' if schema == 1 else 'interval (method in the table)'
        caption = f"{row['scenario']} / {row['metric']}: {row['delta_pct']:+.2f}%, {name} {interval(ci)}; {row['direction']} is better"
        plots.append(f'''<figure class="card"><figcaption>{esc(caption)}</figcaption>
<svg viewBox="0 0 480 90" role="img" aria-label="{esc(caption)}">
<line x1="40" x2="440" y1="36" y2="36" stroke="var(--line)"/>
<line x1="240" x2="240" y1="16" y2="57" stroke="var(--muted)" stroke-dasharray="3 3"/>
<line x1="{position(ci[0]):.2f}" x2="{position(ci[1]):.2f}" y1="36" y2="36" stroke="var(--accent)" stroke-width="4"/>
<circle cx="{position(row['delta_pct']):.2f}" cy="36" r="6" fill="var(--accent)"/>
<text x="40" y="78" fill="var(--muted)" font-size="12">−{bound:.1f}%</text>
<text x="240" y="78" text-anchor="middle" fill="var(--muted)" font-size="12">0%</text>
<text x="440" y="78" text-anchor="end" fill="var(--muted)" font-size="12">+{bound:.1f}%</text></svg></figure>''')
    return '<div class="interval-plots">' + ''.join(plots) + '</div>' if plots else ''


def hero_link(releases):
    first = next((r for r in releases if r['version'] == '1.0.0'), None)
    if first is not None and first['status'] == 'published':
        return f'Explore the {release_label(first)} results'
    return 'Explore the 1.0.0 plan'


# Engine comparisons (docs/data/engine-comparisons.json): engines compared on one build, not one
# release against another. Classes and family statements are copied from the campaign analyzer
# by an exporter (scripts/export_cf5_site.py) and shown exactly as computed.
ENGINE_SCHEMA = 1
ENGINE_STATEMENTS = ('prefer cluster-forest', 'prefer reference', 'mixed results', 'insufficient evidence',
                     'no difference beyond the margins', 'isolated differences')
ENGINE_CLASSES = ('FASTER', 'SLOWER', 'EQUIVALENT', 'INCONCLUSIVE', 'TIMER_LIMITED', 'SMALLER', 'LARGER', 'SIMILAR')
ENGINE_CLASS_TEXT = {
    'FASTER': 'cluster-forest faster beyond the margin',
    'SLOWER': 'cluster-forest slower beyond the margin',
    'EQUIVALENT': 'difference within the margin',
    'INCONCLUSIVE': 'interval too wide to decide',
    'TIMER_LIMITED': 'difference not resolvable at the measurement limit; not counted',
    'SMALLER': 'cluster-forest uses less memory (deterministic count)',
    'LARGER': 'cluster-forest uses more memory (deterministic count)',
    'SIMILAR': 'memory within the margin',
}
STATEMENT_TEXT = {
    'prefer cluster-forest': 'the family favours cluster-forest',
    'prefer reference': 'the family favours the reference engine',
    'mixed results': 'classes point in different directions',
    'insufficient evidence': 'a non-conclusive cell (INCONCLUSIVE or TIMER_LIMITED) prevents a statement',
    'no difference beyond the margins': 'every class is within the margins',
    'isolated differences': 'within the margins except a few cells',
}
STABLE_LINK = r'https://github\.com/[\w.-]+/[\w.-]+/(blob|tree)/[0-9a-f]{40}/\S+'
ENGINE_NAMES = {'compact-bfs': 'compact-bfs', 'ett': 'ETT', 'hdt': 'HDT'}


def validate_engines(data):
    """Reject engine comparisons without a stable report, limitations or analyzer classes."""
    if not __debug__:
        raise RuntimeError('Validation requires Python without -O')
    assert data['schema_version'] == ENGINE_SCHEMA, 'Unsupported engine-comparison schema'
    seen = set()
    for c in data['comparisons']:
        assert re.fullmatch(r'[a-z0-9][a-z0-9-]*', c['id']) and c['id'] not in seen, 'Unique slug id required'
        seen.add(c['id'])
        for key in ('title', 'kind', 'candidate_engine', 'campaign', 'environment', 'method', 'decision'):
            assert nonempty(c.get(key)), f'Engine comparison requires {key}'
        for key in ('candidate_sha', 'tooling_sha'):
            assert re.fullmatch(r'[0-9a-f]{40}', c[key]), f'{key} must be a 40-character SHA'
        for key in ('report_url', 'evidence_url'):
            assert re.fullmatch(STABLE_LINK, c[key]), f'{key} must be a commit permalink'
        assert c['limitations'] and all(nonempty(x) for x in c['limitations']), 'Limitations required'
        assert c['reference_engines'], 'Reference engines required'
        assert c['families'], 'Family statements required'
        for family in c['families']:
            assert nonempty(family['family']) and nonempty(family['description'])
            assert family['scope'] in ('core', 'end-to-end')
            assert family['against'], 'A family needs at least one reference'
            for a in family['against']:
                assert a['reference'] in c['reference_engines']
                assert a['statement'] in ENGINE_STATEMENTS, f'Unknown statement: {a["statement"]}'
                assert a['classes'] and set(a['classes']) <= set(ENGINE_CLASSES), 'Unknown class'
                assert a['cells'] > 0
        for b in c['block_counts']:
            assert set(b['classes']) <= set(ENGINE_CLASSES), 'Unknown class'
        rules = c['lifecycle_rules']
        assert set(rules['counts']) == {'C1', 'C2', 'C3', 'C4'}
        assert len(rules['c3_fail']) == rules['counts']['C3'].get('FAIL', 0), 'Every C3 FAIL must be listed'
        assert len(rules['c4_exceeds_budget']) == rules['counts']['C4'].get('EXCEEDS_BUDGET', 0), \
            'Every C4 EXCEEDS_BUDGET must be listed'
        if rules['c3_fail']:
            assert nonempty(c.get('lifecycle_disposition')), 'A C3 FAIL needs its recorded disposition'


def engine_name(ref):
    return ENGINE_NAMES.get(ref, ref)


def class_list(classes):
    return ', '.join(f'{n} {esc(k)}' for k, n in classes.items())


def spaced(n):
    """Thousands separated by a space, as in the campaign report."""
    return f'{n:,.0f}'.replace(',', ' ')


def ratio_text(r):
    if r is None:
        return ''
    low, high = r
    text = f'{low:g}×' if low == high else f'{low:g}× to {high:g}×'
    return f'<br><small>median ratio {text}</small>'


def engine_family_table(c):
    refs = c['reference_engines']
    head = ''.join(f'<th scope="col">vs {esc(engine_name(r))}</th>' for r in refs)
    rows = ''
    for f in c['families']:
        by_ref = {a['reference']: a for a in f['against']}
        sizes = ', '.join(spaced(n) for n in f['sizes']) or 'see report'
        cells = ''
        for r in refs:
            a = by_ref.get(r)
            if a is None:
                cells += '<td>not compared</td>'
                continue
            cells += (f'<td><strong>{esc(a["statement"])}</strong><br><small>{class_list(a["classes"])}'
                      f' ({a["cells"]} cells: {esc(", ".join(a["blocks"]))})</small>{ratio_text(a["median_ratio"])}</td>')
        rows += (f'<tr><th scope="row"><code>{esc(f["family"])}</code><br><small>{esc(f["description"])}. '
                 f'Sizes: {esc(sizes)}. Scope: {esc(f["scope"])}.</small></th>{cells}</tr>')
    return ('<div class="table-wrap" role="region" aria-label="Scrollable family table"><table class="wrap">'
            '<caption>Family statements as computed by the analyzer, with the classes of every metric of the '
            "family's cells and the range of their median paired ratio (timed metrics only).</caption><thead><tr>"
            f'<th scope="col">Family, workload, sizes (vertices)</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>')


def lifecycle_table(entries, caption):
    rows = ''.join(
        f'<tr><td><code>{esc(e["run"])}</code></td><td>{esc(e["workload"])}</td><td>{esc(e["graph"])}</td>'
        f'<td>{spaced(e["nodes"])}</td><td>{esc(e["metric"])}</td><td>{e["late_over_early"]:.3f}</td>'
        f'<td><strong>{e["projected_growth_30_pct"]:+.1f} %</strong> (projected from the slope)</td>'
        f'<td>{spaced(e["first_bytes"])} → {spaced(e["last_bytes"])} B</td></tr>'
        for e in entries)
    return ('<div class="table-wrap" role="region" aria-label="Scrollable lifecycle table"><table class="wrap">'
            f'<caption>{esc(caption)}</caption><thead><tr><th scope="col">Run</th><th scope="col">Workload</th>'
            '<th scope="col">Graph</th><th scope="col">Nodes</th><th scope="col">Metric</th>'
            '<th scope="col">Late / early</th><th scope="col">Projected 30-cycle growth</th>'
            f'<th scope="col">First → last</th></tr></thead><tbody>{rows}</tbody></table></div>')


def engine_page(c):
    cand = esc(c['candidate_engine'])
    refs = esc(', '.join(engine_name(r) for r in c['reference_engines']))
    limits = ''.join(f'<li>{esc(x)}</li>' for x in c['limitations'])
    counts_rows = ''.join(f'<tr><th scope="row">{esc(b["block"])}</th><td>vs {esc(engine_name(b["reference"]))}</td>'
                          f'<td>{class_list(b["classes"])}</td></tr>' for b in c['block_counts'])
    rules = c['lifecycle_rules']
    rule_counts = ''.join(f'<li><strong>{k}</strong>: {class_list(v)}</li>' for k, v in rules['counts'].items())
    statements = ''.join(f'<div><dt><strong>{esc(k)}</strong></dt><dd>{esc(v)}</dd></div>'
                         for k, v in STATEMENT_TEXT.items())
    classes = ''.join(f'<div><dt><code>{esc(k)}</code></dt><dd>{esc(v)}</dd></div>' for k, v in ENGINE_CLASS_TEXT.items())
    sha = c['candidate_sha']
    parts = [
        '<p class="eyebrow">ENGINE COMPARISON / ONE BUILD / NOT A RELEASE COMPARISON</p>',
        f'<h1>{cand} compared with {refs}</h1>',
        f'<p class="lead">Connectivity engines measured on the <strong>same Knotrel build</strong> (candidate '
        f'<code>{sha[:7]}</code>), on the same host and inputs. This page compares engines, not one release with '
        'another. Results hold only for the workloads, sizes, host and build measured.</p>',
        f'<p class="note"><strong>Limitation.</strong> {esc(c["limitations"][0])}</p>',
        f'<p class="note"><strong>Decision.</strong> {esc(c["decision"])}</p>',
        f'<p><a class="icon-link" href="{esc(c["report_url"])}">Full campaign report {icon("external")}</a> '
        f'&middot; <a class="icon-link" href="{esc(c["evidence_url"])}">Analysis and checksums {icon("external")}</a></p>',
        '<h2>Results by workload family</h2>',
        f'<p>A median ratio below 1× favours {cand}: {cand} over the reference for times and tails, the reference '
        f'over {cand} for throughput. Core and end-to-end results are kept apart.</p>',
        engine_family_table(c),
        '<p>"Not compared": that reference has no cell in the family; ETT and HDT have no lifecycle support, so '
        'the lifecycle families are compared with compact-bfs only.</p>',
        '<h2>Lifecycle memory rules (L2)</h2>',
        f'<p>Sustained lifecycle churn on {cand}, checked by the C rules: C1 engine vertices, C2 exact logical '
        'counts, C3 heap growth (late/early at most 1.25 and projected 30-cycle growth at most 10 %), C4 RSS growth '
        'with the same rules, as a disclosure.</p>',
        f'<ul>{rule_counts}</ul>',
        f'<h3>C3 FAIL ({len(rules["c3_fail"])})</h3>',
        '<p>The growth figures are <strong>projected from the slope</strong> of the heap curve to 30 cycles, '
        'not measured growth.</p>',
        lifecycle_table(rules['c3_fail'], 'C3 FAIL runs: the class stays FAIL.'),
        f'<p class="note"><strong>Disposition.</strong> {esc(c.get("lifecycle_disposition", ""))}</p>',
        f'<h3>C4 EXCEEDS_BUDGET ({len(rules["c4_exceeds_budget"])})</h3>',
        '<p>A disclosure category (allocator retention in RSS), never converted into PASS or FAIL.</p>',
        lifecycle_table(rules['c4_exceeds_budget'], 'C4 EXCEEDS_BUDGET runs, disclosed with their numbers.'),
        '<h2>Class counts per block</h2>',
        '<div class="table-wrap" role="region" aria-label="Scrollable class count table"><table>'
        '<caption>Every metric class of the engine blocks, as computed.</caption><thead><tr><th scope="col">Block</th>'
        f'<th scope="col">Reference</th><th scope="col">Classes</th></tr></thead><tbody>{counts_rows}</tbody></table></div>',
        '<h2>Method and perimeter</h2>',
        f'<ul><li>Campaign: {esc(c["campaign"])}</li><li>Candidate <code>{sha}</code>, tooling '
        f'<code>{c["tooling_sha"]}</code></li><li>Host: {esc(c["environment"])}</li><li>{esc(c["method"])}</li>'
        f'{limits}</ul>',
        '<h2>Reading this page</h2>',
        f'<dl class="legend">{statements}</dl><dl class="legend">{classes}</dl>',
    ]
    return page(c['title'], ''.join(parts), '../', 'Engines')


def engines_index(comparisons):
    if not comparisons:
        body = '<div class="empty"><h2>No engine comparison published yet.</h2></div>'
    else:
        body = '<div class="grid">' + ''.join(
            f'<a class="card release" href="engines/{c["id"]}.html"><span class="badge">{esc(c["kind"])}</span>'
            f'<h3>{esc(c["title"])} <span>{icon("arrow")}</span></h3><p>Candidate <code>{c["candidate_sha"][:7]}</code>. '
            f'{esc(c["decision"])}</p><p class="note">{esc(c["limitations"][0])}</p></a>' for c in comparisons) + '</div>'
    return page('Engine comparisons',
                '<p class="eyebrow">ENGINE COMPARISONS</p><h1>Same build.<br>Different engines.</h1><p class="lead">'
                'Connectivity engines compared on one Knotrel build. These pages do not compare releases: release '
                f'reports are under <a href="releases.html">Releases</a>.</p>{body}', active='Engines')


def generate(data, engines=None):
    """Build deterministic pages without running any benchmarks."""
    validate(data)
    engines = engines or {'schema_version': ENGINE_SCHEMA, 'comparisons': []}
    validate_engines(engines)
    releases = data['releases']
    published = sum(r['status'] == 'published' for r in releases)
    outputs = {}
    outputs['index.html'] = page('Performance, in context', f'''
<section class="hero"><p class="eyebrow">KNOTREL / BENCHMARK OBSERVATORY</p><h1>Performance.<br><em>With the evidence.</em></h1><p class="lead">Explore how Knotrel changes across releases. Response times, memory and CPU, with uncertainty and reproducible comparisons.</p><div class="actions"><a class="button primary" href="releases/1.0.0.html">{icon("chart")}<span>{esc(hero_link(releases))}</span>{icon("arrow")}</a><a class="button" href="methodology.html">{icon("measure")}<span>How we measure</span></a></div><div class="summary"><div><strong>{published:02}</strong><span>Published release reports</span></div><div><strong>1.0.0</strong><span>First release in this series</span></div><div><strong>95%</strong><span>Target confidence level</span></div></div></section>
<section><div class="section-title"><div><p class="eyebrow">RELEASE TRACKER</p><h2>A baseline for every change.</h2></div><a href="releases.html" class="icon-link">All releases {icon("arrow")}</a></div><div class="grid">{cards(releases)}</div><p class="note">The public series starts at 1.0.0 against a frozen 0.9.x reference. Planned reports contain no measurements. Published reports link to their campaign evidence.</p></section>
<section><p class="eyebrow">THREE VIEWS, ONE WORKLOAD</p><h2>Speed is only part of the story.</h2><div class="grid"><article class="card"><span class="number">01 / LATENCY</span><h3>How long do answers take?</h3><p>p50, p95 and p99 alongside throughput, failures and update visibility.</p></article><article class="card"><span class="number">02 / MEMORY</span><h3>What does the graph cost?</h3><p>Steady and peak memory. Heap and RSS, with process boundaries made explicit.</p></article><article class="card"><span class="number">03 / CPU</span><h3>How much work gets done?</h3><p>CPU time and utilization, interpreted against successful operations and offered load.</p></article></div></section>
<section><div class="section-title"><div><p class="eyebrow">ENGINE COMPARISONS</p><h2>Same build. Different engines.</h2></div><a href="engines.html" class="icon-link">All engine comparisons {icon("arrow")}</a></div><p>Engines measured on one Knotrel build, separate from the release reports: for example cluster-forest against compact-bfs, ETT and HDT (CF5, candidate 02cba68).</p></section>
<section class="callout"><p class="eyebrow">EXTERNAL COMPARISONS</p><h2>Same question. Different systems.</h2><p>Neo4j and PostgreSQL comparisons are planned after 1.1.0 and selected profiling work. Freshness, atomicity and full-stack costs are part of the comparison.</p><a href="competitors.html" class="icon-link">{icon("compare")}View the experiment scope {icon("arrow")}</a></section>''')
    outputs['releases.html'] = page('Release explorer', f'<p class="eyebrow">RELEASE EXPLORER</p><h1>Every release.<br>Its own evidence.</h1><p class="lead">Exact references are selected at campaign freeze and remain attached to that report.</p><div class="grid">{cards(releases)}</div><h2>Reference selection</h2><ol><li>Previous patch in the same minor, if available.</li><li>Latest patch of the previous available minor.</li><li>Latest patch of the previous major.</li><li>1.0.0 on the stable longitudinal workload subset.</li></ol><p>Duplicate references are removed. For 1.0.0, use the latest released 0.9.x patch at freeze. Missing or incompatible comparisons are explained, never filled with historical ratios from another environment.</p>', active='Releases')
    for r in releases:
        if r['status'] == 'planned':
            detail = '<div class="empty"><span class="badge">Awaiting campaign</span><h2>No measurements published yet.</h2><p>This is a comparison plan, not a performance verdict. Charts and estimates will appear only when validated evidence is available.</p></div>'
        else:
            detail = ''
            schema = row_schema(r)
            for comparison in r['comparisons']:
                rows = ''.join(result_row(x, schema) for x in comparison['results'])
                detail += f'<h2>Compared with v{comparison["reference_version"]}</h2><p>Candidate: <code>{comparison["candidate_sha"]}</code><br>Reference: v{comparison["reference_version"]} <code>{comparison["reference_sha"]}</code></p><p>{esc(comparison["environment"])}</p><p><a href="{esc(comparison["campaign_url"])}">Campaign manifest and raw evidence ↗</a></p><div class="table-wrap" role="region" aria-label="Scrollable measurement table"><table><caption>Estimates and confidence intervals. Verdicts are supplied by the campaign analyzer and shown exactly as measured, with their category and execution status.</caption><thead><tr>'+''.join(f'<th scope="col">{x}</th>' for x in COLUMNS)+'</tr></thead><tbody>'+rows+'</tbody></table></div>'
                detail += confidence_plot(comparison['results'], schema)
            detail += legend()
        outputs[f'releases/{r["version"]}.html'] = page(f'v{release_label(r)}', f'<p class="eyebrow">RELEASE REPORT / {esc(r["status"])}{" / PRERELEASE" if is_prerelease(r) else ""}</p><h1>Knotrel {esc(release_label(r))}</h1><p class="lead">{esc(r["baseline_policy"])}</p>{decision_note(r)}{detail}<h2>What this comparison covers</h2><div class="grid"><article class="card"><h3>Response & capacity</h3><p>Latency distributions, throughput, failures and concurrent updates.</p></article><article class="card"><h3>Resource footprint</h3><p>Steady/peak memory and CPU cost with explicit measurement boundaries.</p></article><article class="card"><h3>Confidence & provenance</h3><p>Independent runs, interval methods, exact revisions and linked evidence.</p></article></div><p class="note">Missing coverage is not PASS. An accepted exception does not change a failed verdict.</p>', '../', 'Releases')
    outputs['competitors.html'] = page('External comparisons', '''<p class="eyebrow">EXTERNAL COMPARISONS / PLANNED</p><h1>Compare the service.<br>Account for the contract.</h1><p class="lead">The first Neo4j and PostgreSQL campaign follows Knotrel 1.1.0, Cluster Forest and any selected profiling optimizations.</p><div class="grid"><article class="card"><h2>PostgreSQL</h2><p>Direct connectivity queries against indexed authoritative graph tables.</p></article><article class="card"><h2>PostgreSQL + Knotrel</h2><p>Connectivity served by Knotrel, including feeder cost and source-to-query lag.</p></article><article class="card"><h2>Neo4j</h2><p>Reviewed reachability queries with explicit transaction and freshness guarantees.</p></article></div><h2>Periodic, versioned campaigns</h2><p>Review the need for a refresh quarterly or after a relevant minor release. Every campaign pins versions, configurations and hardware. Historical reports remain unchanged.</p><h2>Fair comparisons</h2><p>Use the same logical graph and trace, validate answers independently, include required synchronization or recomputation, and report full-stack resources. Non-equivalent cases are identified separately.</p><div class="empty"><h2>No competitor results published here yet.</h2><p>The experiment is tracked in <a href="https://github.com/knotrel/knotrel-benchmarks/issues/15">benchmark issue #15</a>.</p></div>''', active='Competitors')
    outputs['methodology.html'] = page('Measurement methodology', '''<p class="eyebrow">METHODOLOGY</p><h1>Numbers need context.</h1><p class="lead">A reproducible comparison connects every estimate to its workload, environment and raw observations.</p><h2>01 / Freeze the experiment</h2><p>Pin candidate and reference revisions, binary hashes, backend, graph traces, seeds, resource budgets, warm-up, run order, sample counts, exclusions and analysis. Exploratory profiling does not enter the formal sample.</p><h2>02 / Compare equivalent work</h2><p>Match graph, lifecycle, visibility and atomicity semantics. Validate with an independent oracle. Measure all required work; classify incompatible arms as NOT_EQUIVALENT.</p><h2>03 / Quantify uncertainty</h2><p>Use independent repeated process runs and balanced or randomized ordering. Report 95% confidence intervals for absolute estimates and changes where supported, with the estimand, method and run count. Preserve paired designs and account for correlated observations.</p><p>A p99 describes a latency tail; its confidence interval describes uncertainty in that estimate. Millions of requests in one process are not millions of independent experiments. Deterministic byte counts need no artificial interval. Missing intervals require an explanation.</p><h2>04 / Interpret the whole system</h2><p>Show latency with successful throughput, errors and offered load; CPU with work completed; memory with process boundaries; feeder responses with freshness. Declare open-loop or closed-loop load and avoid coordinated omission.</p><h2>05 / Preserve unfavorable results</h2><p>Keep failed and invalid runs. Thresholds, multiple-comparison policy and rerun rules are declared in advance. Report practical effect sizes and uncertainty; statistical significance alone is not a regression budget.</p><div class="grid"><article class="card"><h3>PASS / FAIL / REGRESSION</h3><p>Campaign-defined verdicts, not recalculated by this website. A qualifier such as PASS (IMPROVED) is kept as written.</p></article><article class="card"><h3>INCONCLUSIVE / UNRESOLVED / INVALID</h3><p>Insufficient precision (including INCONCLUSIVE_DISCLOSED) or invalid evidence must remain visible.</p></article><article class="card"><h3>NOT_EQUIVALENT</h3><p>A contract mismatch cannot establish a comparative performance claim.</p></article><article class="card"><h3>TIMER_LIMITED / EXCEEDS_BUDGET</h3><p>A timer-limited cell or a disclosure category is listed with its numbers, never converted.</p></article><article class="card"><h3>NOT_RUN / no verdict</h3><p>Unmeasured or nonconforming results show their reason and no numbers.</p></article><article class="card"><h3>Category and status</h3><p>Each row also states its role (decisive, descriptive, disclosure) and whether it completed.</p></article></div><p class="note">An exception records a release decision. It never converts a failed measurement to PASS.</p><h2>Inspect the implementation</h2><p><a href="https://github.com/knotrel/knotrel-benchmarks/blob/main/docs/methodology.md">Harness methodology</a> · <a href="https://github.com/knotrel/knotrel-benchmarks/blob/main/AGENTS.md">Repository measurement rules</a></p>''', active='Methodology')
    outputs['engines.html'] = engines_index(engines['comparisons'])
    for c in engines['comparisons']:
        outputs[f'engines/{c["id"]}.html'] = engine_page(c)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if generated pages are stale')
    args = parser.parse_args()
    engine_data = DOCS / 'data/engine-comparisons.json'
    engines = json.loads(engine_data.read_text()) if engine_data.exists() else None
    outputs = generate(json.loads((DOCS / 'data/releases.json').read_text()), engines)
    for name, content in outputs.items():
        target = DOCS / name
        if args.check:
            if not target.exists() or target.read_text() != content:
                raise SystemExit(f'Stale generated page: {name}')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    print(f'{len(outputs)} pages validated' if args.check else f'{len(outputs)} pages generated')


if __name__ == '__main__':
    main()
