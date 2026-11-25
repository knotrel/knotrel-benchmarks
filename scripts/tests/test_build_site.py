"""Check publication integrity without running performance workloads."""
import copy
import importlib.util
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('build_site', Path(__file__).parents[1] / 'build_site.py')
site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(site)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and not value.startswith(('https://', '#')):
                self.paths.append(value)


# Schema 1 tests start from a fixed planned 1.0.0 entry, not from the live
# docs/data/releases.json, so publishing results does not change what they test.
PLANNED = {'schema_version': 1, 'releases': [{
    'version': '1.0.0', 'status': 'planned',
    'baseline_policy': 'Latest released 0.9.x patch at campaign freeze, frozen as the reference.',
    'comparisons': []}]}


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.live = json.loads((site.DOCS / 'data/releases.json').read_text())
        self.data = copy.deepcopy(PLANNED)

    def published(self):
        row = dict(scenario='test-only', metric='latency', unit='ms', direction='lower',
                   candidate=11, reference=10, delta_pct=10, runs=12,
                   verdict='REGRESSION', ci_method='paired bootstrap over processes',
                   candidate_ci95=[10, 12], reference_ci95=[9, 11], delta_ci95=[5, 15],
                   evidence_url='https://example.org/test-only')
        comparison = dict(candidate_sha='a'*40, reference_sha='b'*40,
                          reference_version='0.9.0', environment='test fixture only',
                          campaign_url='https://example.org/test-only', results=[row])
        r = self.data['releases'][0]
        r.update(status='published', comparisons=[comparison])
        return comparison, row

    def test_links_and_generated_files(self):
        engines = json.loads((site.DOCS / 'data/engine-comparisons.json').read_text())
        for name, output in site.generate(self.live, engines).items():
            self.assertEqual((site.DOCS / name).read_text(), output)
            parser = Links()
            parser.feed(output)
            for link in parser.paths:
                self.assertTrue((site.DOCS / name).parent.joinpath(link).exists(), (name, link))

    def test_pending_has_no_verdict_or_fake_measurement(self):
        page = site.generate(self.data)['releases/1.0.0.html']
        self.assertIn('No measurements published yet', page)
        self.assertNotIn('<table>', page)

    def test_multiple_references_and_escaped_content(self):
        comparison, row = self.published()
        row['scenario'] = '<script>alert(1)</script>'
        second = copy.deepcopy(comparison)
        second['reference_version'] = '0.8.0'
        self.data['releases'][0]['comparisons'].append(second)
        page = site.generate(self.data)['releases/1.0.0.html']
        self.assertEqual(page.count('<table>'), 2)
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>alert', page)
        self.assertIn('REGRESSION', page)

    def test_reject_moving_reference(self):
        comparison, _ = self.published()
        comparison['reference_version'] = '0.9.x'
        with self.assertRaises(AssertionError):
            site.validate(self.data)

    def test_reject_inconsistent_delta(self):
        _, row = self.published()
        row['delta_pct'] = -10
        with self.assertRaises(AssertionError):
            site.validate(self.data)

    def test_missing_interval_requires_reason(self):
        _, row = self.published()
        row['delta_ci95'] = None
        with self.assertRaises(AssertionError):
            site.validate(self.data)
        row['ci_unavailable_reason'] = 'Insufficient independent observations'
        site.validate(self.data)

    def test_no_unreviewed_measurements_on_planned_page(self):
        self.published()
        self.data['releases'][0]['status'] = 'planned'
        with self.assertRaises(AssertionError):
            site.validate(self.data)


FIXTURE = Path(__file__).parent / 'fixtures' / 'site_all_outcomes.json'


