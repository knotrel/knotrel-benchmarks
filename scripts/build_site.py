#!/usr/bin/env python3
"""Generate the static performance site from validated release summaries."""
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


def validate(data):
    """Reject ambiguous identities and incomplete published evidence."""
    if not __debug__:
        raise RuntimeError('Validation requires Python without -O')
    assert data['schema_version'] == 1, 'Unsupported schema'
    seen = set()
    for release in data['releases']:
        version = release['version']
        assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'Exact version required'
        assert version not in seen, 'Duplicate version'
        seen.add(version)
        assert release['status'] in ('planned', 'published')
        assert isinstance(release['baseline_policy'], str)
        if release['status'] == 'planned':
            assert not release.get('comparisons'), 'Planned releases cannot contain measurements'
            continue
        assert release['comparisons'], 'Published release requires comparisons'
        references = set()
        for comparison in release['comparisons']:
            assert comparison['reference_version'] not in references, 'Duplicate reference'
            references.add(comparison['reference_version'])
            for field in ('candidate_sha', 'reference_sha'):
                assert re.fullmatch(r'[0-9a-f]{40}', comparison[field] or ''), field
            assert re.fullmatch(r'\d+\.\d+\.\d+', comparison['reference_version'] or '')
            assert comparison['environment'] and comparison['results']
            assert comparison['campaign_url'].startswith('https://')
            for row in comparison['results']:
                for key in ('scenario', 'metric', 'unit', 'direction', 'verdict', 'ci_method'):
                    assert isinstance(row[key], str) and row[key]
                assert row['direction'] in ('lower', 'higher')
                assert row['verdict'] in ('PASS', 'FAIL', 'REGRESSION', 'INCONCLUSIVE', 'INVALID', 'NOT_EQUIVALENT')
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
                assert row['evidence_url'].startswith('https://')


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
        'external': '<path d="M14 3h7v7m0-7L10 14M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-6"/>',
    }
    return f'<svg class="icon icon-{name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>'


def page(title, content, prefix='', active='Overview'):
    """Render a page with paths that also work under project Pages URLs."""
    links = [('Overview', 'index.html'), ('Releases', 'releases.html'),
             ('Competitors', 'competitors.html'), ('Methodology', 'methodology.html')]
    nav_icons = {'Overview': 'chart', 'Releases': 'layers', 'Competitors': 'compare', 'Methodology': 'measure'}
    nav = ''.join(f'<a {"aria-current=page" if label == active else ""} href="{prefix}{url}">{icon(nav_icons[label])}<span>{label}</span></a>' for label, url in links)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | Knotrel Performance</title><meta name="description" content="Reproducible Knotrel release performance, uncertainty and benchmark evidence.">
<link rel="icon" href="{prefix}assets/mark.svg"><link rel="stylesheet" href="{prefix}assets/performance.css">
<script src="{prefix}assets/site.js" defer></script></head><body>
<a class="skip" href="#main">Skip to content</a><header><a class="brand" href="{prefix}index.html"><img src="{prefix}assets/mark.svg" alt="" width="30" height="30">Knotrel <span>Performance</span></a><nav aria-label="Main">{nav}</nav><button id="theme" class="theme-button" type="button" aria-label="Switch to light mode" title="Switch to light mode">{icon("sun")}{icon("moon")}</button></header>
<main id="main">{content}</main><footer><div><strong>Knotrel Performance</strong><p>Measurements with context. Evidence you can inspect.</p></div><div><a href="https://knotrel.github.io/knotrel/">Knotrel documentation ↗</a><a href="{REPO}">Benchmark repository ↗</a><a href="{prefix}data/releases.json">Release data · JSON</a></div></footer></body></html>'''


def cards(releases):
    return ''.join(f'<a class="card release" href="releases/{r["version"]}.html"><span class="badge">{esc(r["status"])}</span><h3>v{r["version"]} <span>{icon("arrow")}</span></h3><p>{esc(r["baseline_policy"])}</p></a>' for r in releases)


def interval(value):
    return 'Not available' if value is None else f'[{value[0]:.3g}, {value[1]:.3g}]'


def confidence_plot(rows):
    """Render each relative estimate on its own labeled symmetric percent axis."""
    plots = []
    for row in rows:
        ci = row.get('delta_ci95')
        if ci is None or row['verdict'] in ('INVALID', 'NOT_EQUIVALENT'):
            continue
        bound = max(1, abs(ci[0]), abs(ci[1]), abs(row['delta_pct'])) * 1.15
        def position(value):
            return 240 + value / bound * 200
        label = f"{row['scenario']} / {row['metric']}: {row['delta_pct']:+.2f}%, 95% CI {interval(ci)}; {row['direction']} is better"
        plots.append(f'''<figure class="card"><figcaption>{esc(label)}</figcaption>
