#!/usr/bin/env python3
"""Record diagnostic HDT snapshots against a verified normal-run source manifest.

Timings are instrumented diagnostics, not a normal benchmark comparison. The
referenced manifest retains both checkouts' measured sources and patches.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess

from run_baseline import ROOT, command, hashes
from run_scale import run_measurement


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--source-manifest', required=True, type=Path)
    parser.add_argument('--nodes', nargs='+', type=int, default=[100000])
    parser.add_argument('--query-percent', nargs='+', type=int, default=[50, 99])
    parser.add_argument('--rounds', type=int, default=20)
    parser.add_argument('--workloads', nargs='+', default=['sustained-churn-path-v1', 'sustained-churn-blocks-v1'])
    args = parser.parse_args()
    before = hashes()
    reference = args.source_manifest.resolve()
    if json.loads(reference.read_text())['source_sha256'] != before:
        parser.error('source manifest does not match current build inputs')
    build_args = ['cargo', 'build', '--release', '--locked', '--bin', 'hdt-profile', '--message-format=json-render-diagnostics']
    build = subprocess.run(build_args, cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE)
    artifacts = [json.loads(line) for line in build.stdout.splitlines()]
    binary = next(Path(a['executable']) for a in artifacts if a.get('reason') == 'compiler-artifact' and a.get('target', {}).get('name') == 'hdt-profile' and a.get('executable'))
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    meta = {'source_manifest': str(reference.relative_to(ROOT)),
            'source_manifest_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
            'source_sha256': before, 'compiler': command(['rustc', '-vV']),
            'build_command': build_args, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'timing_scope': 'Instrumented cache-perturbed diagnostic timings; never aggregate with normal benchmarks.',
            'storage_scope': 'Vector capacity bytes and live ordered payload, excluding B-tree and allocator overhead; not total heap or RSS.',
            'cases': []}
    cases = list(itertools.product(args.nodes, args.query_percent, args.workloads, ['hdt', 'hdt-v2']))
    random.Random(42).shuffle(cases)
    for n, q, workload, engine in cases:
        name = f'{workload}-n{n}-q{q}-{engine}'
        invocation = [str(binary), '--nodes', str(n), '--query-percent', str(q), '--rounds', str(args.rounds), '--seed', '42', '--workload', workload, '--engine', engine]
        result, timed_out = run_measurement(invocation, 180)
        (destination / (name + '.json')).write_text(result.stdout)
        (destination / (name + '.stderr.txt')).write_text(result.stderr)
        meta['cases'].append({'name': name, 'command': invocation, 'exit_code': result.returncode, 'timed_out': timed_out})
        (destination / 'manifest.partial.json').write_text(json.dumps(meta, indent=2) + '\n')
        result.check_returncode()
        json.loads(result.stdout)
        print(name, flush=True)
    if hashes() != before:
        raise RuntimeError('source changed during diagnostic collection')
    (destination / 'run_hdt_profile.py').write_bytes(Path(__file__).read_bytes())
    # Retain imported collector helpers, including timeout/process-group behavior.
    for script in ['run_baseline.py', 'run_scale.py']:
        (destination / script).write_bytes((ROOT / 'scripts' / script).read_bytes())
    (destination / 'manifest.partial.json').unlink()
    meta['artifact_sha256'] = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')


if __name__ == '__main__':
    main()