class SchemaTwoTests(unittest.TestCase):
    """Schema 2: verdict, category and execution status as three separate fields."""

    def setUp(self):
        self.data = json.loads(FIXTURE.read_text())
        self.rows = self.data['releases'][0]['comparisons'][0]['results']

    def row(self, scenario):
        return next(r for r in self.rows if r['scenario'] == scenario)

    def rejects(self):
        with self.assertRaises((AssertionError, KeyError)):
            site.validate(self.data)

    def test_fixture_holds_every_outcome_and_is_valid(self):
        site.validate(self.data)
        self.assertEqual({r['verdict'] for r in self.rows}, set(site.VERDICTS) | {None})
        self.assertEqual({r['category'] for r in self.rows}, set(site.CATEGORIES))
        self.assertEqual({r['status'] for r in self.rows}, set(site.STATUSES))

    def test_every_verdict_accepted(self):
        for verdict in site.MEASURED_VERDICTS:
            with self.subTest(verdict):
                self.row('fixture-pass')['verdict'] = verdict
                site.validate(self.data)

    def test_unknown_verdict_rejected(self):
        for verdict in ('PASSED', 'pass', 'PASS(IMPROVED)', 'NOT RUN', '', 'IMPROVED'):
            with self.subTest(verdict):
                self.setUp()
                self.row('fixture-pass')['verdict'] = verdict
                self.rejects()
        self.setUp()
        del self.row('fixture-pass')['verdict']
        self.rejects()

    def test_category_and_status_enums_enforced(self):
        for key, value in (('category', 'deciding'), ('category', None), ('status', 'done'), ('status', 'NOT_RUN')):
            with self.subTest((key, value)):
                self.setUp()
                self.row('fixture-pass')[key] = value
                self.rejects()
        for key in ('category', 'status'):
            with self.subTest(missing=key):
                self.setUp()
                del self.row('fixture-pass')[key]
                self.rejects()

    def test_verdict_must_match_status(self):
        for scenario, verdict in (('fixture-pass', 'NOT_RUN'), ('fixture-pass', None), ('fixture-not-run', 'PASS'),
                                  ('fixture-not-run', None), ('fixture-nonconforming', 'PASS'),
                                  ('fixture-failed', 'PASS'), ('fixture-failed', 'NOT_RUN')):
            with self.subTest((scenario, verdict)):
                self.setUp()
                self.row(scenario)['verdict'] = verdict
                self.rejects()

    def test_not_run_requires_reason(self):
        for scenario in ('fixture-not-run', 'fixture-nonconforming', 'fixture-failed'):
            for reason in (None, '', '   '):
                with self.subTest((scenario, reason)):
                    self.setUp()
                    self.row(scenario)['status_reason'] = reason
                    self.rejects()
            with self.subTest((scenario, 'absent')):
                self.setUp()
                del self.row(scenario)['status_reason']
                self.rejects()

    def test_not_run_with_values_rejected(self):
        values = {'candidate': 1, 'reference': 1, 'delta_pct': 0.0, 'delta_ci95': [-1, 1],
                  'candidate_ci95': [0, 2], 'reference_ci95': [0, 2], 'runs': 3}
        for scenario in ('fixture-not-run', 'fixture-nonconforming', 'fixture-failed'):
            for key, value in values.items():
                with self.subTest((scenario, key)):
                    self.setUp()
                    self.row(scenario)[key] = value
                    self.rejects()
        self.setUp()
        self.row('fixture-not-run').update(candidate=None, reference=None, delta_pct=None, delta_ci95=None)
        site.validate(self.data)  # null is the same as absent

    def test_rule_rows_carry_no_estimate(self):
        for key, value in (('delta_pct', 1.0), ('delta_ci95', [0, 1]), ('reference', -1), ('runs', 0)):
            with self.subTest(key):
                self.setUp()
                self.row('fixture-rule')[key] = value
                self.rejects()
        self.setUp()
        self.row('fixture-rule')['estimate_unavailable_reason'] = ' '
        self.rejects()
        self.setUp()
        self.row('fixture-rule').update(candidate=64, reference=0)  # zero reference needs its unit
        self.rejects()
        self.row('fixture-rule')['unit'] = 'bytes'
        site.validate(self.data)

    def test_completed_rows_keep_schema_one_rules(self):
        for key, value in (('delta_pct', 50.0), ('runs', True), ('reference', 0), ('ci_method', '')):
            with self.subTest(key):
                self.setUp()
                self.row('fixture-pass')[key] = value
                self.rejects()

    def test_release_schema_versions(self):
        self.data['schema_version'] = 1
        self.rejects()  # a release cannot be newer than the dataset
        self.setUp()
        self.data['releases'][0]['schema_version'] = 3
        self.rejects()
        self.setUp()
        self.data['schema_version'] = 3
        self.rejects()

    def test_old_entries_still_valid(self):
        old = json.loads((site.DOCS / 'data/releases.json').read_text())
        site.validate(old)
        legacy = dict(scenario='legacy', metric='latency', unit='ms', direction='lower', candidate=11, reference=10,
                      delta_pct=10, runs=12, verdict='REGRESSION', ci_method='paired bootstrap',
                      candidate_ci95=[10, 12], reference_ci95=[9, 11], delta_ci95=[5, 15],
                      evidence_url='https://example.org/legacy')
        entry = dict(version='0.9.0', status='published', baseline_policy='legacy entry',
                     comparisons=[dict(candidate_sha='c'*40, reference_sha='d'*40, reference_version='0.8.0',
                                       environment='legacy', campaign_url='https://example.org/legacy',
                                       results=[legacy])])
        for version in (1, 2):  # unchanged in a schema 1 file and inside a schema 2 file
            with self.subTest(version):
                data = {'schema_version': version, 'releases': [copy.deepcopy(entry)]}
                site.validate(data)
                page = site.generate(data)['releases/0.9.0.html']
                self.assertIn('>REGRESSION<', page)
                self.assertIn('>decisive<', page)  # documented schema 1 defaults
                self.assertIn('>completed<', page)
                self.assertIn('95% CI', page)
        bad = copy.deepcopy(entry)
        bad['comparisons'][0]['results'][0]['verdict'] = 'UNRESOLVED'  # schema 1 keeps its six verdicts
        with self.assertRaises(AssertionError):
            site.validate({'schema_version': 2, 'releases': [bad]})

    def test_rendering_shows_each_outcome_unchanged(self):
        outputs = site.generate(self.data)
        page = outputs['releases/1.0.0.html']
        body = page.split('<tbody>', 1)[1].split('</tbody>', 1)[0]
        trs = re.findall(r'<tr>(.*?)</tr>', body)
        self.assertEqual(len(trs), len(self.rows))
        for tr, row in zip(trs, self.rows):
            with self.subTest(row['scenario']):
                cells = re.findall(r'<td[^>]*>(.*?)</td>', tr)
                text = [html.unescape(re.sub(r'<[^>]+>', '', c)) for c in cells]
                self.assertEqual(text[0], row['scenario'])
                self.assertEqual(text[3], 'No verdict' if row['verdict'] is None else row['verdict'])
                self.assertEqual(text[4], row['category'])
                self.assertEqual(text[5], row['status'].replace('_', ' '))
                if row['status'] == 'completed':
                    self.assertEqual(len(cells), len(site.COLUMNS))
                    self.assertNotIn('No measurements', tr)
                else:
                    self.assertIn(f'colspan="{len(site.MEASURE_COLUMNS)}"', tr)
                    self.assertIn(html.escape(row['status_reason']), tr)
                    measure = text[6]
                    self.assertTrue(measure.startswith('No measurements.'))
                    self.assertFalse(re.search(r'\d', measure.replace(row['status_reason'], '')))
                    self.assertFalse(re.search(r'\d', ''.join(text[:6] + text[7:-1]).replace(row['scenario'], '')))
                    self.assertNotIn(row['scenario'], page.split('interval-plots', 1)[-1])
        self.assertIn('class="verdict tone-ok verdict-pass-improved">PASS (IMPROVED)<', page)
        self.assertIn('class="verdict tone-none verdict-not-run">NOT_RUN<', page)
        self.assertIn('class="verdict tone-none verdict-no-verdict">No verdict<', page)
        self.assertIn('fixture: a rule, no single estimate', page)
        self.assertIn('Reading the tables', page)
        self.assertNotIn('95% CI', page)  # schema 2 intervals carry their own coverage in ci_method
        for name, output in outputs.items():
            parser = Links()
            parser.feed(output)
            for link in parser.paths:
                self.assertTrue((site.DOCS / name).parent.joinpath(link).exists(), (name, link))

    def test_json_keeps_each_verdict_text(self):
        site.generate(self.data)
        dumped = json.dumps(self.data)
        for verdict in site.VERDICTS:
            self.assertIn(json.dumps(verdict), dumped)
        self.assertEqual(json.loads(FIXTURE.read_text()), self.data)  # rendering never rewrites the data

    def release(self):
        return self.data['releases'][0]

    def test_published_schema_two_release_requires_its_decision(self):
        for key in ('release_label', 'qualification_decision', 'decision_url'):
            with self.subTest(missing=key):
                self.setUp()
                del self.release()[key]
                self.rejects()
        for key, value in (('release_label', '1.0.1-rc.1'), ('release_label', '1.0'), ('release_label', 'v1.0.0-rc.1'),
                           ('qualification_decision', 'all gates PASS'), ('qualification_decision', 'accepted with exception'),
                           ('decision_url', 'http://example.invalid/DECISION.md'), ('decision_url', '')):
            with self.subTest(**{key: value}):
                self.setUp()
                self.release()[key] = value
                self.rejects()
        for decision in site.DECISIONS:
            with self.subTest(decision=decision):
                self.setUp()
                self.release()['qualification_decision'] = decision
                site.validate(self.data)

    def test_release_candidate_is_labelled_prerelease_with_its_decision(self):
        outputs = site.generate(self.data)
        page, index = outputs['releases/1.0.0.html'], outputs['index.html']
        self.assertIn('<h1>Knotrel 1.0.0-rc.1</h1>', page)
        self.assertIn('RELEASE REPORT / published / PRERELEASE', page)
        self.assertIn('a release candidate (prerelease), not a stable release', page)
        self.assertIn('<strong>accepted with exceptions</strong>', page)
        self.assertIn('href="https://example.invalid/DECISION.md"', page)
        for name in ('index.html', 'releases.html'):
            self.assertIn('<span class="badge">prerelease</span>', outputs[name])
            self.assertIn('qualification accepted with exceptions', outputs[name])
            self.assertIn('v1.0.0-rc.1', outputs[name])
            self.assertNotIn('<h3>v1.0.0 <span>', outputs[name])
        self.assertIn('Explore the 1.0.0-rc.1 results', index)
        self.assertNotIn('all gates PASS', page)

    def test_stable_release_is_not_labelled_prerelease(self):
        self.release()['release_label'] = '1.0.0'
        outputs = site.generate(self.data)
        self.assertIn('a stable release', outputs['releases/1.0.0.html'])
        self.assertNotIn('PRERELEASE', outputs['releases/1.0.0.html'])
        self.assertNotIn('<span class="badge">prerelease</span>', outputs['releases.html'])


