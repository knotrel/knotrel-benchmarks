"""Audit the pilot inputs, results and paired ordering."""
import ast,hashlib,json,sys
from collections import defaultdict,Counter
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'manifest.json').read_text());b=m['builds']
assert hashes()==b['original_source_sha256']
for v,meta in b['variants'].items():
 assert hashlib.sha256(Path(meta['binary']).read_bytes()).hexdigest()==meta['binary_sha256']
 assert hashlib.sha256((H.parent/'2026-10-09-ett-packed-tokens'/(v+'-forest.rs.txt')).read_bytes()).hexdigest()==meta['forest_sha256']
for name,d in m['artifact_sha256'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==d,name
assert len(m['cases'])==304
orders=defaultdict(list)
for a,z in zip(m['cases'][::2],m['cases'][1::2]):
 assert a['pair']==z['pair'] and a['reference']==z['reference']
 assert {a['variant'],z['variant']}=={'before','after'}
 orders[a['reference']].append(a['variant'])
assert len(orders)==38 and all(Counter(v)=={'before':2,'after':2} for v in orders.values())
for c in m['cases']:
 if c['exit_code']!=0:continue
 r=json.loads((H/(c['name']+'.json')).read_text());ref=json.loads((ROOT/c['reference']).read_text())
 assert r['engine']=='knotrel-core/ett-pruned-v2' and r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
 assert len(r['repetitions'])==1
 x,y=r['repetitions'][0],ref['repetitions'][0]
 assert x['forest_stats']==y['forest_stats']
 for key in ('query_true','query_false'):
  assert (x[key] or {}).get('count',0)==(y[key] or {}).get('count',0)
 for key in ('cut','link','connected'):
  assert (x['measurements'][key] or {}).get('count',0)==(y['measurements'][key] or {}).get('count',0)
assert json.loads((H.parent/'2026-10-09-ett-packed-tokens/verification.json').read_text())['all_passed']
for p in H.glob('*.py'):ast.parse(p.read_text())
(H/'audit.json').write_text(json.dumps({'all_passed':True,'attempted_processes':304,'successful_processes':sum(c['exit_code']==0 for c in m['cases']),'balanced_cells':38,'production_sources_unchanged':True,'checks':['binary/source/artifact hashes','trace identity and reference answer counts','ETT forest counters','paired balanced order','workspace verification','Python syntax']},indent=2)+'\n')
print('Audit passed')
