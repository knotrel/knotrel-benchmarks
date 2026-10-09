//! Differential adapter tests: expected answers never come from a measured engine.
use knotrel_benchmarks::engines::{Engine, EngineKind};
use knotrel_core::GraphError;

#[test]
fn every_engine_preserves_registered_graph_semantics_and_cache_invalidation() {
    let ids = [0, 1, u64::MAX, 17, u64::MAX - 1, 29, 30, 31];
    for kind in EngineKind::ALL {
        let mut engine = Engine::new(kind, &ids).unwrap();
        let mut edges = vec![vec![false; ids.len()]; ids.len()];
        let mut seed = 42_u64;
        for step in 0..300 {
            seed = seed
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let a = (seed >> 32) as usize % ids.len();
            let b = (seed >> 48) as usize % ids.len();
            if a != b {
                let insert = step % 3 != 0;
                let changed = if insert {
                    engine.link(ids[a], ids[b])
                } else {
                    engine.cut(ids[b], ids[a])
                };
                assert_eq!(changed, Ok(edges[a][b] != insert), "{kind:?}, step {step}");
                edges[a][b] = insert;
                edges[b][a] = insert;
            }
            let mut reach = edges.clone();
            for (i, row) in reach.iter_mut().enumerate() {
                row[i] = true;
            }
            for k in 0..ids.len() {
                for i in 0..ids.len() {
                    for j in 0..ids.len() {
                        reach[i][j] |= reach[i][k] && reach[k][j];
                    }
                }
            }
            for (i, &source) in ids.iter().enumerate() {
                for (j, &target) in ids.iter().enumerate() {
                    for _ in 0..2 {
                        assert_eq!(
                            engine.connected(source, target),
                            Ok(reach[i][j]),
                            "{kind:?} step {step}, {i}->{j}"
                        );
                    }
                }
            }
        }
        assert_eq!(
            engine.connected(0, 42),
            Err(GraphError::UnknownNode { node: 42 })
        );
        assert_eq!(engine.link(0, 0), Err(GraphError::SelfLoop { node: 0 }));
        assert_eq!(engine.cut(0, 0), Err(GraphError::SelfLoop { node: 0 }));
    }
}

#[test]
fn repeated_bridge_and_cycle_queries_do_not_return_stale_answers() {
    for kind in EngineKind::ALL {
        let mut engine = Engine::new(kind, &[0, 1, 2, 3]).unwrap();
        for _ in 0..20 {
            assert_eq!(engine.link(0, 1), Ok(true));
            assert_eq!(engine.link(1, 2), Ok(true));
            assert_eq!(engine.link(2, 0), Ok(true));
            assert_eq!(engine.cut(0, 1), Ok(true));
            assert_eq!(engine.connected(0, 1), Ok(true));
            assert_eq!(engine.cut(0, 2), Ok(true));
            assert_eq!(engine.connected(0, 1), Ok(false));
            assert_eq!(engine.connected(0, 1), Ok(false));
            assert_eq!(engine.cut(1, 2), Ok(true));
            assert_eq!(engine.cut(1, 2), Ok(false));
            assert_eq!(engine.connected(3, 3), Ok(true));
        }
    }
}

#[test]
fn traversal_controls_observe_cuts_and_early_exit_without_stale_marks() {
    for name in ["traversal-bfs", "traversal-dfs"] {
        let kind = EngineKind::parse(name).expect("registered traversal control");
        let mut graph = Engine::new(kind, &[1, 7, 42, u64::MAX]).unwrap();
        graph.link(1, 7).unwrap();
        graph.link(7, 42).unwrap();
        assert_eq!(graph.connected(1, 7), Ok(true));
        assert_eq!(graph.connected(1, 42), Ok(true));
        graph.cut(7, 42).unwrap();
        assert_eq!(graph.connected(1, 42), Ok(false));
        assert_eq!(graph.connected(42, 42), Ok(true));
        assert_eq!(graph.connected(1, u64::MAX), Ok(false));
    }
}
