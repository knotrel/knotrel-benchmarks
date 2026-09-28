//! Benchmark adapters over a pre-registered vertex universe.
//!
//! These are experimental comparison backends, not replacements for Knotrel's
//! growing-node API. ID translation and duplicate/edge-handle bookkeeping are
//! included in timed calls. Reference BFS retains its original implementation.

use crate::ett_baseline::ForestGraph as BaselineForest;
use crate::hdt_baseline::HdtGraph as BaselineHdt;
use knotrel_core::{
    ForestGraph, ForestStats, Graph, GraphError, HdtGraph, HdtStats, ReferenceGraph,
};
use outils::prelude::{DynamicConnectivity, DynamicGraph, Edge, EmptyWeight, VertexIndex};
use petgraph::{
    Undirected,
    algo::{DfsSpace, has_path_connecting},
    graph::{Graph as PetGraph, NodeIndex},
    visit::Visitable,
};
use std::collections::BTreeMap;

type TraversalGraph = PetGraph<(), (), Undirected, usize>;
type SearchSpace = DfsSpace<NodeIndex<usize>, <TraversalGraph as Visitable>::Map>;

/// Implementations compared under the same operation contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EngineKind {
    /// Original ordered-adjacency Knotrel BFS.
    Reference,
    /// Growing-node production core with compact sorted adjacency and local BFS scratch.
    Compact,
    /// AVL Euler-tour forest with exhaustive smaller-side replacement search.
    EttScan,
    /// Experimental Knotrel HDT with growing vertices and exact-level promotions.
    Hdt,
    /// Frozen HDT v2 with eager per-level vertex storage.
    HdtV2,
    /// Frozen original ETT implementation with eager smaller-side enumeration.
    EttBaseline,
    /// Compact-index adjacency vectors with reusable BFS scratch memory.
    DenseBfs,
    /// petgraph 0.8.3 depth-first path test with reusable traversal space.
    Petgraph,
    /// outils 0.3.0 HDT with an adapter for simple-graph semantics.
    Outils,
}
impl EngineKind {
    /// Stable default comparison order; collectors should rotate this order.
    pub const ALL: [Self; 9] = [
        Self::Reference,
        Self::Compact,
        Self::EttScan,
        Self::Hdt,
        Self::HdtV2,
        Self::EttBaseline,
        Self::DenseBfs,
        Self::Petgraph,
        Self::Outils,
    ];
    /// CLI selector, also recorded in comparison manifests.
    #[must_use]
    pub fn key(self) -> &'static str {
        match self {
            Self::Reference => "reference-bfs",
            Self::Compact => "compact-bfs",
            Self::EttScan => "ett-scan",
            Self::Hdt => "hdt",
            Self::HdtV2 => "hdt-v2",
            Self::EttBaseline => "ett-scan-v1",
            Self::DenseBfs => "dense-bfs",
            Self::Petgraph => "petgraph-dfs",
            Self::Outils => "outils-hdt",
        }
    }
    /// Versioned backend identity for measurement reports.
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Reference => "knotrel-core/reference-bfs",
            Self::Compact => "knotrel-core/compact-bfs-v1",
            Self::EttScan => "knotrel-core/ett-pruned-v2",
            Self::Hdt => "knotrel-core/hdt-sparse-levels-v3",
            Self::HdtV2 => "knotrel-core/hdt-levels-v2",
            Self::EttBaseline => "knotrel-core/ett-scan-v1",
            Self::DenseBfs => "knotrel-benchmarks/dense-bfs-v1",
            Self::Petgraph => "petgraph-0.8.3/dfs",
            Self::Outils => "outils-0.3.0/hdt",
        }
    }
    /// Parse an explicit selector without silently falling back.
    ///
    /// # Errors
    /// Returns an error for unknown names.
    pub fn parse(name: &str) -> Result<Self, &'static str> {
        Self::ALL
            .into_iter()
            .find(|kind| kind.key() == name)
            .ok_or("unknown engine")
    }
}