<svg viewBox="0 0 480 90" role="img" aria-label="{esc(label)}">
<line x1="40" x2="440" y1="36" y2="36" stroke="var(--line)"/>
<line x1="240" x2="240" y1="16" y2="57" stroke="var(--muted)" stroke-dasharray="3 3"/>
<line x1="{position(ci[0]):.2f}" x2="{position(ci[1]):.2f}" y1="36" y2="36" stroke="var(--accent)" stroke-width="4"/>
<circle cx="{position(row['delta_pct']):.2f}" cy="36" r="6" fill="var(--accent)"/>
<text x="40" y="78" fill="var(--muted)" font-size="12">−{bound:.1f}%</text>
<text x="240" y="78" text-anchor="middle" fill="var(--muted)" font-size="12">0%</text>
<text x="440" y="78" text-anchor="end" fill="var(--muted)" font-size="12">+{bound:.1f}%</text></svg></figure>''')
    return '<div class="interval-plots">' + ''.join(plots) + '</div>' if plots else ''


def generate(data):
    """Build deterministic pages without running any benchmarks."""
    validate(data)
    releases = data['releases']
    published = sum(r['status'] == 'published' for r in releases)
    outputs = {}
    outputs['index.html'] = page('Performance, in context', f'''
<section class="hero"><p class="eyebrow">KNOTREL / BENCHMARK OBSERVATORY</p><h1>Performance.<br><em>With the evidence.</em></h1><p class="lead">Explore how Knotrel changes across releases. Response times, memory and CPU, with uncertainty and reproducible comparisons.</p><div class="actions"><a class="button primary" href="releases/1.0.0.html">{icon("chart")}<span>Explore the 1.0.0 plan</span>{icon("arrow")}</a><a class="button" href="methodology.html">{icon("measure")}<span>How we measure</span></a></div><div class="summary"><div><strong>{published:02}</strong><span>Published release reports</span></div><div><strong>1.0.0</strong><span>First release in this series</span></div><div><strong>95%</strong><span>Target confidence level</span></div></div></section>
<section><div class="section-title"><div><p class="eyebrow">RELEASE TRACKER</p><h2>A baseline for every change.</h2></div><a href="releases.html" class="icon-link">All releases {icon("arrow")}</a></div><div class="grid">{cards(releases)}</div><p class="note">The public series starts at 1.0.0 against a frozen 0.9.x reference. Planned reports contain no measurements. Published reports link to their campaign evidence.</p></section>
<section><p class="eyebrow">THREE VIEWS, ONE WORKLOAD</p><h2>Speed is only part of the story.</h2><div class="grid"><article class="card"><span class="number">01 / LATENCY</span><h3>How long do answers take?</h3><p>p50, p95 and p99 alongside throughput, failures and update visibility.</p></article><article class="card"><span class="number">02 / MEMORY</span><h3>What does the graph cost?</h3><p>Steady and peak memory. Heap and RSS, with process boundaries made explicit.</p></article><article class="card"><span class="number">03 / CPU</span><h3>How much work gets done?</h3><p>CPU time and utilization, interpreted against successful operations and offered load.</p></article></div></section>
<section class="callout"><p class="eyebrow">EXTERNAL COMPARISONS</p><h2>Same question. Different systems.</h2><p>Neo4j and PostgreSQL comparisons are planned after 1.1.0 and selected profiling work. Freshness, atomicity and full-stack costs are part of the comparison.</p><a href="competitors.html" class="icon-link">{icon("compare")}View the experiment scope {icon("arrow")}</a></section>''')
    outputs['releases.html'] = page('Release explorer', f'<p class="eyebrow">RELEASE EXPLORER</p><h1>Every release.<br>Its own evidence.</h1><p class="lead">Exact references are selected at campaign freeze and remain attached to that report.</p><div class="grid">{cards(releases)}</div><h2>Reference selection</h2><ol><li>Previous patch in the same minor, if available.</li><li>Latest patch of the previous available minor.</li><li>Latest patch of the previous major.</li><li>1.0.0 on the stable longitudinal workload subset.</li></ol><p>Duplicate references are removed. For 1.0.0, use the latest released 0.9.x patch at freeze. Missing or incompatible comparisons are explained, never filled with historical ratios from another environment.</p>', active='Releases')
    for r in releases:
        if r['status'] == 'planned':
            detail = '<div class="empty"><span class="badge">Awaiting campaign</span><h2>No measurements published yet.</h2><p>This is a comparison plan, not a performance verdict. Charts and estimates will appear only when validated evidence is available.</p></div>'
        else:
            detail = ''
            for comparison in r['comparisons']:
                rows = ''
                for x in comparison['results']:
                    rows += '<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in (x['scenario'], x['metric'], x['direction'] + ' is better', f'{x["reference"]} {x["unit"]}', interval(x.get('reference_ci95')), f'{x["candidate"]} {x["unit"]}', interval(x.get('candidate_ci95')), f'{x["delta_pct"]:+.2f}%', interval(x.get('delta_ci95')), x['runs'], x['verdict'], x['ci_method'], x.get('ci_unavailable_reason', ''), x.get('disposition', 'None'))) + f'<td><a href="{esc(x["evidence_url"])}">Evidence</a></td></tr>'
                detail += f'<h2>Compared with v{comparison["reference_version"]}</h2><p>Candidate: <code>{comparison["candidate_sha"]}</code><br>Reference: v{comparison["reference_version"]} <code>{comparison["reference_sha"]}</code></p><p>{esc(comparison["environment"])}</p><p><a href="{esc(comparison["campaign_url"])}">Campaign manifest and raw evidence ↗</a></p><div class="table-wrap" tabindex="0" role="region" aria-label="Scrollable measurement table"><table><caption>Estimates and 95% confidence intervals. Verdicts are supplied by the campaign analyzer.</caption><thead><tr>'+''.join(f'<th scope="col">{x}</th>' for x in ('Scenario','Metric','Direction','Reference','Reference CI','Candidate','Candidate CI','Change','Change CI','Runs','Verdict','CI method','CI limitation','Disposition','Source'))+'</tr></thead><tbody>'+rows+'</tbody></table></div>'
                detail += confidence_plot(comparison['results'])
        outputs[f'releases/{r["version"]}.html'] = page(f'v{r["version"]}', f'<p class="eyebrow">RELEASE REPORT / {esc(r["status"])}</p><h1>Knotrel {r["version"]}</h1><p class="lead">{esc(r["baseline_policy"])}</p>{detail}<h2>What this comparison covers</h2><div class="grid"><article class="card"><h3>Response & capacity</h3><p>Latency distributions, throughput, failures and concurrent updates.</p></article><article class="card"><h3>Resource footprint</h3><p>Steady/peak memory and CPU cost with explicit measurement boundaries.</p></article><article class="card"><h3>Confidence & provenance</h3><p>Independent runs, interval methods, exact revisions and linked evidence.</p></article></div><p class="note">Missing coverage is not PASS. An accepted exception does not change a failed verdict.</p>', '../', 'Releases')
    outputs['competitors.html'] = page('External comparisons', '''<p class="eyebrow">EXTERNAL COMPARISONS / PLANNED</p><h1>Compare the service.<br>Account for the contract.</h1><p class="lead">The first Neo4j and PostgreSQL campaign follows Knotrel 1.1.0, Cluster Forest and any selected profiling optimizations.</p><div class="grid"><article class="card"><h2>PostgreSQL</h2><p>Direct connectivity queries against indexed authoritative graph tables.</p></article><article class="card"><h2>PostgreSQL + Knotrel</h2><p>Connectivity served by Knotrel, including feeder cost and source-to-query lag.</p></article><article class="card"><h2>Neo4j</h2><p>Reviewed reachability queries with explicit transaction and freshness guarantees.</p></article></div><h2>Periodic, versioned campaigns</h2><p>Review the need for a refresh quarterly or after a relevant minor release. Every campaign pins versions, configurations and hardware. Historical reports remain unchanged.</p><h2>Fair comparisons</h2><p>Use the same logical graph and trace, validate answers independently, include required synchronization or recomputation, and report full-stack resources. Non-equivalent cases are identified separately.</p><div class="empty"><h2>No competitor results published here yet.</h2><p>The experiment is tracked in <a href="https://github.com/knotrel/knotrel-benchmarks/issues/15">benchmark issue #15</a>.</p></div>''', active='Competitors')
    outputs['methodology.html'] = page('Measurement methodology', '''<p class="eyebrow">METHODOLOGY</p><h1>Numbers need context.</h1><p class="lead">A reproducible comparison connects every estimate to its workload, environment and raw observations.</p><h2>01 / Freeze the experiment</h2><p>Pin candidate and reference revisions, binary hashes, backend, graph traces, seeds, resource budgets, warm-up, run order, sample counts, exclusions and analysis. Exploratory profiling does not enter the formal sample.</p><h2>02 / Compare equivalent work</h2><p>Match graph, lifecycle, visibility and atomicity semantics. Validate with an independent oracle. Measure all required work; classify incompatible arms as NOT_EQUIVALENT.</p><h2>03 / Quantify uncertainty</h2><p>Use independent repeated process runs and balanced or randomized ordering. Report 95% confidence intervals for absolute estimates and changes where supported, with the estimand, method and run count. Preserve paired designs and account for correlated observations.</p><p>A p99 describes a latency tail; its confidence interval describes uncertainty in that estimate. Millions of requests in one process are not millions of independent experiments. Deterministic byte counts need no artificial interval. Missing intervals require an explanation.</p><h2>04 / Interpret the whole system</h2><p>Show latency with successful throughput, errors and offered load; CPU with work completed; memory with process boundaries; feeder responses with freshness. Declare open-loop or closed-loop load and avoid coordinated omission.</p><h2>05 / Preserve unfavorable results</h2><p>Keep failed and invalid runs. Thresholds, multiple-comparison policy and rerun rules are declared in advance. Report practical effect sizes and uncertainty; statistical significance alone is not a regression budget.</p><div class="grid"><article class="card"><h3>PASS / FAIL / REGRESSION</h3><p>Campaign-defined verdicts, not recalculated by this website.</p></article><article class="card"><h3>INCONCLUSIVE / INVALID</h3><p>Insufficient precision or invalid evidence must remain visible.</p></article><article class="card"><h3>NOT_EQUIVALENT</h3><p>A contract mismatch cannot establish a comparative performance claim.</p></article></div><p class="note">An exception records a release decision. It never converts a failed measurement to PASS.</p><h2>Inspect the implementation</h2><p><a href="https://github.com/knotrel/knotrel-benchmarks/blob/main/docs/methodology.md">Harness methodology</a> · <a href="https://github.com/knotrel/knotrel-benchmarks/blob/main/AGENTS.md">Repository measurement rules</a></p>''', active='Methodology')
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if generated pages are stale')
    args = parser.parse_args()
    outputs = generate(json.loads((DOCS / 'data/releases.json').read_text()))
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
