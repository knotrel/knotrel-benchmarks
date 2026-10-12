"""Compare connected disassembly in the original uninstrumented pilot binaries."""
import hashlib,json,re,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parent/'2026-10-10-ett-scan-root'
b=json.loads((P/'builds.json').read_text());out={}
for v in ('before','after'):
 binary=Path(b['variants'][v]['binary']);assert hashlib.sha256(binary.read_bytes()).hexdigest()==b['variants'][v]['binary_sha256']
 symbols=subprocess.check_output(['nm',str(binary)],text=True)
 names=[line.split()[-1] for line in symbols.splitlines() if 'ForestGraph9connected' in line or ('GenericForestbE9connected' in line)]
 assert len(names)==2
 lines=subprocess.check_output(['otool','-tvV',str(binary)],text=True).splitlines();out[v]={}
 for n,name in enumerate(sorted(names)):
  start=lines.index(name+':');body=[]
  for line in lines[start+1:]:
   if not re.match(r'^[0-9a-f]{16}\s',line):break
   body.append(line)
  assert body
  base=int(body[0].split()[0],16);end=int(body[-1].split()[0],16)+4
  instructions=[re.sub(r'^[0-9a-f]{16}\s+','',line) for line in body]
  def relative(match):
   value=int(match[0],16)
   return f'function+{value-base:#x}' if base<=value<end else match[0]
  normalized=[re.sub(r'0x[0-9a-f]+',relative,line) for line in instructions]
  out[v][name]={'address':base,'instructions':len(body),'normalized':normalized}
  (H/f'{v}-function-{n}.txt').write_text(name+':\n'+'\n'.join(body)+'\n')
comparison={name:{'instructions':a['instructions'],'address_shift_bytes':out['after'][name]['address']-a['address'],'same_normalized_instructions':a['normalized']==out['after'][name]['normalized']} for name,a in out['before'].items()}
for name, result in comparison.items():
 a=out['before'][name]['normalized'];b=out['after'][name]['normalized']
 result['same_prefix_through_first_return']=a[:a.index('ret')+1]==b[:b.index('ret')+1]
(H/'assembly-audit.json').write_text(json.dumps({'functions':comparison,'disassembly':out},indent=2)+'\n')
print(json.dumps(comparison,indent=2))
