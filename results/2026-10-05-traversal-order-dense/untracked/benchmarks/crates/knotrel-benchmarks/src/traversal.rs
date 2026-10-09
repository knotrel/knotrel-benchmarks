//! Benchmark-only controlled traversals over a snapshot of Compact adjacency.
//! Mutation/ID code copied from knotrel-core on 2026-10-05; no production API changes.
use knotrel_core::{GraphError, NodeId};
use std::collections::{BTreeMap, btree_map::Entry};

/// Benchmark copy of Compact's sorted adjacency and growing stable indices.
#[derive(Debug, Default)]
pub struct Graph {
    ids: BTreeMap<NodeId, usize>,
    adjacency: Vec<Vec<usize>>,
    edges: usize,
}

impl Graph {
    /// Creates an empty graph in O(1) time.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds an isolated vertex, returning true only if it was absent.
    ///
    /// Existing edges are unchanged. O(log V) amortized time; growing the outer
    /// vector can take O(V) in a single insertion. Indices never change.
    pub fn add_node(&mut self, node: NodeId) -> bool {
        if let Entry::Vacant(entry) = self.ids.entry(node) {
            let index = self.adjacency.len();
            self.adjacency.push(Vec::new());
            entry.insert(index);
            true
        } else {
            false
        }
    }

    /// Inserts an undirected edge, creating absent endpoints.
    ///
    /// Reversed endpoints identify the same edge; duplicates return false.
    /// O(log V + deg(source) + deg(target)) amortized time, including sorted
    /// vector shifts. A new vertex can trigger an O(V) capacity growth.
    ///
    /// # Errors
    /// Returns [`GraphError::SelfLoop`] without creating vertices for equal IDs.
    pub fn link(&mut self, source: NodeId, target: NodeId) -> Result<bool, GraphError> {
        Self::check_distinct(source, target)?;
        self.add_node(source);
        self.add_node(target);
        let a = self.ids[&source];
        let b = self.ids[&target];
        let Err(position) = self.adjacency[a].binary_search(&b) else {
            return Ok(false);
        };
        let reverse = self.adjacency[b]
            .binary_search(&a)
            .expect_err("symmetric absence");
        self.adjacency[a].insert(position, b);
        self.adjacency[b].insert(reverse, a);
        self.edges += 1;
        Ok(true)
    }

    /// Removes an edge, preserving vertices; absent edges return false.
    ///
    /// Worst-case time: O(log V + deg(source) + deg(target)), due to vector shifts.
    ///
    /// # Errors
    /// Returns [`GraphError::SelfLoop`] for equal IDs without changing the graph.
    pub fn cut(&mut self, source: NodeId, target: NodeId) -> Result<bool, GraphError> {
        Self::check_distinct(source, target)?;
        let (Some(&a), Some(&b)) = (self.ids.get(&source), self.ids.get(&target)) else {
            return Ok(false);
        };
        let Ok(position) = self.adjacency[a].binary_search(&b) else {
            return Ok(false);
        };
        let reverse = self.adjacency[b].binary_search(&a).expect("symmetric edge");
        self.adjacency[a].remove(position);
        self.adjacency[b].remove(reverse);
        self.edges -= 1;
        Ok(true)
    }

    /// Returns the number of vertices, including isolated ones, in O(1) time.
    #[must_use]
    pub fn node_count(&self) -> usize {
        self.adjacency.len()
    }

    /// Returns the number of undirected edges in O(1) time.
    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.edges
    }

    fn check_distinct(source: NodeId, target: NodeId) -> Result<(), GraphError> {
        if source == target {
            Err(GraphError::SelfLoop { node: source })
        } else {
            Ok(())
        }
    }
}

/// Structural work from one diagnostic query; not timing instrumentation.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, serde::Serialize)]
pub struct SearchStats {
    /// Vertices removed from the frontier and expanded (target discovery exits early).
    pub expanded_vertices: usize,
    /// Adjacency entries inspected, including the target-discovering entry.
    pub examined_arcs: usize,
    /// Maximum number of pending vertices, excluding an already expanded vertex.
    pub peak_frontier: usize,
    /// Maximum live vector length; BFS retains expanded entries until query end.
    pub peak_buffer_len: usize,
}

