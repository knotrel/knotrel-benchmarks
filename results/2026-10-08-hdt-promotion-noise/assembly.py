"""Inspect frozen binaries; preserve excerpts and conservative normalized diffs."""
import json,subprocess,re,hashlib,difflib
from pathlib import Path
H=Path(__file__).resolve().parent;build=json.loads((H.parent/'2026-10-07-hdt-promotion-joins/builds.json').read_text())
tool=subprocess.check_output(['xcrun','--find','llvm-objdump'],text=True).strip();parsed={};commands={}
for v,b in build['variants'].items():
 assert hashlib.sha256(Path(b['binary']).read_bytes()).hexdigest()==b['binary_sha256']
 cmd=[tool,'--disassemble','--demangle','--no-show-raw-insn',b['binary']];commands[v]=cmd
 out=subprocess.check_output(cmd,text=True);funcs={};name=None
 for line in out.splitlines():
  m=re.match(r'^([0-9a-f]+) <(.+)>:$',line)
  if m:name=m[2];funcs[name]={'address':m[1],'lines':[]}
  elif name and re.match(r'^[0-9a-f]+:',line):funcs[name]['lines'].append(line)
 parsed[v]=funcs
names=['<knotrel_core::hdt_forest::Forest>::'+s for s in ('link','join','reroot','connected')]+['<knotrel_core::hdt::HdtGraph>::'+s for s in ('cut','link','promote','connected')]
rows=[]
def normalize(line):
 line=re.sub(r'^[0-9a-f]+:\s*','',line)
 return re.sub(r'0x[0-9a-f]+ (<.*>)',r'\1',line)
for i,name in enumerate(names):
 b,a=(parsed[v][name] for v in ('before','after'))
 for v in ('before','after'):
  d=parsed[v][name];(H/f'assembly-{i}-{v}.txt').write_text(d['address']+' <'+name+'>:\n'+'\n'.join(d['lines'])+'\n')
 bn,an=([normalize(l) for l in d['lines']] for d in (b,a))
 (H/f'assembly-{i}-normalized.diff').write_text(''.join(difflib.unified_diff([l+'\n' for l in bn],[l+'\n' for l in an],fromfile='before',tofile='after')))
 prefix=0
 for left,right in zip(b['lines'],a['lines']):
  if left!=right:break
  prefix+=1
 rows.append({'symbol':name,'before_address':b['address'],'after_address':a['address'],'before_instructions':len(bn),'after_instructions':len(an),'normalized_equal':bn==an,'exact_disassembly_prefix_instructions':prefix})
(H/'assembly.json').write_text(json.dumps({'commands':commands,'tool_version':subprocess.check_output([tool,'--version'],text=True),'normalization':'Remove instruction-address prefixes and numeric address preceding a symbol annotation; retain annotation, offsets, registers and immediate operands. This is textual disassembly comparison, not byte equality or semantic proof.','rows':rows},indent=2)+'\n')
lines=['# Frozen-binary code inspection','','[assembly.json](assembly.json) records tool/version/commands and normalization. Raw excerpts and normalized diffs are saved per row in order. Only instruction-address prefixes and numeric target addresses preceding symbol annotations are removed; symbol offsets, registers and other immediates remain. Equality is textual under those rules, not full binary equality.','','| Symbol | Before address | After address | Instructions before/after | Normalized equal | Exact disassembly prefix |','|---|---|---|---:|---|---:|']
for r in rows:lines.append(f"| `{r['symbol']}` | `{r['before_address']}` | `{r['after_address']}` | {r['before_instructions']}/{r['after_instructions']} | {r['normalized_equal']} | {r['exact_disassembly_prefix_instructions']} |")
lines+=['','The ordinary Forest::link retains its address and instruction count; its disassembly is identical through the first return. Differences afterward include relocated allocation-call targets and panic metadata. There is no extra wrapper call visible on that ordinary return path. HdtGraph::promote grows by 129 AArch64 instructions (516 bytes); later symbols move by 0x204. The compiler incorporated the promoted-link work into promote rather than emitting a separate promoted-link symbol.','','This rules against an obvious added ordinary-link wrapper on the inspected path. It does not rule out data/code layout or hardware effects, and does not establish them as the timing cause. No performance counters, affinity control or cache flushing were used.']
# Check the precise prefix claim directly.
f=parsed['before'][names[0]]['lines'];ret=next(i for i,l in enumerate(f) if re.search(r'\bret\s*$',l));assert rows[0]['exact_disassembly_prefix_instructions']>ret
assert rows[6]['after_instructions']-rows[6]['before_instructions']==129
(H/'assembly.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(rows,indent=2))
