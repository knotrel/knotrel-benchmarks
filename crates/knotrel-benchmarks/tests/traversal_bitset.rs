//! Word boundaries, scratch reuse and graph growth must preserve exact BFS work.
use knotrel_benchmarks::traversal::{BitSearchSpace, DequeSearchSpace, Graph, SearchSpace};

#[test]
fn bitset_matches_epochs_after_growth_cuts_and_early_exits() {
    let mut graph = Graph::new();
    let (mut epoch, mut bits) = (SearchSpace::default(), BitSearchSpace::default());
    graph.link(0, 1).unwrap();
    assert!(graph.search_bits::<true>(0, 1, &mut bits).unwrap());
    for i in 1..130 {
        graph.link(i, i + 1).unwrap();
    }
    for (a, b) in [(0, 130), (63, 64), (64, 129), (130, 0), (65, 65)] {
        assert_eq!(
            graph.search::<false, true>(a, b, &mut epoch),
            graph.search_bits::<true>(a, b, &mut bits)
        );
        assert_eq!(epoch.stats(), bits.stats());
    }
    graph.cut(63, 64).unwrap();
    for (a, b) in [(0, 130), (0, 1), (64, 130), (0, 130)] {
        assert_eq!(
            graph.search::<false, true>(a, b, &mut epoch),
            graph.search_bits::<true>(a, b, &mut bits)
        );
        assert_eq!(epoch.stats(), bits.stats());
    }
    let mut other = Graph::new();
    other.add_node(100);
    other.add_node(200);
    assert!(!other.search_bits::<true>(100, 200, &mut bits).unwrap());
    other.link(100, 200).unwrap();
    assert!(other.search_bits::<true>(100, 200, &mut bits).unwrap());
}

#[test]
fn scratch_ledger_distinguishes_fresh_marks_reuse_and_queue_history() {
    const NODE_COUNT: usize = 131;
    let mut graph = Graph::new();
    for node in 1..NODE_COUNT as u64 {
        graph.link(node - 1, node).unwrap();
    }
    let (mut epoch, mut bits) = (SearchSpace::default(), BitSearchSpace::default());
    let target = NODE_COUNT as u64 - 1;
    assert!(graph.search::<false, true>(0, target, &mut epoch).unwrap());
    assert!(graph.search_bits::<true>(0, target, &mut bits).unwrap());
    assert_eq!(epoch.stats(), bits.stats());
    assert_eq!(epoch.stats().peak_frontier, 1);
    assert_eq!(epoch.stats().peak_buffer_len, NODE_COUNT - 1);
    let initial_epoch = epoch.scratch_stats();
    let initial_bits = bits.scratch_stats();
    assert_eq!(initial_epoch.mark_initialized_elements, NODE_COUNT);
    assert_eq!(initial_epoch.mark_cleared_elements, 0);
    assert_eq!(
        initial_bits.mark_initialized_elements,
        NODE_COUNT.div_ceil(u64::BITS as usize)
    );
    assert_eq!(
        initial_bits.mark_cleared_elements,
        initial_bits.mark_initialized_elements
    );
    assert!(initial_epoch.queue_growth_events > 0);
    assert_eq!(
        initial_epoch.queue_capacity_bytes,
        initial_epoch.queue_capacity_increase_bytes
    );
    assert_eq!(
        initial_epoch.queue_capacity_bytes,
        initial_bits.queue_capacity_bytes
    );
    assert!(initial_epoch.queue_capacity_bytes >= (NODE_COUNT - 1) * size_of::<usize>());
    assert!(graph.search::<false, true>(0, target, &mut epoch).unwrap());
    assert!(graph.search_bits::<true>(0, target, &mut bits).unwrap());
    let reused_epoch = epoch.scratch_stats();
    let reused_bits = bits.scratch_stats();
    assert_eq!(reused_epoch.mark_initialized_elements, 0);
    assert_eq!(reused_epoch.mark_cleared_elements, 0);
    assert_eq!(reused_bits.mark_initialized_elements, 0);
    assert_eq!(
        reused_bits.mark_cleared_elements,
        NODE_COUNT.div_ceil(u64::BITS as usize)
    );
    assert_eq!(reused_epoch.queue_growth_events, 0);
    assert_eq!(reused_bits.queue_growth_events, 0);
    assert_eq!(reused_epoch.queue_capacity_increase_bytes, 0);
    assert_eq!(
        reused_epoch.queue_capacity_bytes,
        initial_epoch.queue_capacity_bytes
    );
    assert_eq!(
        reused_bits.queue_capacity_bytes,
        initial_bits.queue_capacity_bytes
    );
    assert!(graph.search::<false, false>(0, target, &mut epoch).unwrap());
    assert!(graph.search_bits::<false>(0, target, &mut bits).unwrap());
    assert_eq!(epoch.scratch_stats(), reused_epoch);
    assert_eq!(bits.scratch_stats(), reused_bits);
    assert_eq!(epoch.stats(), Default::default());
    assert_eq!(bits.stats(), Default::default());
}

