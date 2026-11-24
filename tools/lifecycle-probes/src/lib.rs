//! Shared workload generation and an independent application-side lifecycle
//! reference for the Knotrel v0.5.0 lifecycle qualification.
//!
//! - [`Rng`]: deterministic SplitMix64, so every arm replays the same trace.
//! - [`Topology`] and [`generate`]: sparse random graphs, rings with chords,
//!   and hub graphs with high-degree centers.
//! - [`Op`] traces: generated against a light model of registered topology so
//!   most mutations target existing objects (setters on absent objects are
//!   cheap error paths and would under-measure the work).
//! - [`Reference`]: what an application would write without M10. It keeps
//!   the same registered topology and flags in hash maps beside a plain
//!   [`ConnectivityGraph`] holding the effective graph, and implements the
//!   same results and error precedence. It never compacts removed vertices.
//! - [`Subject`]: the common interface both arms execute; results fold into
//!   a digest that must match between arms.

pub mod churn;

use knotrel_core::{ConnectivityGraph, EngineConfig, LifecycleError, LifecycleGraph};
use rustc_hash::{FxHashMap, FxHashSet};

/// Deterministic SplitMix64 generator.
#[derive(Debug, Clone)]
pub struct Rng(pub u64);

impl Rng {
    /// Next 64-bit value.
    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    }

    /// Uniform value in `0..bound` (`bound > 0`), with negligible modulo bias.
    pub fn below(&mut self, bound: u64) -> u64 {
        self.next_u64() % bound
    }
}

/// Graph families of the qualification matrix.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Topology {
    /// `2n` random edges (average degree about 4).
    Sparse,
    /// A ring with one chord every 64 nodes (cycles everywhere).
    Ring,
    /// A ring backbone plus `max(1, n / 2000)` hubs of degree `min(2000, n - 1)`.
    Hub,
}

impl Topology {
    /// Parses a CLI name.
    pub fn parse(name: &str) -> Option<Self> {
        Some(match name {
            "sparse" => Self::Sparse,
            "ring" => Self::Ring,
            "hub" => Self::Hub,
            _ => return None,
        })
    }

    /// The CLI name.
    pub fn name(self) -> &'static str {
        match self {
            Self::Sparse => "sparse",
            Self::Ring => "ring",
            Self::Hub => "hub",
        }
    }
}

/// Parses an engine selector.
pub fn parse_engine(name: &str) -> Option<EngineConfig> {
    Some(match name {
        "compact-bfs" => EngineConfig::CompactBfs,
        "ett" => EngineConfig::EulerTour,
        "hdt" => EngineConfig::Hdt,
        "cluster-forest" => EngineConfig::ClusterForest,
        _ => return None,
    })
}

/// Generates `n` nodes `0..n` and a deduplicated simple edge list.
pub fn generate(topology: Topology, n: u64, seed: u64) -> Vec<(u64, u64)> {
    let mut rng = Rng(seed);
    let mut set = FxHashSet::default();
    let mut edges = Vec::new();
    let mut push = |a: u64, b: u64, set: &mut FxHashSet<(u64, u64)>| {
        if a != b && set.insert((a.min(b), a.max(b))) {
            edges.push((a, b));
        }
    };
    match topology {
        Topology::Sparse => {
            for _ in 0..2 * n {
                let (a, b) = (rng.below(n), rng.below(n));
                push(a, b, &mut set);
            }
        }
        Topology::Ring => {
            for v in 0..n {
                push(v, (v + 1) % n, &mut set);
                if v % 64 == 0 {
                    push(v, rng.below(n), &mut set);
                }
            }
        }
        Topology::Hub => {
            for v in 0..n {
                push(v, (v + 1) % n, &mut set);
            }
            let hubs = (n / 2000).max(1);
            let degree = 2000.min(n - 1);
            for h in 0..hubs {
                let hub = rng.below(n);
                let _ = h;
                for _ in 0..degree {
                    push(hub, rng.below(n), &mut set);
                }
            }
        }
    }
    edges
}

/// One operation of a trace.
#[derive(Debug, Clone, Copy)]
pub enum Op {
    /// `add_node`.
    AddNode(u64),
    /// `link`.
    Link(u64, u64),
    /// `cut`.
    Cut(u64, u64),
    /// `connected`.
    Connected(u64, u64),
    /// `set_node_active`.
    SetNode(u64, bool),
    /// `set_edge_enabled`.
    SetEdge(u64, u64, bool),
    /// `remove_node`.
    Remove(u64),
}

