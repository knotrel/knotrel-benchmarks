//! Benchmark-only controlled traversals over a snapshot of Compact adjacency.
//! Mutation/ID code copied from knotrel-core on 2026-10-05; no production API changes.
use knotrel_core::{GraphError, NodeId};
use std::collections::{BTreeMap, VecDeque, btree_map::Entry};

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
    /// Maximum logical container length; Vec BFS retains expanded entries until query end.
    pub peak_buffer_len: usize,
}

/// Logical scratch work from one counted query; not allocator or timing data.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, serde::Serialize)]
pub struct ScratchStats {
    /// Newly added mark elements initialized by growth (u32 epochs or u64 words).
    pub mark_initialized_elements: usize,
    /// Mark elements explicitly cleared, separately from growth initialization.
    pub mark_cleared_elements: usize,
    /// Mark capacity times element size, excluding allocator and Vec metadata.
    pub mark_capacity_bytes: usize,
    /// Pushes that increased queue capacity, not measured allocator calls.
    pub queue_growth_events: usize,
    /// Queue capacity increases times index size; not bytes copied or allocator traffic.
    pub queue_capacity_increase_bytes: usize,
    /// Queue capacity times index size, unchanged by clearing its logical length.
    pub queue_capacity_bytes: usize,
}

/// Counted queue work and capacities, excluding container and allocator metadata.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, serde::Serialize)]
pub struct QueueStats {
    /// Vertices enqueued, including the source but not an early-discovered target.
    pub enqueues: usize,
    /// Largest capacity times index size during this query, including retained initial capacity.
    pub peak_capacity_bytes: usize,
    /// Capacity after query cleanup, before any caller-owned scratch is dropped.
    pub final_capacity_bytes: usize,
}

/// Optional exact internal-index traversal order, for tests and diagnostics only.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct TraversalOrder {
    /// Expanded vertices in FIFO order.
    pub expanded: Vec<usize>,
    /// Inspected directed adjacency entries, including the target-discovering entry.
    pub examined: Vec<(usize, usize)>,
}

fn push_frontier<const COUNT: bool>(
    frontier: &mut Vec<usize>,
    scratch: &mut ScratchStats,
    vertex: usize,
) {
    let previous_capacity = if COUNT { frontier.capacity() } else { 0 };
    frontier.push(vertex);
    if COUNT {
        let capacity = frontier.capacity();
        scratch.queue_growth_events += usize::from(capacity > previous_capacity);
        scratch.queue_capacity_increase_bytes +=
            (capacity - previous_capacity) * size_of::<usize>();
        scratch.queue_capacity_bytes = capacity * size_of::<usize>();
    }
}

/// Caller-owned scratch, using identical u32 epochs and Vec storage for BFS/DFS.
#[derive(Debug, Default)]
pub struct SearchSpace {
    visited: Vec<u32>,
    generation: u32,
    frontier: Vec<usize>,
    stats: SearchStats,
    scratch: ScratchStats,
}
impl SearchSpace {
    /// Last diagnostic query's structural counts; zero in uninstrumented mode.
    pub fn stats(&self) -> SearchStats {
        self.stats
    }

