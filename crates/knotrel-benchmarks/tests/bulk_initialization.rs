//! Bulk versus incremental facade initialization: observable equivalence.
//!
//! Correctness only; nothing here times or compares performance. The incremental
//! reference is deliberately a separate ordered loop, independent of the API under test.

use knotrel_benchmarks::{Config, Operation, WorkloadKind, generate_with_query_percent};
use knotrel_core::{ConnectivityGraph, EngineConfig, GraphError, GraphLimits, NodeId};
use serde_json::Value;
use std::process::{Command, Output};

const ENGINES: [EngineConfig; 3] = [
    EngineConfig::CompactBfs,
    EngineConfig::EulerTour,
    EngineConfig::Hdt,
];
const KINDS: [WorkloadKind; 8] = [
    WorkloadKind::Chain,
    WorkloadKind::Cycle,
    WorkloadKind::Components,
    WorkloadKind::Hub,
    WorkloadKind::SustainedPath,
    WorkloadKind::SustainedBlocks,
    WorkloadKind::DenseBridge,
    WorkloadKind::RedundantBridge,
];

fn incremental(
    engine: EngineConfig,
    limits: GraphLimits,
    nodes: &[NodeId],
    edges: &[(NodeId, NodeId)],
) -> Result<ConnectivityGraph, GraphError> {
    let mut graph = ConnectivityGraph::with_limits(engine, limits);
    for &node in nodes {
        graph.add_node(node)?;
    }
    for &(a, b) in edges {
        graph.link(a, b)?;
    }
    Ok(graph)
}

fn same_state(bulk: &ConnectivityGraph, sequential: &ConnectivityGraph, ids: &[NodeId]) {
    assert_eq!(bulk.engine(), sequential.engine());
    assert_eq!(bulk.limits(), sequential.limits());
    assert_eq!(bulk.node_count(), sequential.node_count());
    assert_eq!(bulk.edge_count(), sequential.edge_count());
    for &x in ids {
        for &y in ids {
            assert_eq!(bulk.connected(x, y), sequential.connected(x, y), "{x},{y}");
        }
    }
}

/// Builds both ways, requires identical outcomes, and returns the shared error.
fn compare_construction(
    engine: EngineConfig,
    limits: GraphLimits,
    nodes: &[NodeId],
    edges: &[(NodeId, NodeId)],
) -> Option<GraphError> {
    let bulk = ConnectivityGraph::try_from_edges(engine, limits, nodes, edges);
    let sequential = incremental(engine, limits, nodes, edges);
    match (bulk, sequential) {
        (Err(a), Err(b)) => {
            assert_eq!(a, b, "{engine:?} {limits:?}");
            Some(a)
        }
        (Ok(mut bulk), Ok(mut sequential)) => {
            let mut ids: Vec<_> = nodes
                .iter()
                .copied()
                .chain(edges.iter().flat_map(|&(a, b)| [a, b]))
                .collect();
            ids.extend([0, 1, 2, 3, 9, 50, u64::MAX]);
            ids.sort_unstable();
            ids.dedup();
            same_state(&bulk, &sequential, &ids);
            // Identical continuation: growth, duplicates, self-loops, absent cuts,
            // limit pressure and removal of every input edge.
            let mut steps: Vec<(u8, u64, u64)> = vec![
                (0, 50, 50),
                (0, 50, 50),
                (1, 1, 1),
                (2, 7, 8),
                (1, 0, 1),
                (1, 1, 0),
                (1, 2, 50),
                (2, 0, 1),
                (1, 9, 50),
                (2, 50, 9),
            ];
            steps.extend(
                edges
                    .iter()
                    .flat_map(|&(a, b)| [(2, a, b), (2, a, b), (1, a, b)]),
            );
            for (kind, a, b) in steps {
                match kind {
                    0 => assert_eq!(bulk.add_node(a), sequential.add_node(a)),
                    1 => assert_eq!(bulk.link(a, b), sequential.link(a, b)),
                    _ => assert_eq!(bulk.cut(a, b), sequential.cut(a, b)),
                }
                same_state(&bulk, &sequential, &ids);
            }
            None
        }
        (bulk, sequential) => panic!(
            "outcomes differ for {engine:?} {limits:?}: bulk={:?} incremental={:?}",
            bulk.err(),
            sequential.err()
        ),
    }
}

