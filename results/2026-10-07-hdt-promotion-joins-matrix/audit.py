"""Verify frozen inputs, measured artifacts and balanced per-cell order."""
import ast,hashlib,json,sys
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'manifest.json').read_text());build=m['builds']
assert hashes()==build['original_source_sha256']
assert build==json.loads((H.parent/'2026-10-07-hdt-promotion-joins/builds.json').read_text())
for name,digest in m['artifact_sha256'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==digest,name
for v,data in build['variants'].items():assert hashlib.sha256(Path(data['binary']).read_bytes()).hexdigest()==data['binary_sha256'],v
cells=defaultdict(lambda:defaultdict(list))
for c in m['cases']:
 ref=json.loads((ROOT/c['reference']).read_text())
 cells[(ref['trace_fingerprint_fnv1a64'],c['regime'])][c['pair']].append(c['variant'])
for key,pairs in cells.items():
 assert len(pairs)==4,key
 assert sum(v==['before','after'] for v in pairs.values())==2,key
 assert sum(v==['after','before'] for v in pairs.values())==2,key
assert len(cells)==38 and len(m['cases'])==304
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
(H/'audit.json').write_text(json.dumps({'passed':True,'measured_artifact_hashes_checked':len(m['artifact_sha256']),'source_hashes_match':True,'binary_hashes_match_pilot':True,'balanced_cells':len(cells),'processes':len(m['cases']),'python_syntax_valid':True},indent=2)+'\n')
print('Frozen hashes and all 38 balanced cells verified')
