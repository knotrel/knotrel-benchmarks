#!/usr/bin/env python3
"""Record isolated backend processes, including whole-process peak resident memory.

macOS /usr/bin/time -l reports bytes; Linux time -v reports KiB. RSS includes
trace generation, exported JSON, warmup and harness, not just engine allocations.
No engine or query timeout failures are silently dropped. Use a new output folder.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import random
import re
import signal
import subprocess
import sys

from run_baseline import ROOT, CORE, command, hashes


def peak_rss(stderr, system):
    """Normalize the platform time tool's peak process RSS to bytes."""
    if system == 'darwin':
        match = re.search(r'^\s*(\d+)\s+maximum resident set size\s*$', stderr, re.M)
        return int(match[1]) if match else None
    match = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)', stderr)
    return int(match[1]) * 1024 if match else None


def run_measurement(invocation, timeout):
    """Bound both time wrapper and benchmark lifetime; preserve partial output."""
    with subprocess.Popen(invocation, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return subprocess.CompletedProcess(invocation, process.returncode, stdout, stderr), False
        except subprocess.TimeoutExpired:
            # The new session belongs exclusively to this measurement. Killing
            # its group also stops the benchmark child of /usr/bin/time.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(invocation, 124, stdout, stderr), True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--nodes', nargs='+', type=int, default=[10000, 100000])
    parser.add_argument('--query-percent', nargs='+', type=int, default=[10, 50, 90, 99])
    parser.add_argument('--rounds', type=int, default=20)
    parser.add_argument('--trials', type=int, default=2)
    parser.add_argument('--regimes', nargs='+', choices=['fresh', 'warmed'], default=['fresh', 'warmed'])
    parser.add_argument('--engines', nargs='+', default=['compact-bfs','petgraph-dfs','ett-scan'])
    parser.add_argument('--workloads', nargs='+', default=['sustained-churn-path-v1','sustained-churn-blocks-v1'])
    parser.add_argument('--query-repeats', type=int, default=0)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if min(args.nodes) < 2 or min(args.rounds,args.trials,args.timeout) < 1 or args.query_repeats < 0:
        parser.error('invalid size/count')
    if any(not 1 <= q <= 99 for q in args.query_percent): parser.error('query percentage must be 1..99')
    if sys.platform not in ['darwin','linux']: parser.error('RSS collector supports macOS and Linux')
    destination=args.destination.resolve();destination.mkdir(parents=True,exist_ok=False)
    before=hashes()
    meta={'platform':platform.platform(),'compiler':command(['rustc','-vV']),
          'source_sha256':before,'arguments':vars(args)|{'destination':str(destination)},
          'memory_scope':'Peak entire child process, including trace, export, warmups, samples and engine. Not engine-only RSS.',
          'environment':{k:os.environ.get(k) for k in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_BUILD_TARGET','CARGO_TARGET_DIR']},
          'cases':[]}
    for name,root in [('benchmarks',ROOT),('core',CORE)]:
        meta[name]={'revision':command(['git','rev-parse','HEAD'],root),'status':command(['git','status','--porcelain'],root)}
        (destination/f'{name}.patch').write_text(command(['git','diff','--binary','HEAD'],root)+'\n')
        for relative in command(['git','ls-files','--others','--exclude-standard'],root).splitlines():
            f=root/relative
            if relative.startswith('crates/') and f.suffix=='.rs':
                saved=destination/'untracked'/name/relative;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(f.read_bytes())
    for script in ['run_scale.py','run_baseline.py']:
        (destination/script).write_bytes((ROOT/'scripts'/script).read_bytes())
    build_args=['cargo','build','--release','--locked','--message-format=json-render-diagnostics']
    meta['build_command']=build_args
    build=subprocess.run(build_args,cwd=ROOT,check=True,text=True,stdout=subprocess.PIPE)
    artifacts=[json.loads(line) for line in build.stdout.splitlines()]
    binary=next(Path(a['executable']) for a in artifacts if a.get('reason')=='compiler-artifact' and a.get('target',{}).get('name')=='knotrel-benchmarks' and a.get('executable'))
    meta['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    cases=list(itertools.product(args.nodes,args.query_percent,args.workloads,range(args.trials),args.regimes,args.engines))
    random.Random(42).shuffle(cases)
    for i,(n,q,workload,trial,regime,engine) in enumerate(cases):
        name=f'{workload}-n{n}-q{q}-{regime}-p{trial}-{engine}'
        invocation=[str(binary),'--nodes',str(n),'--rounds',str(args.rounds),'--workload',workload,'--query-percent',str(q),
                    '--engine',engine,'--warmup',str(int(regime=='warmed')),'--repetitions','1','--seed','42',
                    '--query-repeats',str(args.query_repeats),'--trace-out',str(destination/(name+'.trace.json'))]
        timed=['/usr/bin/time','-l' if sys.platform=='darwin' else '-v',*invocation]
        print(f'{i+1}/{len(cases)} {name}',flush=True)
        result,timed_out=run_measurement(timed,args.timeout)
        (destination/(name+'.stderr.txt')).write_text(result.stderr)
        case={'name':name,'nodes':n,'query_percent':q,'workload':workload,'trial':trial,'regime':regime,'engine':engine,
              'command':timed,'timed_out':timed_out,'exit_code':result.returncode,'peak_process_rss_bytes':peak_rss(result.stderr,sys.platform)}
        meta['cases'].append(case)
        (destination/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
        if result.returncode:
            (destination/(name+'.partial-stdout.txt')).write_text(result.stdout)
        result.check_returncode()
        json.loads(result.stdout)
        if case['peak_process_rss_bytes'] is None: raise RuntimeError('missing process RSS')
        (destination/(name+'.json')).write_text(result.stdout)
    if before!=hashes():raise RuntimeError('source changed during measurement')
    for script in ['run_scale.py','run_baseline.py']:
        if (destination/script).read_bytes()!=(ROOT/'scripts'/script).read_bytes():raise RuntimeError('collector changed')
    (destination/'manifest.partial.json').unlink()
    meta['artifact_sha256']={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')


if __name__=='__main__':main()
