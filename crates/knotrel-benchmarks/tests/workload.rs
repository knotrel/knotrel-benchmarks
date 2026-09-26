//! Independent correctness checks for benchmark workloads.

use knotrel_benchmarks::{Config, Operation, chain_workload};
use knotrel_core::Graph;

#[test]
fn known_chain_answers_hold_after_every_split_and_rejoin() {
    let config = Config {
        nodes: 9,
        rounds: 20,
        seed: 42,
    };
    let workload = chain_workload(config).unwrap();
    assert_eq!(
        workload.initial_edges,
        vec![
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 8)
        ]
    );
    assert_eq!(workload.operations.len(), 80);
    let mut graph = Graph::new();
    for (a, b) in workload.initial_edges {
        graph.link(a, b).unwrap();
    }
    for (index, operation) in workload.operations.into_iter().enumerate() {
        match operation {
            Operation::Cut { source, target } => assert_eq!(graph.cut(source, target), Ok(true)),
            Operation::Link { source, target } => assert_eq!(graph.link(source, target), Ok(true)),
            Operation::Connected {
                source,
                target,
                expected,
            } => {
                assert_eq!(expected, index % 4 == 3);
                assert_eq!((source, target), (0, 8));
                assert_eq!(graph.connected(source, target), Ok(expected));
            }
        }
    }
    assert_eq!((graph.node_count(), graph.edge_count()), (9, 8));
}

#[test]
fn seeds_reproduce_the_same_trace() {
    let config = Config {
        nodes: 50,
        rounds: 100,
        seed: 9,
    };
    let first = chain_workload(config).unwrap();
    assert_eq!(first, chain_workload(config).unwrap());
    assert_ne!(
        first,
        chain_workload(Config { seed: 10, ..config }).unwrap()
    );
}

#[test]
fn invalid_sizes_fail_before_allocation() {
    for config in [
        Config {
            nodes: 0,
            rounds: 1,
            seed: 0,
        },
        Config {
            nodes: 1,
            rounds: 1,
            seed: 0,
        },
        Config {
            nodes: 2,
            rounds: 0,
            seed: 0,
        },
        Config {
            nodes: 2,
            rounds: usize::MAX,
            seed: 0,
        },
        Config {
            nodes: u64::MAX,
            rounds: 1,
            seed: 0,
        },
    ] {
        assert!(chain_workload(config).is_err());
    }
    let minimal = chain_workload(Config {
        nodes: 2,
        rounds: 1,
        seed: 0,
    })
    .unwrap();
    assert_eq!(minimal.initial_edges, vec![(0, 1)]);
    assert_eq!(
        minimal.operations,
        vec![
            Operation::Cut {
                source: 0,
                target: 1
            },
            Operation::Connected {
                source: 0,
                target: 1,
                expected: false
            },
            Operation::Link {
                source: 0,
                target: 1
            },
            Operation::Connected {
                source: 0,
                target: 1,
                expected: true
            },
        ]
    );
}