    /// Most recent counted scratch ledger; uncounted calls leave it unchanged.
    pub fn scratch_stats(&self) -> ScratchStats {
        self.scratch
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
        if COUNT {
            space.scratch = ScratchStats {
                mark_capacity_bytes: space.visited.capacity() * size_of::<u32>(),
                queue_capacity_bytes: space.frontier.capacity() * size_of::<usize>(),
                ..ScratchStats::default()
            };
        }
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
            if COUNT {
                space.scratch.mark_initialized_elements =
                    self.adjacency.len() - space.visited.len();
            }
            space.visited.resize(self.adjacency.len(), 0);
        }
        space.generation = space.generation.wrapping_add(1);
        if space.generation == 0 {
            if COUNT {
                space.scratch.mark_cleared_elements = space.visited.len();
            }
            space.visited.fill(0);
            space.generation = 1;
        }
        if COUNT {
            space.scratch.mark_capacity_bytes = space.visited.capacity() * size_of::<u32>();
        }
        let generation = space.generation;
        space.visited[a] = generation;
        push_frontier::<COUNT>(&mut space.frontier, &mut space.scratch, a);
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
                    push_frontier::<COUNT>(&mut space.frontier, &mut space.scratch, neighbor);
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
        assert_eq!(s.scratch_stats().mark_cleared_elements, 5);
        g.cut(0, 1).unwrap();
        assert!(!g.search::<true, false>(0, 3, &mut s).unwrap());
        assert_eq!(s.stats(), SearchStats::default());
    }

    #[test]
    fn deque_growth_while_wrapped_preserves_fifo_order_and_capacity() {
        let mut space = DequeSearchSpace {
            frontier: VecDeque::with_capacity(4),
            ..DequeSearchSpace::default()
        };
        let capacity = space.frontier.capacity();
        for vertex in 0..capacity {
            push_deque_frontier::<true>(&mut space, vertex);
        }
        for vertex in 0..capacity / 2 {
            assert_eq!(space.frontier.pop_front(), Some(vertex));
        }
        for vertex in capacity..capacity + capacity / 2 {
            push_deque_frontier::<true>(&mut space, vertex);
        }
        assert!(!space.frontier.as_slices().1.is_empty());
        let growths = space.scratch.queue_growth_events;
        push_deque_frontier::<true>(&mut space, capacity + capacity / 2);
        assert!(space.frontier.capacity() > capacity);
        assert_eq!(space.scratch.queue_growth_events, growths + 1);
        let expected: Vec<_> = (capacity / 2..=capacity + capacity / 2).collect();
        assert_eq!(space.frontier.iter().copied().collect::<Vec<_>>(), expected);
        let retained = space.frontier.capacity();
        while space.frontier.pop_front().is_some() {}
        assert_eq!(space.frontier.capacity(), retained);
    }
}

/// Benchmark-only reusable packed visit marks and the same BFS queue as epochs.
/// Retained marks use eight bytes per 64 registered vertices (rounded up).
/// Every non-reflexive query clears the retained bitset; no answers are cached.
#[derive(Debug, Default)]
pub struct BitSearchSpace {
    visited: Vec<u64>,
    frontier: Vec<usize>,
    stats: SearchStats,
    scratch: ScratchStats,
    queue: QueueStats,
    order: Option<TraversalOrder>,
}
impl BitSearchSpace {
    /// Creates diagnostic scratch that records exact counted traversal order.
    pub fn with_order_recording() -> Self {
        Self {
            order: Some(TraversalOrder::default()),
            ..Self::default()
        }
    }

    /// Recorded order from the last counted query, if explicitly enabled.
    pub fn recorded_order(&self) -> Option<&TraversalOrder> {
        self.order.as_ref()
    }

    /// Queue counters from the last counted query; uncounted calls leave them unchanged.
    pub fn queue_stats(&self) -> QueueStats {
        self.queue
    }

    /// Last diagnostic query's counts; zero for uninstrumented searches.
    pub fn stats(&self) -> SearchStats {
        self.stats
    }