if __name__ == '__main__':
    unittest.main()


class EngineComparisonTests(unittest.TestCase):
    """The CF5 engine page: one build, original classes, limitation and L2 non-PASS rows visible."""

    def setUp(self):
        self.releases = copy.deepcopy(PLANNED)
        self.engines = json.loads((site.DOCS / 'data/engine-comparisons.json').read_text())
        self.c = self.engines['comparisons'][0]

    def page(self):
        return site.generate(self.releases, self.engines)[f'engines/{self.c["id"]}.html']

    def test_page_names_the_comparison_kind_and_limitation(self):
        page = self.page()
        self.assertIn('ENGINE COMPARISON / ONE BUILD / NOT A RELEASE COMPARISON', page)
        self.assertIn('cluster-forest compared with compact-bfs, ETT, HDT', page)
        self.assertIn('Host swap activity not verifiable; results accepted by the maintainer with this limitation',
                      page)
        self.assertIn(self.c['report_url'], page)
        self.assertIn('compact-bfs stays the default engine', page)

    def test_lifecycle_fails_and_disclosures_are_listed_as_projections(self):
        page = self.page()
        rules = self.c['lifecycle_rules']
        self.assertEqual([(e['workload'], e['nodes'], e['projected_growth_30_pct']) for e in rules['c3_fail']],
                         [('reuse same', 1000, 20.2), ('toggle', 1000, 14.6)])
        self.assertIn('<strong>+20.2 %</strong> (projected from the slope)', page)
        self.assertIn('<strong>+14.6 %</strong> (projected from the slope)', page)
        self.assertEqual(len(rules['c4_exceeds_budget']), 9)
        self.assertIn('C4 EXCEEDS_BUDGET (9)', page)
        for e in rules['c3_fail'] + rules['c4_exceeds_budget']:
            self.assertIn(e['run'], page)

    def test_family_statements_match_the_analyzer(self):
        analysis = json.loads((site.ROOT / 'results/v1.1.0-cf5/analysis/attempt1/analysis-session1.json').read_text())
        for family in self.c['families']:
            for a in family['against']:
                self.assertEqual(a['statement'],
                                 analysis['family_statements'][family['family']][a['reference']]['statement'])

    def test_rejects_missing_limitation_unlisted_fail_and_moving_links(self):
        for mutate in (lambda c: c.update(limitations=[]),
                       lambda c: c['lifecycle_rules']['c3_fail'].pop(),
                       lambda c: c['lifecycle_rules']['c4_exceeds_budget'].pop(),
                       lambda c: c.pop('lifecycle_disposition'),
                       lambda c: c.update(report_url='https://github.com/knotrel/knotrel-benchmarks/blob/main/x.md'),
                       lambda c: c['families'][0]['against'][0].update(statement='prefer cluster-forest strongly'),
                       lambda c: c['families'][0]['against'][0]['classes'].update(PASS=1)):
            engines = copy.deepcopy(self.engines)
            mutate(engines['comparisons'][0])
            with self.assertRaises((AssertionError, KeyError)):
                site.generate(self.releases, engines)

    def test_engines_index_without_data(self):
        page = site.generate(self.releases)['engines.html']
        self.assertIn('No engine comparison published yet.', page)

    def test_exporter_reproduces_the_dataset(self):
        spec = importlib.util.spec_from_file_location('export_cf5_site', site.ROOT / 'scripts/export_cf5_site.py')
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        self.assertEqual(exporter.build(self.c['report_url'], self.c['evidence_url']), self.engines)
