#!/usr/bin/env python3
"""Exact-connectivity and cache-invalidation probe for GraphScope 0.29.0.

Importing this module needs only Python's standard library. GraphScope is loaded
only by main, and calls use its explicit analytical builtin rather than a
NetworkX fallback. Timings are diagnostic client-to-engine durations, not a
native-core comparison. Run each invocation in a fresh process/container.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys
import time
import traceback


def node_key(node):
    """Encode the entire Knotrel u64 domain losslessly as GraphScope string IDs."""
    if type(node) is not int or not 0 <= node < 2**64:
        raise ValueError('node must be a u64 integer')
    return str(node)


def from_export(envelope):
    """Read the version-1 trace envelope; accept small oracle-checked graphs only."""
    if envelope['schema_version'] != 1:
        raise ValueError('unsupported trace schema')
    n = envelope['config']['nodes']
    if type(n) is not int or not 1 <= n <= 128:
        raise ValueError('functional probe supports 1..128 vertices')
    return dict(name=envelope['workload'], nodes=list(range(n)),
                initial_edges=envelope['trace']['initial_edges'],
                operations=envelope['trace']['operations'])


def contract_cases():
    """Small hand-derived cases including repeated endpoints across state changes."""
    def query(a, b, expected):
        return dict(op='connected', source=a, target=b, expected=expected)
    def update(op, a, b, changed=True):
        return dict(op=op, source=a, target=b, changed=changed)
    bridge = dict(name='bridge-cache-invalidation', nodes=list(range(6)),
                  initial_edges=[[0, 1], [1, 2], [2, 3]], operations=[])
    bridge['operations'] = ([query(0, 3, True)] * 3
        + [update('cut', 1, 2)] + [query(0, 3, False)] * 3
        + [update('cut', 1, 2, False), query(4, 4, True), query(4, 5, False)]
        + [update('link', 1, 2)] + [query(0, 3, True)] * 3
        + [update('link', 2, 1, False), query(3, 0, True)])
    cycle = dict(name='cycle-alternative-then-split', nodes=list(range(6)),
                 initial_edges=[[0, 1], [1, 2], [2, 3], [3, 0]], operations=[
                     query(0, 2, True), update('cut', 0, 1), query(0, 2, True),
                     update('cut', 0, 3), query(0, 2, False), query(0, 2, False),
                     update('link', 0, 1), query(0, 2, True)])
    join = dict(name='separate-components-join-split', nodes=list(range(6)),
                initial_edges=[[0, 1], [2, 3]], operations=[
                    query(0, 3, False), update('link', 1, 2), query(0, 3, True),
                    update('cut', 1, 2), query(0, 3, False), query(0, 3, False)])
    large = 2**64-1
    width = dict(name='full-u64-string-mapping', nodes=[0, large, large-1],
                 initial_edges=[[0, large]], operations=[query(0, large, True),
                     update('cut', large, 0), query(0, large, False),
                     update('link', large, large-1), query(large, large-1, True)])
    return [bridge, cycle, join, width]


def validate_case(case):
    """Validate topology answers using independent matrix transitive closure.

    Recompute Floyd-Warshall for each query: O(q*n^3 + updates), O(n^2)
    scratch. This is a small-graph validation oracle, never a timed backend.
    Each diagonal is reachable even for isolated vertices; updates are symmetric.
    """
    nodes = case['nodes']
    if not nodes or len(nodes) > 128 or len(set(nodes)) != len(nodes):
        raise ValueError('need 1..128 unique nodes')
    for node in nodes:
        node_key(node)
    indices = {node: i for i, node in enumerate(nodes)}
    matrix = [[False] * len(nodes) for _ in nodes]
    def endpoints(a, b):
        if a not in indices or b not in indices:
            raise ValueError('unknown endpoint')
        return indices[a], indices[b]
    for a, b in case['initial_edges']:
        i, j = endpoints(a, b)
        if i == j or matrix[i][j]:
            raise ValueError('invalid initial edge')
        matrix[i][j] = matrix[j][i] = True
    for op in case['operations']:
        i, j = endpoints(op['source'], op['target'])
        if op['op'] in ('link', 'cut'):
            if i == j:
                raise ValueError('self-loop')
            inserted = op['op'] == 'link'
            if (matrix[i][j] != inserted) != op.get('changed', True):
                raise ValueError('wrong expected mutation result')
            matrix[i][j] = matrix[j][i] = inserted
        elif op['op'] == 'connected':
            reach = [row[:] for row in matrix]
            for v in range(len(nodes)):
                reach[v][v] = True
            for k in range(len(nodes)):
                for a in range(len(nodes)):
                    for b in range(len(nodes)):
                        reach[a][b] |= reach[a][k] and reach[k][b]
            if type(op['expected']) is not bool or reach[i][j] != op['expected']:
                raise ValueError('wrong topology-derived query answer')
        else:
            raise ValueError('unknown operation')


class GraphScopeBackend:
    """Small synchronous adapter, including existence checks and mutation flush.

    number_of_edges is a public reporting operation that drains mutation buffers
    in the pinned version. Charge this synchronization to the mutation. The
    client metadata cache remains enabled; there is no user answer cache. ID
    conversion and bridge calls are included in timed operation costs.
    """
    def __init__(self, nx, has_path, case):
        self.graph = nx.Graph()
        self.has_path = has_path
        self.graph.add_nodes_from(node_key(n) for n in case['nodes'])
        self.graph.add_edges_from((node_key(a), node_key(b)) for a, b in case['initial_edges'])
        if self.graph.number_of_edges() != len(case['initial_edges']):
            raise RuntimeError('initial edge count mismatch')

    def execute(self, op):
        """Return changed/connected, enforcing Knotrel's simple-graph contract."""
        a, b = node_key(op['source']), node_key(op['target'])
        if op['op'] == 'connected':
            if not self.graph.has_node(a) or not self.graph.has_node(b):
                raise ValueError('unknown node')
            # Existing-node reflexivity is part of the adapter contract; avoid
            # relying on traversal implementations to discover the empty path.
            return a == b or bool(self.has_path(self.graph, a, b))
        if a == b:
            raise ValueError('self-loop')
        exists = self.graph.has_edge(a, b)
        if op['op'] == 'link':
            self.graph.add_edge(a, b)
            changed = not exists
        elif op['op'] == 'cut':
            if exists:
                self.graph.remove_edge(a, b)
            changed = exists
        else:
            raise ValueError('unknown operation')
        self.graph.number_of_edges()
        return changed

    def close(self):
        """Release the graph using the public API; cleanup is timed separately."""
        self.graph.clear()