    /// Most recent counted scratch ledger; uncounted calls leave it unchanged.
    pub fn scratch_stats(&self) -> ScratchStats {
        self.scratch
    }
}
impl Graph {
    /// Exact BFS with packed marks; same ordering and early exit as epoch BFS.
    /// Costs O(retained mark words + reached vertices + examined arcs), plus
    /// O(log V) ID lookup and amortized scratch growth. Retained marks are cleared
    /// even after switching to a smaller graph. COUNT is compiled out when false.
    ///
    /// # Errors
    /// Reports unknown endpoints, source first, matching epoch BFS.
    pub fn search_bits<const COUNT: bool>(
        &self,
        source: NodeId,
        target: NodeId,
        space: &mut BitSearchSpace,
    ) -> Result<bool, GraphError> {
        space.stats = SearchStats::default();
        if COUNT {
            space.scratch = ScratchStats {
                mark_capacity_bytes: space.visited.capacity() * size_of::<u64>(),
                queue_capacity_bytes: space.frontier.capacity() * size_of::<usize>(),
                ..ScratchStats::default()
            };
            let capacity = space.frontier.capacity() * size_of::<usize>();
            space.queue = QueueStats {
                peak_capacity_bytes: capacity,
                final_capacity_bytes: capacity,
                ..QueueStats::default()
            };
            if let Some(order) = &mut space.order {
                order.expanded.clear();
                order.examined.clear();
            }
        }
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
        let words = self.adjacency.len().div_ceil(64);
        if space.visited.len() < words {
            if COUNT {
                space.scratch.mark_initialized_elements = words - space.visited.len();
            }
            space.visited.resize(words, 0);
        }
        if COUNT {
            space.scratch.mark_cleared_elements = space.visited.len();
            space.scratch.mark_capacity_bytes = space.visited.capacity() * size_of::<u64>();
        }
        space.visited.fill(0);
        space.visited[a / 64] |= 1_u64 << (a % 64);
        push_frontier::<COUNT>(&mut space.frontier, &mut space.scratch, a);
        let mut cursor = 0;
        let mut found = false;
        if COUNT {
            space.stats.peak_frontier = 1;
            space.stats.peak_buffer_len = 1;
            space.queue.enqueues = 1;
        }
        'search: loop {
            if cursor == space.frontier.len() {
                break;
            }
            let vertex = space.frontier[cursor];
            cursor += 1;
            if COUNT {
                space.stats.expanded_vertices += 1;
                if let Some(order) = &mut space.order {
                    order.expanded.push(vertex);
                }
            }
            for &neighbor in &self.adjacency[vertex] {
                if COUNT {
                    space.stats.examined_arcs += 1;
                    if let Some(order) = &mut space.order {
                        order.examined.push((vertex, neighbor));
                    }
                }
                if neighbor == b {
                    found = true;
                    break 'search;
                }
                let word = neighbor / 64;
                let mask = 1_u64 << (neighbor % 64);
                if space.visited[word] & mask == 0 {
                    space.visited[word] |= mask;
                    push_frontier::<COUNT>(&mut space.frontier, &mut space.scratch, neighbor);
                    if COUNT {
                        space.queue.enqueues += 1;
                        space.stats.peak_buffer_len =
                            space.stats.peak_buffer_len.max(space.frontier.len());
                        let pending = space.frontier.len() - cursor;
                        space.stats.peak_frontier = space.stats.peak_frontier.max(pending);
                    }
                }
            }
        }
        space.frontier.clear();
        if COUNT {
            let capacity = space.frontier.capacity() * size_of::<usize>();
            space.queue.peak_capacity_bytes = capacity;
            space.queue.final_capacity_bytes = capacity;
        }
        Ok(found)
    }
}

/// Benchmark-only VecDeque FIFO with the same packed marks and reset policy as BitSearchSpace.
#[derive(Debug, Default)]
pub struct DequeSearchSpace {
    visited: Vec<u64>,
    frontier: VecDeque<usize>,
    stats: SearchStats,
    scratch: ScratchStats,
    queue: QueueStats,
    order: Option<TraversalOrder>,
}

impl DequeSearchSpace {
    /// Creates diagnostic scratch that records exact counted traversal order.
    pub fn with_order_recording() -> Self {
        Self {
            order: Some(TraversalOrder::default()),
            ..Self::default()
        }
    }

    /// Recorded order from the last counted query, if explicitly enabled.
    pub fn recorded_order(&self) -> Option<&TraversalOrder> {
        self.order.as_ref()
    }

    /// Last query's graph-work counters; zero in uninstrumented mode.
    pub fn stats(&self) -> SearchStats {
        self.stats
    }

    /// Last counted scratch work, not allocator traffic or bytes copied.
    pub fn scratch_stats(&self) -> ScratchStats {
        self.scratch
    }

