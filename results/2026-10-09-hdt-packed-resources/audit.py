"""Verify frozen inputs, process inventories and matching replay semantics."""
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
def read(p):
    return json.loads(p.read_text())
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

build = read(H / 'builds.json')
original = read(H.parent / '2026-10-08-hdt-packed-tokens/builds.json')
for name, expected in build['original_source_sha256'].items():
    prefix, relative = name.split('/', 1)
    root = ROOT if prefix == 'benchmarks' else ROOT.parent / 'knotrel'
    assert digest(root / relative) == expected, name
for variant in ('before', 'after'):
    assert build['variants'][variant]['forest_sha256'] == original['variants'][variant]['forest_sha256']
    assert digest(H / (variant + '-forest.rs.txt')) == build['variants'][variant]['forest_sha256']
    for b in (build, original):
        assert digest(Path(b['variants'][variant]['binary'])) == b['variants'][variant]['binary_sha256']
assert digest(H / 'diagnostic-main.rs.txt') == build['main_sha256']
assert digest(H / 'diagnostic-main.rs.txt') == digest(H.parent / '2026-10-08-hdt-phase-resources/after-main.rs.txt')
identities = set()
counts = {}
for folder, key, expected in ((H, 'runs', 18), (H / 'confirmation', 'cases', 16)):
    manifest = read(folder / 'manifest.json')
    for name, sha in manifest['artifact_sha256'].items():
        assert digest(folder / name) == sha, name
    runs = manifest[key]
    assert len(runs) == expected and all(r['exit_code'] == 0 for r in runs)
    full = [r for r in runs if r.get('nodes', 1000000) == 1000000]
    assert len(full) == 16
    assert Counter(r['variant'] for r in full[::2]) == {'before': 4, 'after': 4}
    for a, b in zip(full[::2], full[1::2]):
        assert a['pair'] == b['pair'] and {a['variant'], b['variant']} == {'before', 'after'}
    for run in full:
        data = read(folder / (run['name'] + '.json'))
        assert data['warmup'] == 0 and data['query_percent'] == 50
        assert data['workload'] == 'sustained-churn-path-v1' and len(data['repetitions']) == 1
        rep = data['repetitions'][0]
        identities.add(json.dumps([data['trace_fingerprint_fnv1a64'], rep['hdt_stats'],
            [rep[k]['count'] for k in ('query_true', 'query_false')],
            [(rep['measurements'][k] or {}).get('count', 0) for k in ('cut', 'link', 'connected')]], sort_keys=True))
        if folder == H:
            observations = read(folder / (run['name'] + '-observations.json'))
            assert [o['phase'] for o in observations] == [p + '_' + s for p in ('empty_before', 'setup', 'replay', 'empty_after') for s in ('start', 'end')]
    counts[folder.name] = len(runs)
assert len(identities) == 1
assert read(H / 'verification.json')['all_passed']
for path in H.rglob('*.py'):
    ast.parse(path.read_text(), filename=str(path))
(H / 'audit.json').write_text(json.dumps({'all_passed': True, 'successful_processes': counts,
    'checks': ['production source hashes unchanged', 'original and diagnostic binary hashes',
    'packed forest source identity', 'shared diagnostic source', 'manifest artifact hashes',
    'eight adjacent balanced pairs per study', 'matching trace, answers and HDT counters',
    'phase sequences', 'verification result', 'Python syntax']}, indent=2) + '\n')
print('Audit passed:', counts)