#[test]
fn workload_graphs_and_dynamic_continuations_match_across_modes() {
    for kind in KINDS {
        let config = Config {
            nodes: 24,
            rounds: 2,
            seed: 7,
        };
        let workload = generate_with_query_percent(kind, config, 50).unwrap();
        let nodes: Vec<_> = (0..config.nodes).collect();
        for engine in ENGINES {
            let limits = GraphLimits::default();
            let mut bulk =
                ConnectivityGraph::try_from_edges(engine, limits, &nodes, &workload.initial_edges)
                    .unwrap();
            let mut sequential =
                incremental(engine, limits, &nodes, &workload.initial_edges).unwrap();
            assert_eq!(bulk.edge_count(), workload.initial_edges.len());
            same_state(&bulk, &sequential, &nodes);
            for (step, &op) in workload.operations.iter().enumerate() {
                match op {
                    Operation::Link { source, target } => {
                        let result = bulk.link(source, target);
                        assert_eq!(result, sequential.link(source, target));
                        assert_eq!(result, Ok(true), "{} step {step}", kind.name());
                    }
                    Operation::Cut { source, target } => {
                        let result = bulk.cut(source, target);
                        assert_eq!(result, sequential.cut(source, target));
                        assert_eq!(result, Ok(true), "{} step {step}", kind.name());
                    }
                    Operation::Connected {
                        source,
                        target,
                        expected,
                    } => {
                        let result = bulk.connected(source, target);
                        assert_eq!(result, sequential.connected(source, target));
                        assert_eq!(result, Ok(expected), "{} step {step}", kind.name());
                    }
                }
                assert_eq!(bulk.node_count(), sequential.node_count());
                assert_eq!(bulk.edge_count(), sequential.edge_count());
                if step % 25 == 0 {
                    same_state(&bulk, &sequential, &nodes);
                }
            }
            same_state(&bulk, &sequential, &nodes);
        }
    }
}

#[test]
fn degenerate_duplicate_and_self_loop_inputs_match_across_modes() {
    use GraphError::SelfLoop;
    let max = u64::MAX;
    let no_limits = GraphLimits::default();
    for engine in ENGINES {
        // Successful inputs: empty, isolated-only, implicit endpoints, duplicates,
        // reversed repeats, sparse IDs, disconnected components and cycles.
        for (nodes, edges) in [
            (&[][..], &[][..]),
            (&[0, 1, 2][..], &[][..]),
            (&[2, 2, 2][..], &[][..]),
            (&[][..], &[(5, 6), (6, 7)][..]),
            (&[0, 1][..], &[(1, 9)][..]),
            (&[0, 1, 2, 3][..], &[(0, 1), (1, 0), (0, 1), (1, 2)][..]),
            (&[3, 2, 1, 0][..], &[(0, 1), (2, 3)][..]),
            (&[][..], &[(0, max), (max, 1 << 63), (1 << 63, 0)][..]),
            (&[0, 1, 2][..], &[(0, 1), (1, 2), (2, 0), (0, 2)][..]),
        ] {
            assert_eq!(compare_construction(engine, no_limits, nodes, edges), None);
        }
        // Self-loops report the first offending edge and never reach later input.
        for (edges, node) in [
            (&[(4, 4)][..], 4),
            (&[(0, 1), (2, 2), (3, 3)][..], 2),
            (&[(0, 1), (1, 2), (max, max)][..], max),
        ] {
            assert_eq!(
                compare_construction(engine, no_limits, &[0, 1], edges),
                Some(SelfLoop { node })
            );
        }
    }
}