/// Light model of registered topology used only to pick trace targets.
struct Model {
    nodes: Vec<u64>,
    node_index: FxHashMap<u64, usize>,
    edges: Vec<(u64, u64)>,
    edge_index: FxHashMap<(u64, u64), usize>,
    adjacency: FxHashMap<u64, Vec<u64>>,
}

impl Model {
    fn new(n: u64, edges: &[(u64, u64)]) -> Self {
        let mut model = Self {
            nodes: Vec::new(),
            node_index: FxHashMap::default(),
            edges: Vec::new(),
            edge_index: FxHashMap::default(),
            adjacency: FxHashMap::default(),
        };
        for v in 0..n {
            model.add_node(v);
        }
        for &(a, b) in edges {
            model.add_edge(a, b);
        }
        model
    }

    fn add_node(&mut self, v: u64) {
        if !self.node_index.contains_key(&v) {
            self.node_index.insert(v, self.nodes.len());
            self.nodes.push(v);
            self.adjacency.insert(v, Vec::new());
        }
    }

    fn add_edge(&mut self, a: u64, b: u64) {
        let key = (a.min(b), a.max(b));
        if a == b || self.edge_index.contains_key(&key) {
            return;
        }
        self.add_node(a);
        self.add_node(b);
        self.edge_index.insert(key, self.edges.len());
        self.edges.push(key);
        self.adjacency.get_mut(&a).unwrap().push(b);
        self.adjacency.get_mut(&b).unwrap().push(a);
    }

    fn remove_edge(&mut self, key: (u64, u64)) {
        let Some(index) = self.edge_index.remove(&key) else {
            return;
        };
        let last = self.edges.pop().unwrap();
        if index < self.edges.len() {
            self.edges[index] = last;
            self.edge_index.insert(last, index);
        }
        for (x, y) in [(key.0, key.1), (key.1, key.0)] {
            let list = self.adjacency.get_mut(&x).unwrap();
            let pos = list.iter().position(|&z| z == y).unwrap();
            list.swap_remove(pos);
        }
    }

    fn remove_node(&mut self, v: u64) {
        let Some(index) = self.node_index.remove(&v) else {
            return;
        };
        let neighbors = self.adjacency.get(&v).cloned().unwrap_or_default();
        for w in neighbors {
            self.remove_edge((v.min(w), v.max(w)));
        }
        self.adjacency.remove(&v);
        let last = self.nodes.pop().unwrap();
        if index < self.nodes.len() {
            self.nodes[index] = last;
            self.node_index.insert(last, index);
        }
    }

    fn node(&self, rng: &mut Rng) -> u64 {
        self.nodes[rng.below(self.nodes.len() as u64) as usize]
    }

    fn edge(&self, rng: &mut Rng) -> Option<(u64, u64)> {
        (!self.edges.is_empty()).then(|| self.edges[rng.below(self.edges.len() as u64) as usize])
    }
}

/// Operation mixes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mix {
    /// 90% `connected`, 10% lifecycle mutations.
    QueryHeavy,
    /// 10% `connected`, 90% lifecycle mutations.
    MutationHeavy,
    /// Legacy only: 50% `link`/`cut`, 50% `connected` (opt-in cost).
    Legacy,
    /// Only removals with fresh-ID re-registration (remove, add a never-used
    /// ID, link it twice), so retired engine slots accumulate and the
    /// lifecycle facade compacts inside the window.
    FreshChurn,
}

impl Mix {
    /// Parses a CLI name.
    pub fn parse(name: &str) -> Option<Self> {
        Some(match name {
            "query" => Self::QueryHeavy,
            "mutation" => Self::MutationHeavy,
            "legacy" => Self::Legacy,
            "fresh-churn" => Self::FreshChurn,
            _ => return None,
        })
    }
}

