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

#[test]
fn all_families_are_reproducible_and_reject_unaddressable_sizes() {
    use knotrel_benchmarks::{WorkloadKind, generate};
    for kind in [
        WorkloadKind::Chain,
        WorkloadKind::Cycle,
        WorkloadKind::Components,
        WorkloadKind::Hub,
    ] {
        let config = Config {
            nodes: 32,
            rounds: 30,
            seed: 42,
        };
        let first = generate(kind, config).unwrap();
        assert_eq!(first, generate(kind, config).unwrap());
        assert_ne!(
            first,
            generate(kind, Config { seed: 43, ..config }).unwrap()
        );
        for invalid in [
            Config {
                nodes: u64::MAX,
                ..config
            },
            Config {
                rounds: usize::MAX,
                ..config
            },
            Config {
                rounds: 0,
                ..config
            },
        ] {
            assert!(generate(kind, invalid).is_err());
        }
    }
}

#[test]
fn sustained_traces_match_independent_matrix_oracle_and_exact_ratios() {
    use knotrel_benchmarks::{WorkloadKind, generate_with_query_percent};
    for kind in [WorkloadKind::SustainedPath, WorkloadKind::SustainedBlocks] {
        for nodes in [2, 3, 16, 17, 19, 33] {
            for percent in [1, 10, 50, 90, 99] {
                let config = Config {
                    nodes,
                    rounds: 4,
                    seed: 42,
                };
                let trace = generate_with_query_percent(kind, config, percent).unwrap();
                assert_eq!(
                    trace,
                    generate_with_query_percent(kind, config, percent).unwrap()
                );
                assert_eq!(trace.operations.len(), 400);
                for round in trace.operations.as_chunks::<100>().0 {
                    assert_eq!(
                        round
                            .iter()
                            .filter(|op| matches!(op, Operation::Connected { .. }))
                            .count(),
                        usize::from(percent)
                    );
                }
                let n = nodes as usize;
                let mut adjacency = vec![vec![false; n]; n];
                for &(a, b) in &trace.initial_edges {
                    assert!(a != b && !adjacency[a as usize][b as usize]);
                    adjacency[a as usize][b as usize] = true;
                    adjacency[b as usize][a as usize] = true;
                }
                let initial = adjacency.clone();
                let mut changed_at_boundary = false;
                let mut reach = Vec::new();
                let mut dirty = true;
                for (index, op) in trace.operations.iter().enumerate() {
                    match *op {
                        Operation::Link { source, target } | Operation::Cut { source, target } => {
                            let insert = matches!(op, Operation::Link { .. });
                            assert_ne!(adjacency[source as usize][target as usize], insert);
                            adjacency[source as usize][target as usize] = insert;
                            adjacency[target as usize][source as usize] = insert;
                            dirty = true;
                        }
                        Operation::Connected {
                            source,
                            target,
                            expected,
                        } => {
                            if dirty {
                                reach = adjacency.clone();
                                for (i, row) in reach.iter_mut().enumerate() {
                                    row[i] = true;
                                }
                                for k in 0..n {
                                    for i in 0..n {
                                        for j in 0..n {
                                            reach[i][j] |= reach[i][k] && reach[k][j];
                                        }
                                    }
                                }
                                dirty = false;
                            }
                            assert_eq!(
                                reach[source as usize][target as usize], expected,
                                "{kind:?} n={nodes} q={percent} op={index}"
                            );
                        }
                    }
                    if (index + 1) % 100 == 0 && adjacency != initial {
                        changed_at_boundary = true;
                    }
                }
                // With larger graphs, state survives round boundaries.
                if nodes >= 33 {
                    assert!(changed_at_boundary);
                }
            }
        }
        for percent in [0, 100] {
            assert!(
                generate_with_query_percent(
                    kind,
                    Config {
                        nodes: 16,
                        rounds: 1,
                        seed: 0
                    },
                    percent
                )
                .is_err()
            );
        }
        assert!(
            generate_with_query_percent(
                kind,
                Config {
                    nodes: 16,
                    rounds: usize::MAX,
                    seed: 0
                },
                50
            )
            .is_err()
        );
    }
}