#[test]
fn node_and_edge_limit_failures_match_across_modes() {
    use GraphError::{EdgeLimitExceeded, NodeLimitExceeded, SelfLoop};
    for kind in [
        WorkloadKind::Chain,
        WorkloadKind::Cycle,
        WorkloadKind::DenseBridge,
        WorkloadKind::Components,
    ] {
        let config = Config {
            nodes: 8,
            rounds: 1,
            seed: 3,
        };
        let workload = generate_with_query_percent(kind, config, 50).unwrap();
        let nodes: Vec<_> = (0..config.nodes).collect();
        let (n, e) = (nodes.len(), workload.initial_edges.len());
        for engine in ENGINES {
            let limits = |max_nodes, max_edges| GraphLimits {
                max_nodes,
                max_edges,
            };
            let check = |limits, nodes: &[u64], edges: &[(u64, u64)]| {
                compare_construction(engine, limits, nodes, edges)
            };
            // Exactly full succeeds; one short fails with that limit.
            assert_eq!(
                check(limits(Some(n), Some(e)), &nodes, &workload.initial_edges),
                None
            );
            assert_eq!(
                check(limits(Some(n - 1), None), &nodes, &workload.initial_edges),
                Some(NodeLimitExceeded { limit: n - 1 })
            );
            assert_eq!(
                check(limits(None, Some(e - 1)), &nodes, &workload.initial_edges),
                Some(EdgeLimitExceeded { limit: e - 1 })
            );
            // Nodes are registered before any edge, so the node error wins.
            assert_eq!(
                check(
                    limits(Some(n - 1), Some(e - 1)),
                    &nodes,
                    &workload.initial_edges
                ),
                Some(NodeLimitExceeded { limit: n - 1 })
            );
            // Zero limits remain meaningful.
            assert_eq!(
                check(limits(Some(0), None), &nodes, &[]),
                Some(NodeLimitExceeded { limit: 0 })
            );
            assert_eq!(
                check(limits(None, Some(0)), &[], &workload.initial_edges),
                Some(EdgeLimitExceeded { limit: 0 })
            );
            // Implicit endpoints count toward the node limit when first reached.
            assert_eq!(
                check(
                    limits(Some(n / 2), None),
                    &nodes[..n / 2],
                    &workload.initial_edges
                ),
                Some(NodeLimitExceeded { limit: n / 2 })
            );
            // Duplicates succeed at capacity; a later self-loop is still reached.
            let mut repeated = workload.initial_edges.clone();
            repeated.extend(workload.initial_edges.iter().map(|&(a, b)| (b, a)));
            assert_eq!(check(limits(Some(n), Some(e)), &nodes, &repeated), None);
            repeated.push((2, 2));
            assert_eq!(
                check(limits(Some(n), Some(e)), &nodes, &repeated),
                Some(SelfLoop { node: 2 })
            );
            // An edge-limit failure precedes a later self-loop.
            let mut short = workload.initial_edges.clone();
            short.push((2, 2));
            assert_eq!(
                check(limits(Some(n), Some(e - 1)), &nodes, &short),
                Some(EdgeLimitExceeded { limit: e - 1 })
            );
        }
    }
}

fn profile(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_initialization-profile"))
        .args(args)
        .output()
        .unwrap()
}

