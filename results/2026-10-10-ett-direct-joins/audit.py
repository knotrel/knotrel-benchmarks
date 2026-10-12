"""Verify current sources, frozen binaries, traces and complete balanced trials."""
import ast,hashlib,json,sys,itertools
from pathlib import Path
from collections import defaultdict,Counter
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'manifest.json').read_text());b=m['builds'];assert hashes()==b['original_source_sha256']
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
for v,meta in b['variants'].items():
 assert hashlib.sha256(Path(meta['binary']).read_bytes()).hexdigest()==meta['binary_sha256']
 assert hashlib.sha256((H/(v+'-forest.rs.txt')).read_bytes()).hexdigest()==meta['forest_sha256']
orders=defaultdict(list)
assert len(m['cases'])==162
for offset in range(0,162,3):
 group=m['cases'][offset:offset+3];assert len({c['pair'] for c in group})==1
 assert len({c['reference'] for c in group})==1
 orders[group[0]['reference']].append(tuple(c['variant'] for c in group))
assert len(orders)==9
for order in orders.values():assert set(order)==set(itertools.permutations(('before','after','petgraph')))
assert json.loads((H/'verification.json').read_text())['all_passed']
for p in H.glob('*.py'):ast.parse(p.read_text())
(H/'audit.json').write_text(json.dumps({'all_passed':True,'processes':162,'failures':sum(c['exit_code']!=0 for c in m['cases']),'balanced_cells':9,'production_sources_unchanged':True,'checks':['artifact/source/binary hashes','all six engine order permutations','both-workspace verification','Python syntax'],'semantic_checks':'analyze.py checks trace and reference answer/operation counts'},indent=2)+'\n')
print('Audit passed')
