"""Verify preserved measurements, sources, Python syntax and balanced execution order."""
import ast,hashlib,json,sys
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
build=json.loads((H/'builds.json').read_text());assert hashes()==build['original_source_sha256']
checks={}
for folder,expected in ((H,2),):
 m=json.loads((folder/'manifest.json').read_text())
 for name,digest in m['artifact_sha256'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,(folder,name)
 groups=defaultdict(lambda:defaultdict(list))
 for c in m['cases']:
  assert c['exit_code']==0 and not c['timed_out']
  groups[(c['reference'],c['regime'])][c['pair']].append(c['variant'])
 # Reference names include source trial in the pilot; combine by actual trace identity.
 cells=defaultdict(list)
 for c in m['cases']:
  r=json.loads((folder/(c['name']+'.json')).read_text())
  key=(r['trace_fingerprint_fnv1a64'],c['regime'])
  cells[key].append(c)
 for key,entries in cells.items():
  pairs=defaultdict(list)
  for c in entries:pairs[c['pair']].append(c['variant'])
  assert sum(v==['before','after'] for v in pairs.values())==expected,key
  assert sum(v==['after','before'] for v in pairs.values())==expected,key
 checks[folder.name]={'artifact_hashes_checked':len(m['artifact_sha256']),'processes':len(m['cases']),'balanced_cells':len(cells)}
for folder in H.parent.glob(H.name+'*'):
 for p in folder.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for variant in ('before','after'):
 assert hashlib.sha256((H/(variant+'-forest.rs.txt')).read_bytes()).hexdigest()==build['variants'][variant]['forest_sha256']
assert json.loads((H/'reconstruction-verification.json').read_text())['all_passed']
gate=json.loads((H/'gate.json').read_text())
(H/'audit.json').write_text(json.dumps({'passed':True,'checks':checks,'source_hashes_match_frozen_ranking':True,'candidate_source_hashes_match':True,'python_syntax_valid':True,'pilot_gate_passed':gate['passed']},indent=2)+'\n')
print(json.dumps(checks,indent=2))