fn report(args: &[&str]) -> Value {
    let output = profile(args);
    assert!(
        output.status.success(),
        "{args:?}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn bulk_cli_reports_match_incremental_and_validate_dynamic_continuation() {
    for workload in [
        "chain-split-rejoin-v1",
        "cycle-alternatives-v1",
        "dense-bridge-churn-v1",
        "components-join-split-v1",
    ] {
        for engine in ["compact-bfs", "ett-scan", "hdt"] {
            for surface in ["facade", "facade-limited"] {
                let common = [
                    "--nodes",
                    "16",
                    "--rounds",
                    "2",
                    "--workload",
                    workload,
                    "--engine",
                    engine,
                    "--surface",
                    surface,
                    "--timing",
                    "whole",
                    "--validate",
                ];
                let default = report(&common);
                let explicit = report(&[&common[..], &["--init-mode", "incremental"]].concat());
                let bulk =
                    report(&[&common[..], &["--init-mode", "bulk", "--warmup", "1"]].concat());
                // Incremental reports keep the historical schema, with or without the flag.
                assert!(default.get("initialization").is_none());
                assert!(explicit.get("initialization").is_none());
                assert_eq!(bulk["initialization"], "bulk");
                for key in ["engine", "surface", "timing", "workload", "config"] {
                    assert_eq!(default[key], bulk[key], "{key}");
                }
                assert_eq!(bulk["validated_dynamic_continuation"], true);
                let (a, b) = (&default["repetitions"][0], &bulk["repetitions"][0]);
                assert_eq!(
                    a["trace_fingerprint_fnv1a64"],
                    b["trace_fingerprint_fnv1a64"]
                );
                assert_eq!(a["initial_edges"], b["initial_edges"]);
                assert!(b.get("phases").is_none());
                let (setup, total) = (
                    b["setup_ns"].as_u64().unwrap(),
                    b["total_initialization_ns"].as_u64().unwrap(),
                );
                assert!(0 < setup && setup <= total);
            }
        }
    }
}

#[test]
fn incremental_report_schema_and_help_remain_compatible() {
    let keys = |value: &Value| -> Vec<String> {
        let mut keys: Vec<_> = value.as_object().unwrap().keys().cloned().collect();
        keys.sort();
        keys
    };
    let top = [
        "compiler",
        "config",
        "debug_assertions",
        "engine",
        "measurement",
        "repetitions",
        "schema_version",
        "surface",
        "timing",
        "validated_dynamic_continuation",
        "warmup",
        "workload",
    ];
    for surface in ["adapter", "facade", "facade-limited"] {
        let whole = report(&["--nodes", "16", "--surface", surface, "--timing", "whole"]);
        assert_eq!(keys(&whole), top);
        assert_eq!(
            keys(&whole["repetitions"][0]),
            [
                "initial_edges",
                "setup_ns",
                "total_initialization_ns",
                "trace_fingerprint_fnv1a64"
            ]
        );
    }
    let phases = report(&["--nodes", "16"]);
    assert_eq!(keys(&phases), top);
    assert!(phases["repetitions"][0].get("phases").is_some());
    let help = String::from_utf8(profile(&["--help"]).stdout).unwrap();
    assert!(help.contains("--init-mode incremental|bulk"));
}

#[test]
fn unsupported_bulk_requests_fail_explicitly_without_output() {
    for (args, message) in [
        (vec!["--init-mode", "bulk"], "--surface facade"),
        (
            vec![
                "--init-mode",
                "bulk",
                "--surface",
                "adapter",
                "--timing",
                "whole",
            ],
            "--surface facade",
        ),
        (
            vec!["--init-mode", "bulk", "--surface", "facade"],
            "--timing whole",
        ),
        (
            vec!["--init-mode", "bulk", "--surface", "facade-limited"],
            "--timing whole",
        ),
        (
            vec![
                "--init-mode",
                "bulk",
                "--surface",
                "facade",
                "--timing",
                "whole",
                "--engine",
                "reference-bfs",
            ],
            "compact-bfs",
        ),
        (vec!["--init-mode", "unknown"], "init-mode"),
        (vec!["--init-mode"], "requires a value"),
    ] {
        let output = profile(&args);
        assert!(!output.status.success(), "{args:?}");
        assert!(output.stdout.is_empty(), "{args:?}");
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(stderr.contains(message), "{args:?}: {stderr}");
    }
}
