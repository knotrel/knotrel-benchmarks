"""Check publication integrity without running performance workloads."""
import copy
import importlib.util
import json
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


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((site.DOCS / 'data/releases.json').read_text())

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
        for name, output in site.generate(self.data).items():
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


if __name__ == '__main__':
    unittest.main()
