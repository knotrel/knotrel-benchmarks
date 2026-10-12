"""Verify complete coordinate sequences and original reference semantics."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
m=json.loads((H/'manifest.json').read_text());first=None
for c in m['runs']:
 r=json.loads((H/(c['name']+'.json')).read_text());x=r['repetitions'][0]
 if first is None:first=x['root_accesses']
 assert x['root_accesses']==first
 regime='warmed' if c['warmup'] else 'fresh'
 ref=json.loads((ROOT/f'results/2026-10-06-engine-ranking-sparse/sustained-churn-path-v1-n1000000-q50-{regime}-p0-ett-scan.json').read_text());y=ref['repetitions'][0]
 assert r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
 for k in ('query_true','query_false'):assert (x[k] or {}).get('count',0)==(y[k] or {}).get('count',0)
 for k in ('cut','link','connected'):assert (x['measurements'][k] or {}).get('count',0)==(y['measurements'][k] or {}).get('count',0)
(H/'audit.json').write_text(json.dumps({'all_passed':True,'runs':8,'complete_coordinate_sequences_equal':True,'reference_trace_and_counts_match':True},indent=2)+'\n')
print('Locality audit passed')
