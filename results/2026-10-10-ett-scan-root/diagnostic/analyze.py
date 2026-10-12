"""Verify counter provenance, repeatability and exact operation outcomes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / 'manifest.json').read_text())
for name, digest in manifest['artifact_sha256'].items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
summary = {}
variants = {}
for variant in ('before', 'after'):
    runs = [json.loads((HERE / f'{variant}-{i}.json').read_text()) for i in range(2)]
    assert runs[0] == runs[1]
    variants[variant] = runs[0]
    cuts = [op for op in runs[0]['operations'] if op['operation'] == 'cut']
    summary[variant] = {
        'root_calls': sum(op['phases'][0][0] for op in cuts),
        'root_steps': sum(op['phases'][0][1] for op in cuts),
        'forest_stats': runs[0]['forest_stats'],
    }
a, b = variants['before'], variants['after']
assert len(a['operations']) == len(b['operations'])
assert a['forest_stats'] == b['forest_stats']
for left, right in zip(a['operations'], b['operations']):
    for key in ('index', 'operation', 'answer', 'forest_stats_delta'):
        assert left[key] == right[key], (left['index'], key)
assert summary['before']['root_calls'] - summary['after']['root_calls'] == a['forest_stats'][2]
(HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
