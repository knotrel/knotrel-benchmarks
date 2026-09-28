"""Source snapshots exclude previously staged measurement outputs."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import run_baseline

class SourceSnapshotTests(unittest.TestCase):
    def test_includes_staged_and_unstaged_source_but_not_staged_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(['git', '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args], cwd=root, check=True, capture_output=True)
            git('init', '-q')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'base')
            (root/'crates').mkdir()
            (root/'results').mkdir()
            (root/'crates/lib.rs').write_text('staged source\n')
            (root/'results/old.json').write_text('archived measurement\n')
            git('add', '.')
            (root/'crates/lib.rs').write_text('working source\n')
            patch = run_baseline.source_patch(root)
            self.assertIn('crates/lib.rs', patch)
            self.assertIn('+working source', patch)
            self.assertNotIn('old.json', patch)
            self.assertNotIn('archived measurement', patch)
