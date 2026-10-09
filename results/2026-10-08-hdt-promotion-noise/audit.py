"""Verify same-binary controls, all planned pairs and frozen source hashes."""
import ast,hashlib,json,sys
from pathlib import Path
from collections import defaultdict
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'manifest.json').read_text());assert hashes()==m['builds']['original_source_sha256']
for name,digest in m['artifact_sha256'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==digest,name
for b in m['builds']['variants'].values():assert hashlib.sha256(Path(b['binary']).read_bytes()).hexdigest()==b['binary_sha256']
groups=defaultdict(lambda:defaultdict(list))
for c in m['cases']:
 assert c['exit_code']==0 and not c['timed_out']
 groups[c['cell'],c['mode']][c['trial']].append(c)
for (cell,mode),pairs in groups.items():
 assert len(pairs)==4
 assert sum([c['label'] for c in pair]==['left','right'] for pair in pairs.values())==2
 assert sum([c['label'] for c in pair]==['right','left'] for pair in pairs.values())==2
 for pair in pairs.values():
  if mode.startswith('AA_'):assert pair[0]['command']==pair[1]['command']
  else:assert {c['label']:c['variant'] for c in pair}=={'left':'before','right':'after'}
assert len(groups)==21 and len(m['cases'])==168
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
(H/'audit.json').write_text(json.dumps({'passed':True,'successful_processes':168,'balanced_cell_modes':21,'same_binary_AA_commands':True,'frozen_source_and_binary_hashes':True,'measured_artifact_hashes':len(m['artifact_sha256'])},indent=2)+'\n')
print('All 168 processes, 21 balanced groups and exact A/A commands verified')