/// Generates a trace of `length` operations from the initial topology.
///
/// Lifecycle mutations: deactivate or reactivate a node (40%), disable or
/// enable an edge (40%), remove a node and re-register its ID with two new
/// edges (10%), link a random pair (5%), cut a registered edge (5%).
/// Removing hubs is allowed when the random pick lands on one.
pub fn trace(n: u64, edges: &[(u64, u64)], mix: Mix, length: usize, seed: u64) -> Vec<Op> {
    let mut rng = Rng(seed ^ 0x7ace);
    let mut model = Model::new(n, edges);
    let mut ops = Vec::with_capacity(length + length / 4);
    let query_percent = match mix {
        Mix::QueryHeavy => 90,
        Mix::MutationHeavy => 10,
        Mix::Legacy => 50,
        Mix::FreshChurn => 0,
    };
    let mut next_id = u64::MAX / 2;
    while ops.len() < length {
        if mix == Mix::FreshChurn {
            let v = model.node(&mut rng);
            ops.push(Op::Remove(v));
            model.remove_node(v);
            next_id += 1;
            ops.push(Op::AddNode(next_id));
            model.add_node(next_id);
            for _ in 0..2 {
                let w = model.node(&mut rng);
                ops.push(Op::Link(next_id, w));
                model.add_edge(next_id, w);
            }
            continue;
        }
        if rng.below(100) < query_percent {
            ops.push(Op::Connected(model.node(&mut rng), model.node(&mut rng)));
            continue;
        }
        if mix == Mix::Legacy {
            if rng.below(2) == 0 {
                let (a, b) = (model.node(&mut rng), model.node(&mut rng));
                ops.push(Op::Link(a, b));
                model.add_edge(a, b);
            } else if let Some(edge) = model.edge(&mut rng) {
                ops.push(Op::Cut(edge.0, edge.1));
                model.remove_edge(edge);
            }
            continue;
        }
        let flag = rng.below(2) == 0;
        match rng.below(100) {
            0..=39 => ops.push(Op::SetNode(model.node(&mut rng), flag)),
            40..=79 => {
                if let Some((a, b)) = model.edge(&mut rng) {
                    ops.push(Op::SetEdge(a, b, flag));
                }
            }
            80..=89 => {
                let v = model.node(&mut rng);
                ops.push(Op::Remove(v));
                model.remove_node(v);
                ops.push(Op::AddNode(v));
                model.add_node(v);
                for _ in 0..2 {
                    let w = model.node(&mut rng);
                    ops.push(Op::Link(v, w));
                    model.add_edge(v, w);
                }
            }
            90..=94 => {
                let (a, b) = (model.node(&mut rng), model.node(&mut rng));
                ops.push(Op::Link(a, b));
                model.add_edge(a, b);
            }
            _ => {
                if let Some(edge) = model.edge(&mut rng) {
                    ops.push(Op::Cut(edge.0, edge.1));
                    model.remove_edge(edge);
                }
            }
        }
    }
    ops
}

/// Result category folded into the digest: identical across arms.
fn code<T: Into<u64>>(result: Result<T, ErrorKind>) -> u64 {
    match result {
        Ok(value) => value.into(),
        Err(kind) => 100 + kind as u64,
    }
}

/// Error categories shared by every subject.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorKind {
    /// Self-loop.
    SelfLoop = 0,
    /// Unknown node.
    UnknownNode = 1,
    /// Unknown edge.
    UnknownEdge = 2,
    /// Any other error.
    Other = 3,
}

fn graph_kind(error: knotrel_core::GraphError) -> ErrorKind {
    match error {
        knotrel_core::GraphError::SelfLoop { .. } => ErrorKind::SelfLoop,
        knotrel_core::GraphError::UnknownNode { .. } => ErrorKind::UnknownNode,
        _ => ErrorKind::Other,
    }
}

fn lifecycle_kind(error: LifecycleError) -> ErrorKind {
    match error {
        LifecycleError::Graph(error) => graph_kind(error),
        LifecycleError::UnknownEdge { .. } => ErrorKind::UnknownEdge,
        _ => ErrorKind::Other,
    }
}

/// The interface both arms of a lifecycle comparison execute.
pub trait Subject {
    /// Builds the initial all-active topology (untimed).
    fn build(engine: EngineConfig, n: u64, edges: &[(u64, u64)]) -> Self;
    /// Executes one operation and returns its result code.
    fn apply(&mut self, op: Op) -> u64;
    /// Registered node and edge counts (all nodes and edges for the plain
    /// engine).
    fn counts(&self) -> (usize, usize);
    /// `connected` result code, for end-state comparison.
    fn query(&self, source: u64, target: u64) -> u64;
}

