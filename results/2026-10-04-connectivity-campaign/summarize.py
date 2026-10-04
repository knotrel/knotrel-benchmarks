"""Rebuild this campaign's aggregates from raw JSON; does not pool trial samples.
Run from any directory. Raw collections must be siblings of this directory.
"""
from collections import defaultdict
import hashlib,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
COLLECTIONS=['sparse','dense','repeats','cogentco']
LABELS={'compact-bfs':'Knotrel default / compact BFS','ett-scan':'Knotrel experimental / ETT','hdt':'Knotrel experimental / HDT','petgraph-dfs':'External / petgraph 0.8.3 DFS'}

def build():
    groups=defaultdict(list)
    fingerprints=defaultdict(set)
    cases=0
    for family in COLLECTIONS:
        directory=ROOT/f'2026-10-04-{family}-campaign'
        manifest=json.loads((directory/'manifest.json').read_text())
        for case in manifest['cases']:
            assert case['exit_code']==0 and not case['timed_out']
            path=directory/(case['name']+'.json')
            assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['artifact_sha256'][path.name]
            report=json.loads(path.read_text()); assert len(report['repetitions'])==1
            run=report['repetitions'][0]
            nodes=case.get('nodes',report.get('import',{}).get('node_count'))
            workload=case.get('workload',report['workload'])
            query_percent=case.get('query_percent')
            key=(family,workload,nodes,query_percent,case['regime'],case['engine'])
            fingerprints[key[:-1]].add(report['trace_fingerprint_fnv1a64'])
            values={'base_total_ns':sum(v['total_ns'] for v in run['measurements'].values() if v),
                    'peak_process_rss_bytes':case['peak_process_rss_bytes'],'setup_ns':run['setup_ns']}
            for operation,samples in list(run['measurements'].items())+[('repeated_queries',run['repeated_queries'])]:
                for stat in ['count','p50_ns','p95_ns','p99_ns','total_ns']:
                    values[operation+'_'+stat]=samples[stat] if samples else None
            groups[key].append(values);cases+=1
    assert all(len(f)==1 for f in fingerprints.values()),'backends did not receive identical traces'
    output=[]
    for key,trials in sorted(groups.items()):
        item=dict(zip(['family','workload','nodes','query_percent','regime','engine'],key))
        item['identity']=LABELS[item['engine']];item['trials']=len(trials);item['metrics']={}
        for metric in trials[0]:
            values=[t[metric] for t in trials if t[metric] is not None]
            assert not values or len(values)==len(trials), 'inconsistent missing metrics'
            item['metrics'][metric]=None if not values else {'min':min(values),'median':statistics.median(values),'max':max(values)}
        output.append(item)
    return {'cases':cases,'meaning':'min/median/max across process trials; percentile metrics are summaries of per-process percentiles, not pooled percentiles','groups':output}

if __name__=='__main__':
    (HERE/'summary.json').write_text(json.dumps(build(),indent=2)+'\n')
