"""Behavioral checks using original synthetic GraphML, not third-party data."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'import_topology_zoo.py'
GRAPH = '''<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph edgedefault="undirected">
<node id="z"/><node id="A"/><node id="isolated"/>
<edge id="one" source="A" target="z"/><edge id="two" source="z" target="A"/>
<edge id="loop" source="A" target="A"/>
</graph></graphml>'''

class TopologyImportTests(unittest.TestCase):
    def invoke(self, directory, graph=GRAPH, extra=(), name='trace.json'):
        source = Path(directory) / 'input.graphml'
        source.write_text(graph)
        output = Path(directory) / name
        command = ['python3', str(SCRIPT), str(source), '--output', str(output),
                   '--sha256', hashlib.sha256(source.read_bytes()).hexdigest(),
                   '--source-url', 'https://example.org/fixture.graphml',
                   '--source-revision', 'fixture-v1', '--retrieved-date', '2026-10-03',
                   '--license', 'CC0-1.0', '--citation', 'Original test fixture',
                   '--failures', '2', '--seed', '42', '--queries', '3', *extra]
        return subprocess.run(command, capture_output=True, text=True), output

    def test_parallel_edges_isolates_and_expected_query_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            result, output = self.invoke(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            trace = json.loads(output.read_text())
            self.assertEqual(trace['node_ids'], ['A', 'isolated', 'z'])
            self.assertEqual(trace['trace']['initial_edges'], [[0, 2]])
            self.assertEqual(trace['transform']['discarded_self_loops'], 1)
            self.assertEqual(len(trace['batches']), 4)
            ops = trace['trace']['operations']
            self.assertEqual([op['op'] for op in ops if op['op'] != 'connected'], ['cut','link'])
            # Independent expected states by count of physical links remaining.
            # One failure keeps A-z connected, two split it; first restoration reconnects.
            for batch, connected in zip(trace['batches'], [True,False,True,True]):
                queries = [op for op in ops[batch['start']:batch['end']] if op['op']=='connected']
                self.assertEqual(len(queries), 4)
                for op in queries:
                    expected = connected and {op['source'],op['target']} == {0,2}
                    self.assertEqual(op['expected'], expected)
            again, second = self.invoke(directory, name='second.json')
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(output.read_bytes(), second.read_bytes())

    def test_rejects_semantic_loss_and_bad_metadata_without_output(self):
        invalid = [GRAPH.replace('<node id="z"/>','<data key="hidden"><node id="hidden"/></data><node id="z"/>'),
                   GRAPH.replace('undirected','directed'),
                   GRAPH.replace('source="A" target="z"','source="missing" target="z"'),
                   GRAPH.replace('<node id="z"/>','<node id="z"/><node id="z"/>'),
                   GRAPH.replace('<edge id="one"','<edge directed="true" id="one"'),
                   GRAPH.replace('<node id="z"/>','<node id="z"><graph edgedefault="undirected"/></node>'),
                   GRAPH.replace('</graph>','<hyperedge id="h"/></graph>'),
                   GRAPH.replace('<edge id="one"','<edge sourceport="p" id="one"'),
                   '<!DOCTYPE graphml [<!ENTITY x "foo">]>'+GRAPH]
        for graph in invalid:
            with self.subTest(graph=graph), tempfile.TemporaryDirectory() as directory:
                result, output = self.invoke(directory, graph)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
        for extra in [('--sha256','0'*64),('--failures','3'),('--queries','-1'),('--seed','-1')]:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                result, output = self.invoke(directory, extra=extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_multihop_cycle_bridge_and_isolate_all_pairs(self):
        # Original source fixture: triangle A-B-C, bridge C-D, isolate E.
        edges = [('A','B'),('B','C'),('C','A'),('C','D')]
        graph = '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph edgedefault="undirected">'
        graph += ''.join(f'<node id="{node}"/>' for node in 'ABCDE')
        graph += ''.join(f'<edge id="e{i}" source="{a}" target="{b}"/>' for i,(a,b) in enumerate(edges))
        graph += '</graph></graphml>'
        def reach(pairs, start, end):
            seen, pending = {start}, [start]
            while pending:
                node = pending.pop()
                for a,b in pairs:
                    neighbor = b if a == node else a if b == node else None
                    if neighbor is not None and neighbor not in seen:
                        seen.add(neighbor)
                        pending.append(neighbor)
            return end in seen
        for seed in ('0','42','18446744073709551615'):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as directory:
                result, output = self.invoke(directory,graph,('--failures','4','--seed',seed))
                self.assertEqual(result.returncode,0,result.stderr)
                data=json.loads(output.read_text())
                self.assertEqual(data['transform']['initial_projected_bridges'],1)
                self.assertEqual(data['transform']['initial_component_sizes'],[4,1])
                active=set(range(4))
                order=[int(key.removeprefix('id:e')) for key in data['transform']['failure_order']]
                schedule=[(i,False) for i in order]+[(i,True) for i in reversed(order)]
                projected={tuple(pair) for pair in data['trace']['initial_edges']}
                for batch,(index,restore) in zip(data['batches'],schedule):
                    active.add(index) if restore else active.remove(index)
                    source_pairs=[edges[i] for i in active]
                    for op in data['trace']['operations'][batch['start']:batch['end']]:
                        pair=(op['source'],op['target'])
                        if op['op']=='cut': projected.remove(pair)
                        elif op['op']=='link':
                            self.assertNotIn(pair,projected)
                            projected.add(pair)
                        else:
                            self.assertEqual(op['expected'],reach(source_pairs,'ABCDE'[pair[0]],'ABCDE'[pair[1]]))
                    for a in range(5):
                        for b in range(5):
                            self.assertEqual(reach(projected,a,b),reach(source_pairs,'ABCDE'[a],'ABCDE'[b]))

    def test_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'trace.json'
            target.write_text('keep me')
            result, _ = self.invoke(directory)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(target.read_text(),'keep me')

if __name__ == '__main__':
    unittest.main()