#[test]
fn wide_frontier_and_query_shortcuts_preserve_scratch_accounting() {
    let mut graph = Graph::new();
    for leaf in 1..=5 {
        graph.link(0, leaf).unwrap();
    }
    let (mut epoch, mut bits) = (SearchSpace::default(), BitSearchSpace::default());
    assert!(graph.search::<false, true>(0, 5, &mut epoch).unwrap());
    assert!(graph.search_bits::<true>(0, 5, &mut bits).unwrap());
    assert_eq!(epoch.stats(), bits.stats());
    assert_eq!(epoch.stats().peak_frontier, 4);
    assert_eq!(epoch.stats().peak_buffer_len, 5);
    assert!(graph.search::<false, true>(0, 0, &mut epoch).unwrap());
    assert!(graph.search_bits::<true>(0, 0, &mut bits).unwrap());
    assert_eq!(epoch.scratch_stats().mark_initialized_elements, 0);
    assert_eq!(bits.scratch_stats().mark_cleared_elements, 0);
    assert_eq!(epoch.scratch_stats().queue_growth_events, 0);
    assert_eq!(bits.scratch_stats().queue_capacity_increase_bytes, 0);
    assert!(graph.search::<false, true>(99, 100, &mut epoch).is_err());
    assert!(graph.search_bits::<true>(99, 100, &mut bits).is_err());
    assert_eq!(epoch.stats(), bits.stats());
    assert_eq!(epoch.scratch_stats().mark_cleared_elements, 0);
    assert_eq!(bits.scratch_stats().queue_growth_events, 0);
}

