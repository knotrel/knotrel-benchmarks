"""Rebuild exact-cell before/after comparisons, including historical drift."""
from collections import defaultdict
import hashlib,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def read(family,workspace):
    directory=ROOT/(f'2026-10-04-workspace-v2-{family}-confirmation' if workspace else f'2026-10-04-{family}-campaign')
    manifest=json.loads((directory/'manifest.json').read_text())
    groups=defaultdict(list)
    for case in manifest['cases']:
        if case['engine'] not in ('compact-bfs','compact-workspace'):continue
        path=directory/(case['name']+'.json')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['artifact_sha256'][path.name]
        assert case['exit_code']==0 and not case['timed_out']
        report=json.loads(path.read_text());run=report['repetitions'][0]
        key=(case.get('workload',report['workload']),case.get('nodes',report.get('import',{}).get('node_count')),case.get('query_percent'),case['regime'])
        values={'runtime_ns':run['workload_wall_ns'],'setup_ns':run['setup_ns'],'rss_bytes':case['peak_process_rss_bytes']}
        for op,m in list(run['measurements'].items())+[('repeated',run['repeated_queries'])]:
            for field in ['count','p50_ns','p95_ns','p99_ns','total_ns']:
                values[f'{op}_{field}']=None if m is None else m[field]
        groups[(key,case['engine'])].append((report['trace_fingerprint_fnv1a64'],values))
    return groups

def build():
    result=[]
    for family in ['dense']:
        new=read(family,True);old=read(family,False)
        for key,engine in sorted(new):
            if engine!='compact-bfs':continue
            before=new[(key,'compact-bfs')];after=new[(key,'compact-workspace')];historical=old[(key,'compact-bfs')]
            assert len(before)==len(after)
            assert len({h for values in [before,after,historical] for h,_ in values})==1,'trace changed'
            row=dict(zip(['workload','nodes','query_percent','regime'],key))|{'family':family,'trials':len(before),'metrics':{}}
            for metric in before[0][1]:
                samples=[[v[metric] for _,v in values] for values in [before,after,historical]]
                if all(all(x is None for x in v) for v in samples):row['metrics'][metric]=None;continue
                assert all(all(x is not None for x in v) for v in samples)
                b,a,h=[statistics.median(v) for v in samples]
                row['metrics'][metric]={'before':b,'after':a,'historical':h,'delta_percent':100*(a/b-1) if b else None,'baseline_drift_percent':100*(b/h-1) if h else None,'before_range':[min(samples[0]),max(samples[0])],'after_range':[min(samples[1]),max(samples[1])],'range_separated':max(samples[1])<min(samples[0]) or max(samples[0])<min(samples[1])}
            result.append(row)
    return {'meaning':'after is workspace, before is unchanged BFS in same binary, historical is original campaign; percent is 100*(after/before-1); negative improves; RSS whole-process, not heap','cells':result}

if __name__=='__main__':
    (HERE/'dense-confirmation.json').write_text(json.dumps(build(),indent=2)+'\n')