/// End-state fingerprint: counts and `connected` on `samples`.
pub fn state<S: Subject>(subject: &S, samples: &[(u64, u64)]) -> u64 {
    let (nodes, edges) = subject.counts();
    let mut digest = 0xcbf2_9ce4_8422_2325_u64 ^ (nodes as u64) ^ ((edges as u64) << 32);
    for &(a, b) in samples {
        digest ^= subject.query(a, b);
        digest = digest.wrapping_mul(0x0100_0000_01b3);
    }
    digest
}

/// Runs a trace and returns an order-sensitive FNV-1a digest of results.
pub fn run<S: Subject>(subject: &mut S, ops: &[Op]) -> u64 {
    let mut digest = 0xcbf2_9ce4_8422_2325_u64;
    for &op in ops {
        digest ^= subject.apply(op);
        digest = digest.wrapping_mul(0x0100_0000_01b3);
    }
    digest
}

impl Subject for LifecycleGraph {
    fn build(engine: EngineConfig, n: u64, edges: &[(u64, u64)]) -> Self {
        // Since knotrel 0.5.0 (B1) only compact-bfs supports lifecycle; the
        // matrix gives the lifecycle arm no other engine.
        let mut graph =
            LifecycleGraph::new(engine).expect("lifecycle cells use a supported engine");
        for v in 0..n {
            graph.add_node(v).unwrap();
        }
        for &(a, b) in edges {
            graph.link(a, b).unwrap();
        }
        graph
    }

    fn apply(&mut self, op: Op) -> u64 {
        match op {
            Op::AddNode(v) => code(self.add_node(v).map_err(graph_kind)),
            Op::Link(a, b) => code(self.link(a, b).map_err(graph_kind)),
            Op::Cut(a, b) => code(self.cut(a, b).map_err(graph_kind)),
            Op::Connected(a, b) => code(self.connected(a, b).map_err(graph_kind)),
            Op::SetNode(v, f) => code(self.set_node_active(v, f).map_err(lifecycle_kind)),
            Op::SetEdge(a, b, f) => code(self.set_edge_enabled(a, b, f).map_err(lifecycle_kind)),
            Op::Remove(v) => u64::from(self.remove_node(v)),
        }
    }

    fn counts(&self) -> (usize, usize) {
        (self.node_count(), self.edge_count())
    }

    fn query(&self, source: u64, target: u64) -> u64 {
        code(self.connected(source, target).map_err(graph_kind))
    }
}

/// The plain engine, for legacy-only traces (opt-in cost).
pub struct Plain(pub ConnectivityGraph);

impl Subject for Plain {
    fn build(engine: EngineConfig, n: u64, edges: &[(u64, u64)]) -> Self {
        let mut graph = ConnectivityGraph::new(engine);
        for v in 0..n {
            graph.add_node(v).unwrap();
        }
        for &(a, b) in edges {
            graph.link(a, b).unwrap();
        }
        Self(graph)
    }

    fn apply(&mut self, op: Op) -> u64 {
        match op {
            Op::AddNode(v) => code(self.0.add_node(v).map_err(graph_kind)),
            Op::Link(a, b) => code(self.0.link(a, b).map_err(graph_kind)),
            Op::Cut(a, b) => code(self.0.cut(a, b).map_err(graph_kind)),
            Op::Connected(a, b) => code(self.0.connected(a, b).map_err(graph_kind)),
            _ => panic!("the plain engine runs legacy traces only"),
        }
    }

    fn counts(&self) -> (usize, usize) {
        (self.0.node_count(), self.0.edge_count())
    }

    fn query(&self, source: u64, target: u64) -> u64 {
        code(self.0.connected(source, target).map_err(graph_kind))
    }
}

/// Application-side lifecycle over a plain engine: registered topology and
/// flags in hash maps, the effective graph in the engine.
pub struct Reference {
    nodes: FxHashMap<u64, RefNode>,
    engine: ConnectivityGraph,
}

struct RefNode {
    active: bool,
    neighbors: FxHashMap<u64, bool>,
}