/// Caller-owned scratch, using identical u32 epochs and Vec storage for BFS/DFS.
#[derive(Debug, Default)]
pub struct SearchSpace {
    visited: Vec<u32>,
    generation: u32,
    frontier: Vec<usize>,
    stats: SearchStats,
}
impl SearchSpace {
    /// Last diagnostic query's structural counts; zero in uninstrumented mode.
    pub fn stats(&self) -> SearchStats {
        self.stats
    }
}
impl Graph {
    /// Exact search with BFS (`DFS=false`) or LIFO traversal (`DFS=true`).
    /// Both mark on insertion and stop when an inspected neighbor is the target.
    /// Each vertex enters the frontier at most once. Work is O(reached vertices
    /// plus examined arcs), with O(log V) endpoint lookup and amortized scratch
    /// growth. Epoch rollover clears marks in O(V). COUNT is compile-time-only
    /// instrumentation; normal benchmark instantiations have COUNT=false.
    ///
    /// # Errors
    /// Reports unknown endpoints, source first, matching the production core.
    pub fn search<const DFS: bool, const COUNT: bool>(
        &self,
        source: NodeId,
        target: NodeId,
        space: &mut SearchSpace,
    ) -> Result<bool, GraphError> {
        space.stats = SearchStats::default();
        let a = *self
            .ids
            .get(&source)
            .ok_or(GraphError::UnknownNode { node: source })?;
        let b = *self
            .ids
            .get(&target)
            .ok_or(GraphError::UnknownNode { node: target })?;
        if a == b {
            return Ok(true);
        }
        if space.visited.len() < self.adjacency.len() {
            space.visited.resize(self.adjacency.len(), 0);
        }
        space.generation = space.generation.wrapping_add(1);
        if space.generation == 0 {
            space.visited.fill(0);
            space.generation = 1;
        }
        let generation = space.generation;
        space.visited[a] = generation;
        space.frontier.push(a);
        let mut cursor = 0;
        let mut found = false;
        if COUNT {
            space.stats.peak_frontier = 1;
            space.stats.peak_buffer_len = 1;
        }
        'search: loop {
            let vertex = if DFS {
                let Some(vertex) = space.frontier.pop() else {
                    break;
                };
                vertex
            } else {
                if cursor == space.frontier.len() {
                    break;
                }
                let vertex = space.frontier[cursor];
                cursor += 1;
                vertex
            };
            if COUNT {
                space.stats.expanded_vertices += 1;
            }
            for &neighbor in &self.adjacency[vertex] {
                if COUNT {
                    space.stats.examined_arcs += 1;
                }
                if neighbor == b {
                    found = true;
                    break 'search;
                }
                if space.visited[neighbor] != generation {
                    space.visited[neighbor] = generation;
                    space.frontier.push(neighbor);
                    if COUNT {
                        space.stats.peak_buffer_len =
                            space.stats.peak_buffer_len.max(space.frontier.len());
                        let pending = space.frontier.len() - if DFS { 0 } else { cursor };
                        space.stats.peak_frontier = space.stats.peak_frontier.max(pending);
                    }
                }
            }
        }
        space.frontier.clear();
        Ok(found)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn branching_order_counts_and_rollover_are_exact() {
        let mut g = Graph::new();
        for (a, b) in [(0, 1), (0, 2), (1, 3), (2, 4)] {
            g.link(a, b).unwrap();
        }
        let mut s = SearchSpace::default();
        assert!(g.search::<false, true>(0, 4, &mut s).unwrap());
        assert_eq!(s.stats().expanded_vertices, 3);
        assert_eq!(s.stats().examined_arcs, 6);
        assert!(g.search::<true, true>(0, 4, &mut s).unwrap());
        assert_eq!(s.stats().expanded_vertices, 2);
        assert_eq!(s.stats().examined_arcs, 4);
        s.generation = u32::MAX;
        s.visited.fill(1);
        assert!(g.search::<true, true>(0, 3, &mut s).unwrap());
        g.cut(0, 1).unwrap();
        assert!(!g.search::<true, false>(0, 3, &mut s).unwrap());
        assert_eq!(s.stats(), SearchStats::default());
    }
}
