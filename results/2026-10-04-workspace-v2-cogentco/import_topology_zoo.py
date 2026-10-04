#!/usr/bin/env python3
"""Convert a pinned, flat undirected GraphML topology into an offline import trace.

Only Python's standard library is required. No network access or timed kernel
operations occur here. Original input files and generated traces stay local.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NS = '{http://graphml.graphdrawing.org/xmlns}'
MASK = (1 << 64) - 1


class Lcg:
    """Explicit wrapping LCG; modulo reduction is reproducible but biased."""
    def __init__(self, seed):
        self.state = seed

    def below(self, bound):
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & MASK
        return self.state % bound


def parse_graphml(raw):
    """Return sorted source IDs and physical links, rejecting semantic loss."""
    text = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD and entity declarations are unsupported')
    root = ET.fromstring(text)
    if root.tag != NS + 'graphml':
        raise ValueError('expected namespaced GraphML root')
    graphs = list(root.iter(NS + 'graph'))
    if len(graphs) != 1 or graphs[0] not in list(root):
        raise ValueError('exactly one flat graph is required')
    graph = graphs[0]
    if graph.get('edgedefault') != 'undirected':
        raise ValueError('only undirected graphs are supported')
    for element in root.iter():
        if element.tag in {NS+'hyperedge', NS+'port', NS+'locator', NS+'endpoint'}:
            raise ValueError('hyperedges, ports and external references are unsupported')
    allowed = {NS+'node', NS+'edge', NS+'data', NS+'desc'}
    if any(child.tag not in allowed for child in graph):
        raise ValueError('unsupported graph child')
    for kind in ('node', 'edge'):
        if list(root.iter(NS+kind)) != graph.findall(NS+kind):
            raise ValueError('structural elements must be direct graph children')
    node_elements = graph.findall(NS+'node')
    ids = [node.get('id') for node in node_elements]
    if any(not key for key in ids) or len(set(ids)) != len(ids) or len(ids) < 2:
        raise ValueError('at least two unique nonempty node IDs are required')
    ids.sort(key=lambda key: key.encode('utf-8'))
    mapping = {key: i for i, key in enumerate(ids)}
    links, edge_ids, loops = [], set(), 0
    edges = graph.findall(NS+'edge')
    for index, edge in enumerate(edges):
        if edge.get('directed', 'false') not in ('false', '0'):
            raise ValueError('directed edges are unsupported')
        if any(attr in edge.attrib for attr in ('sourceport','targetport')):
            raise ValueError('edge ports are unsupported')
        a, b = edge.get('source'), edge.get('target')
        if a not in mapping or b not in mapping:
            raise ValueError('edge references an unknown node')
        supplied_id = edge.get('id')
        if supplied_id is not None:
            if not supplied_id or supplied_id in edge_ids:
                raise ValueError('edge IDs must be nonempty and unique when supplied')
            edge_ids.add(supplied_id)
        identity = 'id:' + supplied_id if supplied_id is not None else f'index:{index}'
        if a == b:
            loops += 1
            continue
        source, target = sorted((mapping[a], mapping[b]))
        links.append({'id': identity, 'source': source, 'target': target})
    links.sort(key=lambda link: link['id'].encode('utf-8'))
    return ids, links, loops, len(edges)


def components(node_count, links, active):
    """Independent source-link union-find oracle, rebuilt for each source batch."""
    parent = list(range(node_count))
    def root(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    for index in sorted(active):
        edge = links[index]
        a, b = root(edge['source']), root(edge['target'])
        parent[a] = b
    return [root(node) for node in range(node_count)]


def build_trace(raw, args):
    """Produce normalized mutations and source-derived expected query answers."""
    if hashlib.sha256(raw).hexdigest() != args.sha256.lower():
        raise ValueError('source SHA-256 mismatch')
    if not 0 <= args.seed <= MASK or args.queries < 0 or args.failures < 1:
        raise ValueError('seed must be u64, queries nonnegative, failures positive')
    date.fromisoformat(args.retrieved_date)
    for field in ('source_url', 'source_revision', 'license', 'citation'):
        if not getattr(args, field).strip():
            raise ValueError(f'{field} must be nonempty')
    ids, links, loops, records = parse_graphml(raw)
    if args.failures > len(links):
        raise ValueError('failures exceeds non-loop physical link count')
    counts = Counter((edge['source'], edge['target']) for edge in links)
    initial = sorted(counts)
    order = list(range(len(links)))
    rng = Lcg(args.seed)
    for index in range(len(order)-1, 0, -1):
        other = rng.below(index+1)
        order[index], order[other] = order[other], order[index]
    failed = order[:args.failures]
    active = set(range(len(links)))
    initial_components = components(len(ids), links, active)
    # Bridge count for the projected simple graph, outside benchmark timing.
    # Removing all physical links of a pair distinguishes projected from physical bridges.
    initial_component_count = len(set(initial_components))
    bridges = 0
    for pair in initial:
        without = {i for i,e in enumerate(links) if (e['source'],e['target']) != pair}
        bridges += len(set(components(len(ids), links, without))) > initial_component_count
    operations, batches = [], []
    for time, (index, restore) in enumerate([(i,False) for i in failed] + [(i,True) for i in reversed(failed)]):
        start = len(operations)
        edge = links[index]
        pair = (edge['source'],edge['target'])
        before = counts[pair]
        if restore:
            active.add(index)
            counts[pair] += 1
        else:
            active.remove(index)
            counts[pair] -= 1
        if (before == 0) != (counts[pair] == 0):
            operations.append({'op': 'link' if restore else 'cut', 'source': pair[0], 'target': pair[1]})
        labels = components(len(ids), links, active)
        probes = [(0,len(ids)-1)]
        for _ in range(args.queries):
            source = rng.below(len(ids))
            target = rng.below(len(ids)-1)
            target += target >= source
            probes.append((source,target))
        for source,target in probes:
            operations.append({'op':'connected','source':source,'target':target,'expected':labels[source]==labels[target]})
        batches.append({'time':time,'start':start,'end':len(operations)})
    return {
        'schema_version':1, 'kind':'connectivity-import', 'workload':'topology-zoo-outages-v1',
        'node_ids':ids,
        'provenance': {field:getattr(args,field) for field in
                       ('source_url','source_revision','license','citation','retrieved_date')} | {'source_sha256':args.sha256.lower()},
        'transform': {'generator':'topology-zoo-outages-v1', 'seed':args.seed,
                      'prng':'lcg64-6364136223846793005-1442695040888963407-fisher-yates-modulo-v1',
                      'queries_per_batch':{'fixed':[[0,len(ids)-1]], 'seeded_distinct_pairs':args.queries},
                      'failures':args.failures, 'failure_order':[links[i]['id'] for i in failed],
                      'permutation':[links[i]['id'] for i in order], 'source_links':links,
                      'source_edge_records':records, 'discarded_self_loops':loops,
                      'parallel_links':len(links)-len(initial), 'discarded_records':0,
                      'initial_projected_bridges':bridges,
                      'initial_component_sizes':sorted(Counter(initial_components).values(), reverse=True),
                      'time_unit':'synthetic-source-event-index', 'node_selection':'all-source-nodes',
                      'oracle':'rebuild-union-find-from-active-source-links'},
        'batches':batches, 'trace':{'initial_edges':initial, 'operations':operations},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    for name in ('sha256','source-url','source-revision','retrieved-date','license','citation'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--failures', type=int, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--queries', type=int, default=8, help='seeded pairs per batch, in addition to fixed probe')
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        trace = build_trace(raw,args)
        serialized = json.dumps(trace, sort_keys=True, separators=(',',':'), ensure_ascii=False)+'\n'
        with args.output.open('x', encoding='utf-8') as output:
            output.write(serialized)
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, f'import_topology_zoo: {error}\n')


if __name__ == '__main__':
    main()