def replay(nx, has_path, case, repeat_queries):
    """Time original and repeated queries separately, checking every response."""
    start = time.perf_counter_ns()
    backend = GraphScopeBackend(nx, has_path, case)
    result = dict(case=case['name'], setup_ns=time.perf_counter_ns()-start,
                  samples=[], passed=False)
    try:
        for index, op in enumerate(case['operations']):
            repetitions = 1 + repeat_queries if op['op'] == 'connected' else 1
            expected = op['expected'] if op['op'] == 'connected' else op.get('changed', True)
            for repeat in range(repetitions):
                start = time.perf_counter_ns()
                actual = backend.execute(op)
                elapsed = time.perf_counter_ns()-start
                if actual != expected:
                    raise RuntimeError(f"stale/incorrect answer at operation {index}, repeat {repeat}: {actual} != {expected}")
                result['samples'].append(dict(index=index, op=op['op'], query_repeat=repeat,
                                               expected=expected, actual=actual, elapsed_ns=elapsed))
        result['passed'] = True
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        start = time.perf_counter_ns()
        backend.close()
        result['cleanup_ns'] = time.perf_counter_ns()-start
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trace', type=Path, action='append', default=[])
    parser.add_argument('--repeat-queries', type=int, default=2)
    parser.add_argument('--repetitions', type=int, default=2)
    args = parser.parse_args()
    if args.repeat_queries < 0 or args.repetitions < 1:
        parser.error('query repeats >=0 and repetitions >=1 are required')
    cases = contract_cases()
    for path in args.trace:
        cases.append(from_export(json.loads(path.read_text())))
    for case in cases:
        validate_case(case)
    # Exclusive creation happens before launching any engine; never overwrite.
    with args.output.open('x') as output:
        report = dict(schema_version=1, engine='graphscope.nx/analytical-sssp_has_path',
                      graphscope_required='0.29.0', passed=False, runs=[],
                      environment=dict(platform=platform.platform(), machine=platform.machine(), python=sys.version),
                      cache_protocol=dict(fresh_process=True, same_graph_query_repeats=args.repeat_queries,
                                          fresh_graph_repetitions=args.repetitions, hardware_caches_flushed=False,
                                          engine_session_reused=True, explicit_replay_warmup=0),
                      argv=sys.argv, cases=cases,
                      trace_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in args.trace})
        session = None
        try:
            import graphscope
            from graphscope.nx.algorithms.builtin import has_path
            version = importlib.metadata.version('graphscope')
            report['graphscope_version'] = version
            if version != '0.29.0':
                raise RuntimeError('only GraphScope 0.29.0 is verified by this probe')
            start = time.perf_counter_ns()
            session = graphscope.session(cluster_type='hosts', num_workers=1)
            report['session_start_ns'] = time.perf_counter_ns()-start
            nx = session.nx()
            for repetition in range(args.repetitions):
                for case in cases:
                    print(f"GraphScope: repetition {repetition}, {case['name']}", file=sys.stderr, flush=True)
                    result = replay(nx, has_path, case, args.repeat_queries)
                    result['repetition'] = repetition
                    report['runs'].append(result)
                    if not result['passed']:
                        raise RuntimeError('equivalence probe failed; see operation error')
            report['passed'] = True
        except Exception:
            report['error'] = traceback.format_exc()
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    report['shutdown_error'] = traceback.format_exc()
                    report['passed'] = False
            json.dump(report, output, indent=2)
            output.write('\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
