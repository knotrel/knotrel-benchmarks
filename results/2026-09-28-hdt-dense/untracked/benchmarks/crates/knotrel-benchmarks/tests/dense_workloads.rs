//! Dense bridge churn checked against an independent transitive closure.

use knotrel_benchmarks::{Config, Operation, WorkloadKind, generate, generate_with_query_percent};

const NAMES: [&str; 2] = ["dense-bridge-churn-v1", "redundant-bridge-churn-v1"];

#[test]
fn dense_bridge_traces_preserve_cliques_and_match_closure() {
    for (family, name) in NAMES.into_iter().enumerate() {
        let kind = WorkloadKind::parse(name).expect("dense workload selector");
        assert!(kind.is_sustained());
        for nodes in [4, 5, 8, 9] {
            for seed in [0, 42, u64::MAX] {
                for percent in [1, 10, 50, 90, 99] {
                    let config = Config {
                        nodes,
                        rounds: 3,
                        seed,
                    };
                    let trace = generate_with_query_percent(kind, config, percent).unwrap();
                    assert_eq!(
                        trace,
                        generate_with_query_percent(kind, config, percent).unwrap()
                    );
                    if percent == 50 {
                        assert_eq!(trace, generate(kind, config).unwrap());
                    }
                    let prefix = generate_with_query_percent(
                        kind,
                        Config {
                            rounds: 1,
                            ..config
                        },
                        percent,
                    )
                    .unwrap();
                    assert_eq!(prefix.operations, trace.operations[..100]);
                    assert_eq!(trace.operations.len(), 300);
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
                    let split = n / 2;
                    let mut adjacency = vec![vec![false; n]; n];
                    let mut bridges = Vec::new();
                    for &(source, target) in &trace.initial_edges {
                        let (a, b) = (source as usize, target as usize);
                        assert!(a < n && b < n && a != b && !adjacency[a][b]);
                        adjacency[a][b] = true;
                        adjacency[b][a] = true;
                        if (a < split) != (b < split) {
                            bridges.push((source, target));
                        } else {
                            assert!(bridges.is_empty(), "internal edges precede bridges");
                        }
                    }
                    assert_eq!(bridges.len(), family + 1);
                    for (a, row) in adjacency.iter().enumerate() {
                        for (b, &present) in row.iter().enumerate() {
                            if a != b && (a < split) == (b < split) {
                                assert!(present, "both components are cliques");
                            }
                        }
                    }
                    let mut bridge_toggles = vec![0; bridges.len()];
                    for op in &trace.operations {
                        match *op {
                            Operation::Link { source, target }
                            | Operation::Cut { source, target } => {
                                let index = bridges
                                    .iter()
                                    .position(|&edge| edge == (source, target))
                                    .expect("only initial bridges change");
                                bridge_toggles[index] += 1;
                                let insert = matches!(op, Operation::Link { .. });
                                let (a, b) = (source as usize, target as usize);
                                assert_ne!(
                                    adjacency[a][b], insert,
                                    "updates must change state across rounds"
                                );
                                adjacency[a][b] = insert;
                                adjacency[b][a] = insert;
                            }
                            Operation::Connected {
                                source,
                                target,
                                expected,
                            } => {
                                let mut reach = adjacency.clone();
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
                                assert_eq!(
                                    reach[source as usize][target as usize], expected,
                                    "{name} n={nodes} seed={seed} q={percent}"
                                );
                            }
                        }
                    }
                    if percent <= 90 {
                        assert!(bridge_toggles.iter().all(|&count| count > 0));
                    }
                }
            }
        }
    }
}

#[test]
fn dense_bridge_seeds_change_queries_and_invalid_bounds_fail() {
    for name in NAMES {
        let kind = WorkloadKind::parse(name).expect("dense workload selector");
        let config = Config {
            nodes: 8,
            rounds: 3,
            seed: 42,
        };
        assert_ne!(
            generate(kind, config).unwrap(),
            generate(kind, Config { seed: 43, ..config }).unwrap()
        );
        for nodes in [0, 1, 2, 3, u64::MAX] {
            assert!(generate(kind, Config { nodes, ..config }).is_err());
        }
        for rounds in [0, usize::MAX] {
            assert!(generate(kind, Config { rounds, ..config }).is_err());
        }
        for percent in [0, 100, u8::MAX] {
            assert!(generate_with_query_percent(kind, config, percent).is_err());
        }
    }
}
