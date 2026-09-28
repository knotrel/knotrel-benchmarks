#!/usr/bin/env python3
"""Write one CSV row per isolated measured process; preserve missing categories."""
import csv
import json
from pathlib import Path
import sys


def rows(directory):
    """Read verified schema-2 single-backend cases, keeping trials distinct."""
    manifest=json.loads((directory/'manifest.json').read_text())
    result=[]
    for case in manifest['cases']:
        report=json.loads((directory/(case['name']+'.json')).read_text())
        assert report['schema_version']==2 and len(report['repetitions'])==1
        run=report['repetitions'][0]
        row={key:case[key] for key in ['name','nodes','query_percent','workload','trial','regime','engine','peak_process_rss_bytes']}
        row['setup_ns']=run['setup_ns']
        row['workload_wall_ns']=run['workload_wall_ns']
        row['base_operations_total_ns']=sum(v['total_ns'] for v in run['measurements'].values() if v)
        for name,value in list(run['measurements'].items())+[(k,run[k]) for k in ['query_true','query_false','repeated_queries']]:
            for stat in ['count','total_ns','p50_ns','p95_ns','p99_ns','max_ns']:
                row[name+'_'+stat]=value[stat] if value else None
        for stat in ['tree_cuts','scanned_vertices','candidate_edges','replacements']:
            row[stat]=run['forest_stats'][stat] if run.get('forest_stats') else None
        for stat in ['tree_cuts','candidate_edges','replacements','tree_promotions','non_tree_promotions','levels_visited']:
            row['hdt_'+stat]=run['hdt_stats'][stat] if run.get('hdt_stats') else None
        result.append(row)
    return result


if __name__=='__main__':
    directory=Path(sys.argv[1]);summary=rows(directory)
    with (directory/'summary.csv').open('x',newline='') as output:
        writer=csv.DictWriter(output,fieldnames=list(summary[0]))
        writer.writeheader();writer.writerows(summary)