#[test]
fn fifo_matches_answers_order_marks_and_counts_on_topologies_and_growth() {
    const IDS: [u64; 8] = [0, u64::MAX, 1, 1 << 63, 64, 128, u64::MAX - 1, 777];
    let mut graph = Graph::new();
    let mut production = knotrel_core::Graph::new();
    let mut reference = knotrel_core::ReferenceGraph::new();
    let mut baseline = BitSearchSpace::with_order_recording();
    let mut fifo = DequeSearchSpace::with_order_recording();
    let verify = |graph: &Graph,
                  production: &knotrel_core::Graph,
                  reference: &knotrel_core::ReferenceGraph,
                  baseline: &mut BitSearchSpace,
                  fifo: &mut DequeSearchSpace| {
        for source in IDS.into_iter().chain([9999, 9998]) {
            for target in IDS.into_iter().chain([9999, 9998]) {
                let expected = production.connected(source, target);
                assert_eq!(reference.connected(source, target), expected);
                assert_eq!(graph.connected_fresh_packed_vec(source, target), expected);
                assert_eq!(graph.connected_fresh_packed_deque(source, target), expected);
                assert_eq!(
                    graph.search_bits::<true>(source, target, baseline),
                    expected
                );
                assert_eq!(graph.search_deque::<true>(source, target, fifo), expected);
                assert_eq!(baseline.recorded_order(), fifo.recorded_order());
                assert_eq!(
                    baseline.stats().expanded_vertices,
                    fifo.stats().expanded_vertices
                );
                assert_eq!(baseline.stats().examined_arcs, fifo.stats().examined_arcs);
                assert_eq!(baseline.stats().peak_frontier, fifo.stats().peak_frontier);
                assert_eq!(baseline.queue_stats().enqueues, fifo.queue_stats().enqueues);
                assert_eq!(
                    baseline.scratch_stats().mark_initialized_elements,
                    fifo.scratch_stats().mark_initialized_elements
                );
                assert_eq!(
                    baseline.scratch_stats().mark_cleared_elements,
                    fifo.scratch_stats().mark_cleared_elements
                );
                assert_eq!(
                    baseline.scratch_stats().mark_capacity_bytes,
                    fifo.scratch_stats().mark_capacity_bytes
                );
                assert_eq!(
                    graph.search_bits::<false>(source, target, baseline),
                    expected
                );
                assert_eq!(graph.search_deque::<false>(source, target, fifo), expected);
            }
        }
        assert_eq!(production.node_count(), reference.node_count());
        assert_eq!(production.edge_count(), reference.edge_count());
    };
    verify(&graph, &production, &reference, &mut baseline, &mut fifo);
    for node in IDS {
        assert_eq!(graph.add_node(node), production.add_node(node));
        assert!(reference.add_node(node));
    }
    for edges in [
        vec![(0, 1), (1, 2), (2, 3), (3, 4)],
        vec![(4, 0), (0, 2), (0, 3), (0, 5), (0, 6)],
        vec![(6, 7)],
    ] {
        for (source_index, target_index) in edges {
            let (source, target) = (IDS[source_index], IDS[target_index]);
            assert_eq!(graph.link(source, target), production.link(source, target));
            assert_eq!(reference.link(source, target), Ok(true));
            verify(&graph, &production, &reference, &mut baseline, &mut fifo);
            assert_eq!(graph.link(target, source), production.link(target, source));
            assert_eq!(reference.link(target, source), Ok(false));
            assert_eq!(graph.cut(target, source), production.cut(target, source));
            assert_eq!(reference.cut(target, source), Ok(true));
            assert_eq!(graph.cut(source, target), production.cut(source, target));
            assert_eq!(reference.cut(source, target), Ok(false));
            verify(&graph, &production, &reference, &mut baseline, &mut fifo);
            assert_eq!(graph.link(target, source), production.link(target, source));
            assert_eq!(reference.link(target, source), Ok(true));
        }
    }
    for node in 100..240 {
        let inserted = production.add_node(node);
        assert_eq!(graph.add_node(node), inserted);
        assert_eq!(reference.add_node(node), inserted);
    }
    verify(&graph, &production, &reference, &mut baseline, &mut fifo);
}

#[test]
fn fresh_fifo_path_and_star_preserve_order_without_retaining_history() {
    for edges in [
        vec![(0, 1), (1, 2), (2, 3), (3, 4)],
        vec![(0, 1), (0, 2), (0, 3), (0, 4)],
    ] {
        let mut graph = Graph::new();
        for (source, target) in edges {
            graph.link(source, target).unwrap();
        }
        for target in [1, 4, 0] {
            let mut baseline = BitSearchSpace::with_order_recording();
            let mut fifo = DequeSearchSpace::with_order_recording();
            assert_eq!(
                graph.search_bits::<true>(0, target, &mut baseline),
                graph.search_deque::<true>(0, target, &mut fifo)
            );
            assert_eq!(baseline.recorded_order(), fifo.recorded_order());
            if target == 1 {
                let order = fifo.recorded_order().unwrap();
                assert_eq!(order.expanded, vec![0]);
                assert_eq!(order.examined, vec![(0, 1)]);
                assert_eq!(fifo.queue_stats().enqueues, 1);
            }
            assert_eq!(baseline.queue_stats().enqueues, fifo.queue_stats().enqueues);
            assert_eq!(fifo.stats().peak_buffer_len, fifo.stats().peak_frontier);
            assert!(fifo.stats().peak_buffer_len <= baseline.stats().peak_buffer_len);
            assert_eq!(
                fifo.queue_stats().peak_capacity_bytes,
                fifo.queue_stats().final_capacity_bytes
            );
        }
    }
}