impl Reference {
    /// Logical counts: registered nodes, registered edges, active nodes,
    /// enabled edges, effective edges and engine vertices (which keep removed
    /// nodes: the reference never compacts).
    pub fn logical(&self) -> [usize; 6] {
        let mut edges = 0;
        let mut enabled = 0;
        for node in self.nodes.values() {
            edges += node.neighbors.len();
            enabled += node.neighbors.values().filter(|&&e| e).count();
        }
        [
            self.nodes.len(),
            edges / 2,
            self.nodes.values().filter(|n| n.active).count(),
            enabled / 2,
            self.engine.edge_count(),
            self.engine.node_count(),
        ]
    }

    fn effective(&self, a: u64, b: u64) -> bool {
        self.nodes[&a].active && self.nodes[&b].active
    }

    fn engine_link(&mut self, a: u64, b: u64) {
        self.engine.link(a, b).unwrap();
    }

    fn engine_cut(&mut self, a: u64, b: u64) {
        self.engine.cut(a, b).unwrap();
    }

    fn add_node(&mut self, v: u64) -> bool {
        if self.nodes.contains_key(&v) {
            return false;
        }
        self.nodes.insert(
            v,
            RefNode {
                active: true,
                neighbors: FxHashMap::default(),
            },
        );
        self.engine.add_node(v).unwrap();
        true
    }

    fn link(&mut self, a: u64, b: u64) -> Result<bool, ErrorKind> {
        if a == b {
            return Err(ErrorKind::SelfLoop);
        }
        if self
            .nodes
            .get(&a)
            .is_some_and(|n| n.neighbors.contains_key(&b))
        {
            return Ok(false);
        }
        self.add_node(a);
        self.add_node(b);
        self.nodes.get_mut(&a).unwrap().neighbors.insert(b, true);
        self.nodes.get_mut(&b).unwrap().neighbors.insert(a, true);
        if self.effective(a, b) {
            self.engine_link(a, b);
        }
        Ok(true)
    }

    fn cut(&mut self, a: u64, b: u64) -> Result<bool, ErrorKind> {
        if a == b {
            return Err(ErrorKind::SelfLoop);
        }
        let Some(enabled) = self
            .nodes
            .get(&a)
            .and_then(|n| n.neighbors.get(&b).copied())
        else {
            return Ok(false);
        };
        let effective = enabled && self.effective(a, b);
        self.nodes.get_mut(&a).unwrap().neighbors.remove(&b);
        self.nodes.get_mut(&b).unwrap().neighbors.remove(&a);
        if effective {
            self.engine_cut(a, b);
        }
        Ok(true)
    }

    fn set_node(&mut self, v: u64, active: bool) -> Result<bool, ErrorKind> {
        let node = self.nodes.get(&v).ok_or(ErrorKind::UnknownNode)?;
        if node.active == active {
            return Ok(false);
        }
        let affected: Vec<u64> = node
            .neighbors
            .iter()
            .filter(|&(w, &enabled)| enabled && self.nodes[w].active)
            .map(|(&w, _)| w)
            .collect();
        for w in affected {
            if active {
                self.engine_link(v, w);
            } else {
                self.engine_cut(v, w);
            }
        }
        self.nodes.get_mut(&v).unwrap().active = active;
        Ok(true)
    }

    fn set_edge(&mut self, a: u64, b: u64, enabled: bool) -> Result<bool, ErrorKind> {
        if a == b {
            return Err(ErrorKind::SelfLoop);
        }
        for v in [a, b] {
            if !self.nodes.contains_key(&v) {
                return Err(ErrorKind::UnknownNode);
            }
        }
        let current = *self.nodes[&a]
            .neighbors
            .get(&b)
            .ok_or(ErrorKind::UnknownEdge)?;
        if current == enabled {
            return Ok(false);
        }
        self.nodes.get_mut(&a).unwrap().neighbors.insert(b, enabled);
        self.nodes.get_mut(&b).unwrap().neighbors.insert(a, enabled);
        if self.effective(a, b) {
            if enabled {
                self.engine_link(a, b);
            } else {
                self.engine_cut(a, b);
            }
        }
        Ok(true)
    }

