//! Word boundaries, scratch reuse and graph growth must preserve exact BFS work.
use knotrel_benchmarks::traversal::{BitSearchSpace, Graph, SearchSpace};

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
