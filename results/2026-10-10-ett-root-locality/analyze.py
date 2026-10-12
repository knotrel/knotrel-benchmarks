"""Compare root access sequences and virtual address coverage, not cache misses."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
m=json.loads((H/'manifest.json').read_text())
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
assert len(m['runs'])==8 and all(r['exit_code']==0 for r in m['runs'])
assert all(r['exit_code']==0 for r in m['checks'])
rows=[];reference=None;semantics=None
for r in m['runs']:
 x=json.loads((H/(r['name']+'.json')).read_text());run=x['repetitions'][0];access=run['root_accesses'];seq=[a[0] for a in access]
 shape={'fingerprint':x['trace_fingerprint_fnv1a64'],'forest_stats':run['forest_stats'],'query_true_count':(run['query_true'] or {}).get('count',0),'query_false_count':(run['query_false'] or {}).get('count',0)}
 if reference is None:reference=seq;semantics=shape
 assert seq==reference and shape==semantics
 coords=[a[1] for a in access];lines=[c//m['line_bytes'] for c in coords];pages=[c//m['page_bytes'] for c in coords]
 rows.append({'name':r['name'],'accesses':len(seq),'unique_tokens':len(set(seq)),'unique_lines':len(set(lines)),'unique_pages':len(set(pages)),'line_transitions':sum(a!=b for a,b in zip(lines,lines[1:])),'page_transitions':sum(a!=b for a,b in zip(pages,pages[1:])),'first_parent_coordinate_mod_page':coords[0]%m['page_bytes'],'sequence_sha256':hashlib.sha256(json.dumps(seq,separators=(',',':')).encode()).hexdigest()})
(H/'comparison.json').write_text(json.dumps({'all_sequences_identical':True,'semantics':semantics,'rows':rows},indent=2)+'\n')
for r in rows:print(r)
