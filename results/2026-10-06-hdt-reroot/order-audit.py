"""Qualify global alternation and disclose per-cell order imbalance."""
import json
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent
out={}
for folder in (H,H.parent/'2026-10-06-hdt-reroot-confirmation'):
 if not (folder/'manifest.json').exists():continue
 m=json.loads((folder/'manifest.json').read_text());seen=set();counts=defaultdict(lambda:{'before_first':0,'after_first':0})
 for c in m['cases']:
  if c['pair'] in seen:continue
  seen.add(c['pair']);r=json.loads((H.parents[1]/c['reference']).read_text())
  k=' / '.join(map(str,[r['workload'],r.get('config',{}).get('nodes',r.get('import',{}).get('node_count')),r.get('query_percent'),c['regime']]))
  counts[k][c['variant']+'_first']+=1
 out[folder.name]=dict(counts)
(H/'order-audit.json').write_text(json.dumps(out,indent=2)+'\n')
p=H/'README.md';s=p.read_text();s=s.replace('Each cell uses three sequential pairs, with alternating before/after execution order and a seeded shuffle.', 'Each cell uses three sequential pairs. Before/after order alternates globally after a seeded shuffle; per-cell order balance is not enforced. Six initial cells have the same variant first in all three pairs. See [order-audit.json](order-audit.json), including the separate confirmation order counts.')
s=s.replace('then report.py.', 'then report.py and order-audit.py.')
p.write_text(s)