    /// Last counted queue work; final capacity is retained until scratch is dropped.
    pub fn queue_stats(&self) -> QueueStats {
        self.queue
    }
}

fn push_deque_frontier<const COUNT: bool>(space: &mut DequeSearchSpace, vertex: usize) {
    let previous_capacity = if COUNT { space.frontier.capacity() } else { 0 };
    space.frontier.push_back(vertex);
    if COUNT {
        let capacity = space.frontier.capacity();
        space.queue.enqueues += 1;
        space.scratch.queue_growth_events += usize::from(capacity > previous_capacity);
        space.scratch.queue_capacity_increase_bytes +=
            (capacity - previous_capacity) * size_of::<usize>();
        space.scratch.queue_capacity_bytes = capacity * size_of::<usize>();
        space.queue.peak_capacity_bytes = space
            .queue
            .peak_capacity_bytes
            .max(capacity * size_of::<usize>());
    }
}

impl Graph {
    /// Packed-bit BFS using only standard-library push_back/pop_front FIFO operations.
    ///
    /// Uses identical endpoints, sorted adjacency, mark-on-enqueue and early target
    /// detection to search_bits. Pending frontier excludes the expanded vertex;
    /// deque logical storage contains only pending entries. Popping and clearing do
    /// not shrink capacity. Cost is O(retained mark words + reached vertices + arcs),
    /// plus O(log V) ID lookup and amortized queue/mark growth. No answers are cached.
    ///
    /// # Errors
    /// Reports unknown endpoints, source first, before allocating query scratch.
    pub fn search_deque<const COUNT: bool>(
        &self,
        source: NodeId,
        target: NodeId,
        space: &mut DequeSearchSpace,
    ) -> Result<bool, GraphError> {
        const WORD_BITS: usize = u64::BITS as usize;
        space.stats = SearchStats::default();
        if COUNT {
            let capacity = space.frontier.capacity() * size_of::<usize>();
            space.scratch = ScratchStats {
                mark_capacity_bytes: space.visited.capacity() * size_of::<u64>(),
                queue_capacity_bytes: capacity,
                ..ScratchStats::default()
            };
            space.queue = QueueStats {
                peak_capacity_bytes: capacity,
                final_capacity_bytes: capacity,
                ..QueueStats::default()
            };
            if let Some(order) = &mut space.order {
                order.expanded.clear();
                order.examined.clear();
            }
        }
        let source_index = *self
            .ids
            .get(&source)
            .ok_or(GraphError::UnknownNode { node: source })?;
        let target_index = *self
            .ids
            .get(&target)
            .ok_or(GraphError::UnknownNode { node: target })?;
        if source_index == target_index {
            return Ok(true);
        }
        let words = self.adjacency.len().div_ceil(WORD_BITS);
        if space.visited.len() < words {
            if COUNT {
                space.scratch.mark_initialized_elements = words - space.visited.len();
            }
            space.visited.resize(words, 0);
        }
        if COUNT {
            space.scratch.mark_cleared_elements = space.visited.len();
            space.scratch.mark_capacity_bytes = space.visited.capacity() * size_of::<u64>();
        }
        space.visited.fill(0);
        space.visited[source_index / WORD_BITS] |= 1_u64 << (source_index % WORD_BITS);
        push_deque_frontier::<COUNT>(space, source_index);
        if COUNT {
            space.stats.peak_frontier = 1;
            space.stats.peak_buffer_len = 1;
        }
        let mut found = false;
        'search: while let Some(vertex) = space.frontier.pop_front() {
            if COUNT {
                space.stats.expanded_vertices += 1;
                if let Some(order) = &mut space.order {
                    order.expanded.push(vertex);
                }
            }
            for &neighbor in &self.adjacency[vertex] {
                if COUNT {
                    space.stats.examined_arcs += 1;
                    if let Some(order) = &mut space.order {
                        order.examined.push((vertex, neighbor));
                    }
                }
                if neighbor == target_index {
                    found = true;
                    break 'search;
                }
                let word = neighbor / WORD_BITS;
                let mask = 1_u64 << (neighbor % WORD_BITS);
                if space.visited[word] & mask == 0 {
                    space.visited[word] |= mask;
                    push_deque_frontier::<COUNT>(space, neighbor);
                    if COUNT {
                        space.stats.peak_frontier =
                            space.stats.peak_frontier.max(space.frontier.len());
                        space.stats.peak_buffer_len =
                            space.stats.peak_buffer_len.max(space.frontier.len());
                    }
                }
            }
        }
        space.frontier.clear();
        if COUNT {
            space.queue.final_capacity_bytes = space.frontier.capacity() * size_of::<usize>();
        }
        Ok(found)
    }

    /// Uninstrumented packed-bit Vec BFS with fresh query-local scratch.
    ///
    /// Allocation, mark initialization and scratch destruction are included in the
    /// call. No diagnostic workspace or order recorder is constructed. Matches
    /// the existing packed control's O(V + E) BFS and initialization semantics.
    ///
    /// # Errors
    /// Reports unknown endpoints, source first.
    #[inline(never)]
    pub fn connected_fresh_packed_vec(
        &self,
        source: NodeId,
        target: NodeId,
    ) -> Result<bool, GraphError> {
        const WORD_BITS: usize = u64::BITS as usize;
        let source_index = *self
            .ids
            .get(&source)
            .ok_or(GraphError::UnknownNode { node: source })?;
        let target_index = *self
            .ids
            .get(&target)
            .ok_or(GraphError::UnknownNode { node: target })?;
        if source_index == target_index {
            return Ok(true);
        }
        let mut visited = vec![0_u64; self.adjacency.len().div_ceil(WORD_BITS)];
        visited.fill(0);
        let mut frontier = Vec::new();
        visited[source_index / WORD_BITS] |= 1_u64 << (source_index % WORD_BITS);
        frontier.push(source_index);
        let mut cursor = 0;
        while cursor < frontier.len() {
            let vertex = frontier[cursor];
            cursor += 1;
            for &neighbor in &self.adjacency[vertex] {
                if neighbor == target_index {
                    return Ok(true);
                }
                let word = neighbor / WORD_BITS;
                let mask = 1_u64 << (neighbor % WORD_BITS);
                if visited[word] & mask == 0 {
                    visited[word] |= mask;
                    frontier.push(neighbor);
                }
            }
        }
        Ok(false)
    }

    /// Uninstrumented packed-bit VecDeque BFS with fresh query-local scratch.
    ///
    /// Matches the Vec wrapper's ownership, marks and result boundary; only queue
    /// operations differ. No diagnostic workspace is constructed. Time remains O(V + E).
    ///
    /// # Errors
    /// Reports unknown endpoints, source first.
    #[inline(never)]
    pub fn connected_fresh_packed_deque(
        &self,
        source: NodeId,
        target: NodeId,
    ) -> Result<bool, GraphError> {
        const WORD_BITS: usize = u64::BITS as usize;
        let source_index = *self
            .ids
            .get(&source)
            .ok_or(GraphError::UnknownNode { node: source })?;
        let target_index = *self
            .ids
            .get(&target)
            .ok_or(GraphError::UnknownNode { node: target })?;
        if source_index == target_index {
            return Ok(true);
        }
        let mut visited = vec![0_u64; self.adjacency.len().div_ceil(WORD_BITS)];
        visited.fill(0);
        let mut frontier = VecDeque::new();
        visited[source_index / WORD_BITS] |= 1_u64 << (source_index % WORD_BITS);
        frontier.push_back(source_index);
        while let Some(vertex) = frontier.pop_front() {
            for &neighbor in &self.adjacency[vertex] {
                if neighbor == target_index {
                    return Ok(true);
                }
                let word = neighbor / WORD_BITS;
                let mask = 1_u64 << (neighbor % WORD_BITS);
                if visited[word] & mask == 0 {
                    visited[word] |= mask;
                    frontier.push_back(neighbor);
                }
            }
        }
        Ok(false)
    }
}