/// Synchronous benchmark backend supporting pre-registered arbitrary u64 IDs.
///
/// Indexed backends reject new endpoints after construction. The reference
/// delegates directly to the original core, whose links can create endpoints.
/// Comparisons therefore register every vertex before measurement. This does
/// not establish parity for dynamically growing vertex universes.
pub struct Engine {
    storage: Storage,
}
enum Storage {
    Reference(ReferenceGraph),
    Compact(Graph),
    EttScan(ForestGraph),
    Hdt(HdtGraph),
    HdtV2(BaselineHdt),
    EttBaseline(BaselineForest),
    Indexed(Box<Indexed>),
}
struct Indexed {
    ids: BTreeMap<u64, usize>,
    backend: Backend,
}
enum Backend {
    Dense {
        adjacency: Vec<Vec<usize>>,
        visited: Vec<bool>,
        queue: Vec<usize>,
    },
    Petgraph {
        graph: TraversalGraph,
        scratch: SearchSpace,
    },
    Outils {
        graph: Box<DynamicGraph<EmptyWeight>>,
        edges: BTreeMap<(usize, usize), Edge>,
    },
}

impl Engine {
    /// Initialize all registered vertices, including isolated ones.
    ///
    /// Setup is measured separately from operations. Dense/petgraph storage is
    /// O(n+m); HDT includes O(n log n) forest entries plus edges and adapter maps.
    /// The outils adjacency reservation hint is fixed at four for every workload.
    ///
    /// # Errors
    /// Rejects empty or duplicate node lists. Allocation exhaustion may panic.
    pub fn new(kind: EngineKind, nodes: &[u64]) -> Result<Self, &'static str> {
        let ids: BTreeMap<_, _> = nodes
            .iter()
            .copied()
            .enumerate()
            .map(|(i, id)| (id, i))
            .collect();
        if nodes.is_empty() || ids.len() != nodes.len() {
            return Err("need nonempty unique registered nodes");
        }
        let n = nodes.len();
        if kind == EngineKind::Reference {
            let mut graph = ReferenceGraph::new();
            for &node in nodes {
                graph.add_node(node);
            }
            return Ok(Self {
                storage: Storage::Reference(graph),
            });
        }
        if kind == EngineKind::Compact {
            let mut graph = Graph::new();
            for &node in nodes {
                graph.add_node(node);
            }
            return Ok(Self {
                storage: Storage::Compact(graph),
            });
        }
        if kind == EngineKind::EttScan {
            let mut graph = ForestGraph::new();
            for &node in nodes {
                graph.add_node(node);
            }
            return Ok(Self {
                storage: Storage::EttScan(graph),
            });
        }
        if kind == EngineKind::Hdt {
            let mut graph = HdtGraph::new();
            for &node in nodes {
                graph.add_node(node);
            }
            return Ok(Self {
                storage: Storage::Hdt(graph),
            });
        }
        if kind == EngineKind::HdtV2 {
            let mut graph = BaselineHdt::new();
            for &node in nodes {
                graph.add_node(node);
            }
            return Ok(Self {
                storage: Storage::HdtV2(graph),
            });
        }
        if kind == EngineKind::EttBaseline {
            let mut graph = BaselineForest::new();
            for &node in nodes {
                graph.add_node(node);
            }
            return Ok(Self {
                storage: Storage::EttBaseline(graph),
            });
        }
        let backend = match kind {
            EngineKind::DenseBfs => Backend::Dense {
                adjacency: vec![Vec::new(); n],
                visited: vec![false; n],
                queue: Vec::with_capacity(n),
            },
            EngineKind::Petgraph => {
                let mut graph = TraversalGraph::with_capacity(n, 0);
                for _ in nodes {
                    graph.add_node(());
                }
                let scratch = DfsSpace::new(&graph);
                Backend::Petgraph { graph, scratch }
            }
            EngineKind::Outils => Backend::Outils {
                graph: Box::new(DynamicGraph::new(n, 4)),
                edges: BTreeMap::new(),
            },
            EngineKind::Reference
            | EngineKind::Compact
            | EngineKind::Hdt
            | EngineKind::HdtV2
            | EngineKind::EttScan
            | EngineKind::EttBaseline => unreachable!(),
        };
        Ok(Self {
            storage: Storage::Indexed(Box::new(Indexed { ids, backend })),
        })
    }

    /// Reset diagnostic work counters after initial loading.
    pub fn reset_stats(&mut self) {
        match &mut self.storage {
            Storage::EttScan(graph) => graph.reset_stats(),
            Storage::Hdt(graph) => graph.reset_stats(),
            Storage::HdtV2(graph) => graph.reset_stats(),
            Storage::EttBaseline(graph) => graph.reset_stats(),
            _ => {}
        }
    }
    /// Replacement-search counters, available only for the ETT backends.
    ///
    /// In the frozen v1 backend, `scanned_vertices` counts all eagerly enumerated
    /// vertices. In v2 it counts only yielded candidate-bearing vertices, as in
    /// the current core type. Neither counter counts AVL tokens traversed.
    #[must_use]
    pub fn forest_stats(&self) -> Option<ForestStats> {
        match &self.storage {
            Storage::EttScan(graph) => Some(graph.stats()),
            Storage::EttBaseline(graph) => Some(graph.stats()),
            _ => None,
        }
    }

    /// HDT-only diagnostic counters, separate from ETT scan accounting.
    #[must_use]
    pub fn hdt_stats(&self) -> Option<HdtStats> {
        match &self.storage {
            Storage::Hdt(graph) => Some(graph.stats()),
            Storage::HdtV2(graph) => {
                let s = graph.stats();
                Some(HdtStats {
                    tree_cuts: s.tree_cuts,
                    candidate_edges: s.candidate_edges,
                    replacements: s.replacements,
                    tree_promotions: s.tree_promotions,
                    non_tree_promotions: s.non_tree_promotions,
                    levels_visited: s.levels_visited,
                })
            }
            _ => None,
        }
    }

    /// Structural storage snapshot for either HDT adapter; collect outside timers.
    #[must_use]
    pub fn hdt_storage_stats(&self) -> Option<knotrel_core::HdtStorageStats> {
        match &self.storage {
            Storage::Hdt(graph) => Some(graph.storage_stats()),
            Storage::HdtV2(graph) => Some(graph.storage_stats()),
            _ => None,
        }
    }

    /// Insert an undirected edge; return false for duplicates (including reversal).
    ///
    /// # Errors
    /// Rejects self-loops before mutation. Indexed backends reject unknown nodes.
    pub fn link(&mut self, source: u64, target: u64) -> Result<bool, GraphError> {
        self.update(source, target, true)
    }
    /// Remove an edge without deleting vertices; return false for absent edges.
    ///
    /// # Errors
    /// Rejects self-loops before mutation. Unknown cut endpoints return false.
    pub fn cut(&mut self, source: u64, target: u64) -> Result<bool, GraphError> {
        self.update(source, target, false)
    }
    /// Query exact connectivity, including existing-node reflexivity.
    ///
    /// Dense BFS resets O(n) visited bits, explores reachable edges and queues
    /// each vertex at most once: O(n+m) worst-case traversal and O(log n) ID
    /// translation, with O(n) reusable scratch. It caches no connectivity answers.
    /// petgraph uses DFS with reusable scratch; this is explicitly not BFS.
    /// outils queries its maintained HDT forest after O(log n) ID translation.
    ///
    /// # Errors
    /// Returns UnknownNode, checking source before target, for absent IDs.
    pub fn connected(&mut self, source: u64, target: u64) -> Result<bool, GraphError> {
        let indexed = match &mut self.storage {
            Storage::Reference(graph) => return graph.connected(source, target),
            Storage::Compact(graph) => return graph.connected(source, target),
            Storage::EttScan(graph) => return graph.connected(source, target),
            Storage::Hdt(graph) => return graph.connected(source, target),
            Storage::HdtV2(graph) => return graph.connected(source, target),
            Storage::EttBaseline(graph) => return graph.connected(source, target),
            Storage::Indexed(indexed) => indexed,
        };
        let (a, b) = indexed.endpoints(source, target)?;
        if a == b {
            return Ok(true);
        }
        Ok(match &mut indexed.backend {
            Backend::Dense {
                adjacency,
                visited,
                queue,
            } => {
                visited.fill(false);
                queue.clear();
                visited[a] = true;
                queue.push(a);
                let mut cursor = 0;
                let mut found = false;
                // Every queued vertex is reachable. Mark at insertion, so the
                // queue contains each vertex at most once. Exhaustion proves
                // disconnection. Early success does not leave reusable answers.
                'search: while cursor < queue.len() {
                    for &neighbor in &adjacency[queue[cursor]] {
                        if neighbor == b {
                            found = true;
                            break 'search;
                        }
                        if !visited[neighbor] {
                            visited[neighbor] = true;
                            queue.push(neighbor);
                        }
                    }
                    cursor += 1;
                }
                found
            }
            Backend::Petgraph { graph, scratch } => {
                has_path_connecting(&*graph, NodeIndex::new(a), NodeIndex::new(b), Some(scratch))
            }
            // outils returns false for v==w; the adapter handles it above.
            Backend::Outils { graph, .. } => graph.is_connected(VertexIndex(a), VertexIndex(b)),
        })
    }

    // Dense and petgraph locate an edge by scanning endpoint adjacency:
    // O(deg(source)+deg(target)+log n) worst case including ID translation.
    // Outils bookkeeping uses O(log m) ordered edge-handle lookup on top of the
    // upstream HDT operations. Never pass a stale or duplicate handle upstream.
    fn update(&mut self, source: u64, target: u64, insert: bool) -> Result<bool, GraphError> {
        if source == target {
            return Err(GraphError::SelfLoop { node: source });
        }
        let indexed = match &mut self.storage {
            Storage::Reference(graph) => {
                return if insert {
                    graph.link(source, target)
                } else {
                    graph.cut(source, target)
                };
            }
            Storage::Compact(graph) => {
                return if insert {
                    graph.link(source, target)
                } else {
                    graph.cut(source, target)
                };
            }
            Storage::EttScan(graph) => {
                return if insert {
                    graph.link(source, target)
                } else {
                    graph.cut(source, target)
                };
            }
            Storage::Hdt(graph) => {
                return if insert {
                    graph.link(source, target)
                } else {
                    graph.cut(source, target)
                };
            }
            Storage::HdtV2(graph) => {
                return if insert {
                    graph.link(source, target)
                } else {
                    graph.cut(source, target)
                };
            }
            Storage::EttBaseline(graph) => {
                return if insert {
                    graph.link(source, target)
                } else {
                    graph.cut(source, target)
                };
            }
            Storage::Indexed(indexed) => indexed,
        };
        let (a, b) = match indexed.endpoints(source, target) {
            Ok(pair) => pair,
            Err(error) => return if insert { Err(error) } else { Ok(false) },
        };
        Ok(match &mut indexed.backend {
            Backend::Dense { adjacency, .. } => {
                let position = adjacency[a].iter().position(|&v| v == b);
                match (insert, position) {
                    (true, None) => {
                        adjacency[a].push(b);
                        adjacency[b].push(a);
                        true
                    }
                    (false, Some(i)) => {
                        adjacency[a].swap_remove(i);
                        let j = adjacency[b]
                            .iter()
                            .position(|&v| v == a)
                            .expect("symmetric edge");
                        adjacency[b].swap_remove(j);
                        true
                    }
                    _ => false,
                }
            }
            Backend::Petgraph { graph, .. } => {
                let a = NodeIndex::new(a);
                let b = NodeIndex::new(b);
                match (insert, graph.find_edge(a, b)) {
                    (true, None) => {
                        graph.add_edge(a, b, ());
                        true
                    }
                    (false, Some(edge)) => {
                        graph.remove_edge(edge);
                        true
                    }
                    _ => false,
                }
            }
            Backend::Outils { graph, edges } => {
                let key = (a.min(b), a.max(b));
                if insert {
                    if let std::collections::btree_map::Entry::Vacant(entry) = edges.entry(key) {
                        let edge = graph
                            .insert_edge(VertexIndex(a), VertexIndex(b))
                            .expect("distinct registered vertices");
                        entry.insert(edge);
                        true
                    } else {
                        false
                    }
                } else if let Some(edge) = edges.remove(&key) {
                    graph.delete_edge(edge);
                    true
                } else {
                    false
                }
            }
        })
    }
}
impl Indexed {
    fn endpoints(&self, source: u64, target: u64) -> Result<(usize, usize), GraphError> {
        let a = *self
            .ids
            .get(&source)
            .ok_or(GraphError::UnknownNode { node: source })?;
        let b = *self
            .ids
            .get(&target)
            .ok_or(GraphError::UnknownNode { node: target })?;
        Ok((a, b))
    }
}