    fn remove(&mut self, v: u64) -> bool {
        let Some(node) = self.nodes.remove(&v) else {
            return false;
        };
        for (w, enabled) in node.neighbors {
            let neighbor = self.nodes.get_mut(&w).unwrap();
            neighbor.neighbors.remove(&v);
            if enabled && node.active && neighbor.active {
                self.engine_cut(v, w);
            }
        }
        true
    }

    fn connected(&self, a: u64, b: u64) -> Result<bool, ErrorKind> {
        let na = self.nodes.get(&a).ok_or(ErrorKind::UnknownNode)?;
        let nb = self.nodes.get(&b).ok_or(ErrorKind::UnknownNode)?;
        if !na.active || !nb.active {
            return Ok(false);
        }
        self.engine.connected(a, b).map_err(graph_kind)
    }
}

impl Subject for Reference {
    fn build(engine: EngineConfig, n: u64, edges: &[(u64, u64)]) -> Self {
        let mut reference = Self {
            nodes: FxHashMap::default(),
            engine: ConnectivityGraph::new(engine),
        };
        for v in 0..n {
            reference.add_node(v);
        }
        for &(a, b) in edges {
            reference.link(a, b).unwrap();
        }
        reference
    }

    fn apply(&mut self, op: Op) -> u64 {
        match op {
            Op::AddNode(v) => u64::from(self.add_node(v)),
            Op::Link(a, b) => code(self.link(a, b)),
            Op::Cut(a, b) => code(self.cut(a, b)),
            Op::Connected(a, b) => code(self.connected(a, b)),
            Op::SetNode(v, f) => code(self.set_node(v, f)),
            Op::SetEdge(a, b, f) => code(self.set_edge(a, b, f)),
            Op::Remove(v) => u64::from(self.remove(v)),
        }
    }

    fn counts(&self) -> (usize, usize) {
        let logical = self.logical();
        (logical[0], logical[1])
    }

    fn query(&self, source: u64, target: u64) -> u64 {
        code(self.connected(source, target))
    }
}

/// Current resident set size of this process in bytes, via `ps` (macOS and
/// Linux), or `None` if unavailable.
pub fn rss_bytes() -> Option<u64> {
    let pid = std::process::id().to_string();
    let output = std::process::Command::new("ps")
        .args(["-o", "rss=", "-p", &pid])
        .output()
        .ok()?;
    let kib: u64 = String::from_utf8(output.stdout).ok()?.trim().parse().ok()?;
    Some(kib * 1024)
}

/// First output line of every probe: the measured source and build variant.
pub fn build_record(probe: &str) -> serde_json::Value {
    serde_json::json!({
        "kind": "build",
        "probe": probe,
        "knotrel_rev": env!("KNOTREL_REV"),
        "knotrel_dirty": env!("KNOTREL_DIRTY") == "true",
        "probes_rev": env!("PROBES_REV"),
        "probes_dirty": env!("PROBES_DIRTY") == "true",
        "count_alloc": cfg!(feature = "count-alloc"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The facade and the reference agree on every mixed trace and engine,
    /// operation by operation (not only on the folded digest).
    #[test]
    fn reference_matches_lifecycle_graph_operation_by_operation() {
        // Lifecycle support is compact-bfs only since knotrel 0.5.0 (B1).
        for engine in [EngineConfig::CompactBfs] {
            for (topology, mix) in [
                (Topology::Sparse, Mix::MutationHeavy),
                (Topology::Hub, Mix::QueryHeavy),
                (Topology::Ring, Mix::MutationHeavy),
                (Topology::Sparse, Mix::FreshChurn),
            ] {
                let edges = generate(topology, 300, 11);
                let ops = trace(300, &edges, mix, 3_000, 11);
                let mut facade = <LifecycleGraph as Subject>::build(engine, 300, &edges);
                let mut reference = Reference::build(engine, 300, &edges);
                for op in &ops {
                    assert_eq!(facade.apply(*op), reference.apply(*op), "{op:?}");
                }
            }
        }
    }

    #[test]
    fn legacy_traces_contain_only_legacy_operations() {
        let edges = generate(Topology::Sparse, 100, 3);
        let ops = trace(100, &edges, Mix::Legacy, 1_000, 3);
        assert!(
            ops.iter()
                .all(|op| matches!(op, Op::Link(..) | Op::Cut(..) | Op::Connected(..)))
        );
    }
}
