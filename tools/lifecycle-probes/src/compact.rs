//! Workloads and correctness-gate records of the knotrel#151 comparison
//! (compact internal node indices, option B64; knotrel
//! `docs/design/compact-node-index.md`, section 6).
//!
//! The same source is built against both arms (base and candidate), so every
//! input below is a pure function of its parameters and seed, and every
//! observation reports what the cross-arm correctness gate compares (section
//! 6.5): an input fingerprint, logical counts and the `LifecycleStorage`
//! entry counts (`catalog_nodes`, `incident_entries`, `engine_vertices`,
//! `retired_vertices`). Capacities are reported beside the gate, never in it.
//!
//! Workloads (section 6.3):
//!
//! - `sparse`, `ring`, `hub`: the existing [`crate::generate`] families, node
//!   IDs `0..n`.
//! - `star` (`--degree D`): the `core-lifecycle` star, center 0, leaves
//!   `1..=D`, plus a path among the leaves; `D + 1` nodes.
//! - `hub-in-sparse` (`--nodes N --degree D`): `sparse` with `N` nodes plus
//!   one extra hub linked to `D` distinct random nodes (`D <= N`). Node IDs are
//!   spaced: sparse node `i` has ID `4 i`, the hub has ID `4 N`. IDs `4 i + 2`
//!   are reserved for *ghost* nodes (registered, linked to the hub and removed
//!   before paging, so that cursors can name removed nodes at random
//!   positions) and IDs `4 i + 1`, `4 i + 3` are never registered. Hub spokes
//!   are the last `D` edges, in ascending leaf ID.
//! - `iso` (`--nodes N`): `N` registered nodes, no edge.
//!
//! Slot-order states (section 6.3): `ordered` builds with
//! `LifecycleGraph::try_from_topology` (all nodes active, all edges enabled,
//! nodes in ascending ID); `scrambled` registers every node with `add_node`
//! in a seeded random order, then links the edges in workload order.

use crate::{Rng, Topology, generate};
use knotrel_core::{EdgeSpec, EngineConfig, GraphLimits, LifecycleGraph, NodeSpec};
use serde_json::{Value, json};

/// Salt of the hub-leaf draw of `hub-in-sparse`.
const HUB_SALT: u64 = 0x4b1d_5eed_0151;
/// Salt of the scrambled registration order.
const SCRAMBLE_SALT: u64 = 0x5c4a_3b1e_0151;
/// Salt of the incremental (random) edge order.
const EDGE_ORDER_SALT: u64 = 0xed6e_0dde_0151;
/// Salt of the mass-removal draw (M5, C2).
const MASS_SALT: u64 = 0x3a55_0151;

/// FNV-1a offset basis.
pub const FNV_START: u64 = 0xcbf2_9ce4_8422_2325;

/// One FNV-1a step over a 64-bit word.
pub fn fnv(digest: u64, word: u64) -> u64 {
    (digest ^ word).wrapping_mul(0x0100_0000_01b3)
}

/// A generated workload: registered node IDs (ascending) and the edge list.
#[derive(Debug, Clone)]
pub struct Workload {
    /// The workload name with its parameters, e.g. `hub-in-sparse-10000`.
    pub label: String,
    /// Every registered node, ascending.
    pub ids: Vec<u64>,
    /// Deduplicated simple edges; for hub workloads the spokes are last.
    pub edges: Vec<(u64, u64)>,
    /// The hub (`star`, `hub-in-sparse`).
    pub hub: Option<u64>,
    /// Number of leading edges that are not hub spokes.
    pub base_edges: usize,
    /// Sparse node count `N` of `hub-in-sparse` (ID spacing base).
    pub spaced: Option<u64>,
}

/// Fisher-Yates prefix: the first `k` items of a seeded permutation of `items`.
pub fn sample<T: Copy>(items: &[T], k: usize, rng: &mut Rng) -> Vec<T> {
    let mut pool = items.to_vec();
    let k = k.min(pool.len());
    for i in 0..k {
        let j = i + rng.below((pool.len() - i) as u64) as usize;
        pool.swap(i, j);
    }
    pool.truncate(k);
    pool
}

/// Seeded in-place shuffle.
pub fn shuffle<T>(items: &mut [T], rng: &mut Rng) {
    for i in (1..items.len()).rev() {
        let j = rng.below(i as u64 + 1) as usize;
        items.swap(i, j);
    }
}

/// A star of degree `degree` around node 0 plus a path among the leaves (the
/// `core-lifecycle` `degree` workload).
pub fn star(degree: u64) -> Vec<(u64, u64)> {
    let mut edges: Vec<(u64, u64)> = (1..=degree).map(|leaf| (0, leaf)).collect();
    for leaf in 1..degree {
        edges.push((leaf, leaf + 1));
    }
    edges
}

impl Workload {
    /// Generates a workload by name (see the module documentation).
    pub fn generate(name: &str, nodes: u64, degree: u64, seed: u64) -> Result<Self, String> {
        if let Some(topology) = Topology::parse(name) {
            let edges = generate(topology, nodes, seed);
            let base_edges = edges.len();
            return Ok(Self {
                label: format!("{name}-{nodes}"),
                ids: (0..nodes).collect(),
                edges,
                hub: None,
                base_edges,
                spaced: None,
            });
        }
        match name {
            "star" => {
                if degree < 1 {
                    return Err("star needs --degree >= 1".into());
                }
                let mut edges = star(degree);
                // Spokes last, as for hub-in-sparse (same edge set).
                edges.rotate_left(degree as usize);
                Ok(Self {
                    label: format!("star-{degree}"),
                    ids: (0..=degree).collect(),
                    base_edges: edges.len() - degree as usize,
                    edges,
                    hub: Some(0),
                    spaced: None,
                })
            }
            "hub-in-sparse" => {
                if degree > nodes || degree == 0 {
                    return Err("hub-in-sparse needs 1 <= --degree <= --nodes".into());
                }
                let sparse = generate(Topology::Sparse, nodes, seed);
                let hub = 4 * nodes;
                let mut edges: Vec<(u64, u64)> =
                    sparse.iter().map(|&(a, b)| (4 * a, 4 * b)).collect();
                let base_edges = edges.len();
                let all: Vec<u64> = (0..nodes).collect();
                let mut leaves = sample(&all, degree as usize, &mut Rng(seed ^ HUB_SALT));
                leaves.sort_unstable();
                edges.extend(leaves.into_iter().map(|leaf| (hub, 4 * leaf)));
                let mut ids: Vec<u64> = (0..nodes).map(|i| 4 * i).collect();
                ids.push(hub);
                Ok(Self {
                    label: format!("hub-in-sparse-{degree}"),
                    ids,
                    edges,
                    hub: Some(hub),
                    base_edges,
                    spaced: Some(nodes),
                })
            }
            "iso" => Ok(Self {
                label: format!("iso-{nodes}"),
                ids: (0..nodes).collect(),
                edges: Vec::new(),
                hub: None,
                base_edges: 0,
                spaced: None,
            }),
            other => Err(format!("unknown workload {other:?}")),
        }
    }

    /// Hub spokes (`(hub, leaf)`, ascending leaf), empty without a hub.
    pub fn spokes(&self) -> &[(u64, u64)] {
        &self.edges[self.base_edges..]
    }

    /// Edges that are not hub spokes.
    pub fn base(&self) -> &[(u64, u64)] {
        &self.edges[..self.base_edges]
    }

    /// Nodes other than the hub.
    pub fn ordinary(&self) -> Vec<u64> {
        self.ids
            .iter()
            .copied()
            .filter(|&v| Some(v) != self.hub)
            .collect()
    }

    /// Order-sensitive FNV-1a fingerprint of the node and edge lists.
    pub fn fingerprint(&self) -> String {
        let mut d = fnv(
            fnv(FNV_START, self.ids.len() as u64),
            self.edges.len() as u64,
        );
        for &v in &self.ids {
            d = fnv(d, v);
        }
        for &(a, b) in &self.edges {
            d = fnv(fnv(d, a), b);
        }
        format!("{d:016x}")
    }

    /// Logical counts right after an all-active, all-enabled build.
    pub fn expected(&self) -> [usize; 5] {
        let (v, e) = (self.ids.len(), self.edges.len());
        [v, e, v, e, e]
    }

    /// Ghost IDs (`4 i + 2`) and never-registered IDs (`4 i + 1` or `4 i + 3`)
    /// of a spaced workload, `count` of each, distinct, from `rng`.
    pub fn cursor_ids(&self, count: usize, rng: &mut Rng) -> Result<(Vec<u64>, Vec<u64>), String> {
        let n = self
            .spaced
            .ok_or("cursor kinds need a hub-in-sparse workload")?;
        let all: Vec<u64> = (0..n).collect();
        let ghosts = sample(&all, count, rng)
            .into_iter()
            .map(|i| 4 * i + 2)
            .collect();
        let never = sample(&all, count, rng)
            .into_iter()
            .map(|i| 4 * i + 1 + 2 * rng.below(2))
            .collect();
        Ok((ghosts, never))
    }
}

/// Builds the `ordered` state: `try_from_topology`, all active and enabled.
pub fn build_ordered(engine: EngineConfig, workload: &Workload) -> Result<LifecycleGraph, String> {
    let (nodes, edges) = specs(workload);
    LifecycleGraph::try_from_topology(engine, GraphLimits::default(), &nodes, &edges)
        .map_err(|e| e.to_string())
}

/// Bulk-import inputs: every node active, every edge enabled.
pub fn specs(workload: &Workload) -> (Vec<NodeSpec>, Vec<EdgeSpec>) {
    let nodes = workload
        .ids
        .iter()
        .map(|&node| NodeSpec { node, active: true })
        .collect();
    let edges = workload
        .edges
        .iter()
        .map(|&(source, target)| EdgeSpec {
            source,
            target,
            enabled: true,
        })
        .collect();
    (nodes, edges)
}

/// The seeded registration order of the `scrambled` state.
pub fn scrambled_order(workload: &Workload, seed: u64) -> Vec<u64> {
    let mut order = workload.ids.clone();
    shuffle(&mut order, &mut Rng(seed ^ SCRAMBLE_SALT));
    order
}

/// Builds the `scrambled` state: `add_node` in a seeded random ID order, then
/// `link` in workload order.
pub fn build_scrambled(
    engine: EngineConfig,
    workload: &Workload,
    seed: u64,
) -> Result<LifecycleGraph, String> {
    let mut graph = LifecycleGraph::new(engine).map_err(|e| e.to_string())?;
    for v in scrambled_order(workload, seed) {
        graph.add_node(v).map_err(|e| e.to_string())?;
    }
    for &(a, b) in &workload.edges {
        graph.link(a, b).map_err(|e| e.to_string())?;
    }
    Ok(graph)
}

/// Builds a state by name (`ordered` or `scrambled`).
pub fn build_state(
    engine: EngineConfig,
    workload: &Workload,
    state: &str,
    seed: u64,
) -> Result<LifecycleGraph, String> {
    match state {
        "ordered" => build_ordered(engine, workload),
        "scrambled" => build_scrambled(engine, workload, seed),
        other => Err(format!("unknown --state {other:?}")),
    }
}

/// The incremental build order (M2, I1): the non-spoke edges in a seeded
/// random order, then the hub spokes in ascending leaf ID.
pub fn incremental_edges(workload: &Workload, seed: u64) -> Vec<(u64, u64)> {
    let mut edges = workload.base().to_vec();
    shuffle(&mut edges, &mut Rng(seed ^ EDGE_ORDER_SALT));
    edges.extend_from_slice(workload.spokes());
    edges
}

/// Incremental build: `link` in the given order (creating endpoints), then
/// `add_node` for every ID (registers isolated nodes; a no-op otherwise).
pub fn build_incremental(
    engine: EngineConfig,
    ids: &[u64],
    edges: &[(u64, u64)],
) -> Result<LifecycleGraph, String> {
    let mut graph = LifecycleGraph::new(engine).map_err(|e| e.to_string())?;
    for &(a, b) in edges {
        graph.link(a, b).map_err(|e| e.to_string())?;
    }
    for &v in ids {
        graph.add_node(v).map_err(|e| e.to_string())?;
    }
    Ok(graph)
}

/// `[nodes, edges, active nodes, enabled edges, effective edges]`.
pub fn logical(graph: &LifecycleGraph) -> [usize; 5] {
    [
        graph.node_count(),
        graph.edge_count(),
        graph.active_node_count(),
        graph.enabled_edge_count(),
        graph.effective_edge_count(),
    ]
}

/// The `LifecycleStorage` entry counts the gate compares.
pub fn storage_entries(graph: &LifecycleGraph) -> Value {
    let s = graph.storage_stats();
    json!({"catalog_nodes": s.catalog_nodes, "incident_entries": s.incident_entries,
           "engine_vertices": s.engine_vertices, "retired_vertices": s.retired_vertices})
}

/// Capacities (reported, not gated).
pub fn storage_capacities(graph: &LifecycleGraph) -> Value {
    let s = graph.storage_stats();
    json!({"catalog_node_capacity": s.catalog_node_capacity,
           "incident_capacity": s.incident_capacity})
}

/// The gate object for a graph: fingerprint, logical counts and storage entries.
pub fn gate(workload: &Workload, graph: &LifecycleGraph) -> Value {
    json!({"fingerprint": workload.fingerprint(), "logical": logical(graph),
           "storage": storage_entries(graph)})
}

/// Fails unless the graph's logical counts equal `expected`.
pub fn check_logical(graph: &LifecycleGraph, expected: [usize; 5], at: &str) -> Result<(), String> {
    let got = logical(graph);
    if got == expected {
        Ok(())
    } else {
        Err(format!(
            "{at}: logical counts {got:?}, expected {expected:?}"
        ))
    }
}

/// Mass-removal plan (M5, C2): `percent`% of the nodes (seeded) to remove, in
/// removal order, then as many fresh IDs (above every existing ID) to register,
/// with the expected logical counts after the removals and at the end.
pub struct MassPlan {
    /// Nodes to remove, in order.
    pub removed: Vec<u64>,
    /// Fresh IDs to register afterwards, in order.
    pub fresh: Vec<u64>,
    /// Logical counts after the removals.
    pub after_removal: [usize; 5],
    /// Logical counts at the end.
    pub at_end: [usize; 5],
}

/// Builds the [`MassPlan`] with an independent count of the surviving edges.
pub fn mass_plan(workload: &Workload, percent: u64, seed: u64) -> MassPlan {
    let count = (workload.ids.len() as u64 * percent / 100) as usize;
    let removed = sample(&workload.ids, count, &mut Rng(seed ^ MASS_SALT));
    let gone: rustc_hash::FxHashSet<u64> = removed.iter().copied().collect();
    let surviving = workload
        .edges
        .iter()
        .filter(|(a, b)| !gone.contains(a) && !gone.contains(b))
        .count();
    let top = workload.ids.iter().copied().max().map_or(0, |m| m + 1);
    let fresh: Vec<u64> = (top..top + count as u64).collect();
    let left = workload.ids.len() - count;
    let total = left + count;
    MassPlan {
        removed,
        fresh,
        after_removal: [left, surviving, left, surviving, surviving],
        at_end: [total, surviving, total, surviving, surviving],
    }
}

/// Digest of one page of incident edges: count, then each neighbor and flags.
pub fn page_digest(page: &[(u64, bool, bool)]) -> u64 {
    page.iter()
        .fold(fnv(FNV_START, page.len() as u64), |d, &(n, e, f)| {
            fnv(d, n ^ (u64::from(e) << 62) ^ (u64::from(f) << 63))
        })
}

/// Lower-median (as the other probes) and nearest-rank p99 of a sample.
pub fn median_p99(values: &[u64]) -> (u64, u64) {
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    if sorted.is_empty() {
        return (0, 0);
    }
    let median = sorted[(sorted.len() - 1) / 2];
    let rank = (sorted.len() * 99).div_ceil(100).max(1);
    (median, sorted[rank - 1])
}

/// Salt of the cursor draws (P2-P4).
const CURSOR_SALT: u64 = 0xc0a5_0151;

/// Cursor kinds of P2 and P3 (section 6.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CursorKind {
    /// A registered hub neighbor.
    Registered,
    /// A ghost: registered, linked to the hub, then removed before paging.
    Removed,
    /// An ID that is never registered.
    Never,
}

impl CursorKind {
    /// Output name.
    pub fn name(self) -> &'static str {
        match self {
            Self::Registered => "registered",
            Self::Removed => "removed",
            Self::Never => "never",
        }
    }
}

/// The P2/P3 cursor plan: `each` cursors of every kind, shuffled, and the
/// ghost IDs to register, link to the hub and remove before paging.
pub struct CursorPlan {
    /// Cursors in paging order.
    pub cursors: Vec<(CursorKind, u64)>,
    /// Ghost IDs (also the `Removed` cursors), ascending.
    pub ghosts: Vec<u64>,
    /// `/v1/edges` cursors `(after_source, after_target)` for P4: registered
    /// edges, pairs naming a removed (ghost) node as source or target, and
    /// pairs naming a never-registered ID, shuffled.
    pub edge_cursors: Vec<(CursorKind, u64, u64)>,
}

/// Builds the [`CursorPlan`] of a `hub-in-sparse` workload.
pub fn cursor_plan(workload: &Workload, each: usize, seed: u64) -> Result<CursorPlan, String> {
    let mut rng = Rng(seed ^ CURSOR_SALT);
    let (mut ghosts, never) = workload.cursor_ids(each, &mut rng)?;
    let leaves: Vec<u64> = workload.spokes().iter().map(|e| e.1).collect();
    let registered = sample(&leaves, each, &mut rng);
    let mut cursors: Vec<(CursorKind, u64)> = registered
        .iter()
        .map(|&v| (CursorKind::Registered, v))
        .chain(ghosts.iter().map(|&v| (CursorKind::Removed, v)))
        .chain(never.iter().map(|&v| (CursorKind::Never, v)))
        .collect();
    shuffle(&mut cursors, &mut rng);
    let edges = sample(&workload.edges, each, &mut rng);
    let mut edge_cursors: Vec<(CursorKind, u64, u64)> = edges
        .iter()
        .map(|&(a, b)| (CursorKind::Registered, a.min(b), a.max(b)))
        .collect();
    for (i, (&g, &x)) in ghosts.iter().zip(&never).enumerate() {
        let other = workload.ids[rng.below(workload.ids.len() as u64) as usize];
        if i % 2 == 0 {
            edge_cursors.push((CursorKind::Removed, g, other));
            edge_cursors.push((CursorKind::Never, x, other));
        } else {
            edge_cursors.push((CursorKind::Removed, other, g));
            edge_cursors.push((CursorKind::Never, other, x));
        }
    }
    shuffle(&mut edge_cursors, &mut rng);
    ghosts.sort_unstable();
    Ok(CursorPlan {
        cursors,
        ghosts,
        edge_cursors,
    })
}

/// Registers every ghost, links it to the hub, then removes it (the P2 and
/// P3 setup, untimed). Fails unless every call changes the graph.
pub fn ghost_setup(graph: &mut LifecycleGraph, hub: u64, ghosts: &[u64]) -> Result<(), String> {
    for &g in ghosts {
        if !graph.add_node(g).map_err(|e| e.to_string())?
            || !graph.link(hub, g).map_err(|e| e.to_string())?
        {
            return Err(format!("ghost {g} was already registered"));
        }
    }
    for &g in ghosts {
        if !graph.remove_node(g) {
            return Err(format!("ghost {g} could not be removed"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hub_in_sparse_has_distinct_ascending_spokes_and_spaced_ids() {
        let w = Workload::generate("hub-in-sparse", 2_000, 500, 7).unwrap();
        let hub = w.hub.unwrap();
        assert_eq!(hub, 8_000);
        assert_eq!(w.spokes().len(), 500);
        let leaves: Vec<u64> = w
            .spokes()
            .iter()
            .map(|&(h, l)| {
                assert_eq!(h, hub);
                l
            })
            .collect();
        assert!(leaves.windows(2).all(|p| p[0] < p[1]));
        assert!(w.ids.iter().all(|&v| v % 4 == 0));
        assert_eq!(w.ids.len(), 2_001);
        assert_eq!(w.base().len(), generate(Topology::Sparse, 2_000, 7).len());
        // D = N: every sparse node is a leaf.
        let full = Workload::generate("hub-in-sparse", 300, 300, 7).unwrap();
        assert_eq!(full.spokes().len(), 300);
    }

    #[test]
    fn workloads_are_deterministic_and_seed_sensitive() {
        let a = Workload::generate("hub-in-sparse", 1_000, 100, 3).unwrap();
        let b = Workload::generate("hub-in-sparse", 1_000, 100, 3).unwrap();
        let c = Workload::generate("hub-in-sparse", 1_000, 100, 4).unwrap();
        assert_eq!(a.fingerprint(), b.fingerprint());
        assert_ne!(a.fingerprint(), c.fingerprint());
        assert_eq!(scrambled_order(&a, 9), scrambled_order(&b, 9));
        assert_ne!(scrambled_order(&a, 9), a.ids);
    }

    #[test]
    fn star_matches_the_core_lifecycle_edge_set() {
        let w = Workload::generate("star", 0, 50, 1).unwrap();
        let mut mine = w.edges.clone();
        let mut theirs = star(50);
        mine.sort_unstable();
        theirs.sort_unstable();
        assert_eq!(mine, theirs);
        assert_eq!(w.spokes().len(), 50);
        assert!(w.spokes().iter().all(|&(h, _)| h == 0));
    }

    #[test]
    fn states_build_the_same_graph() {
        let w = Workload::generate("hub-in-sparse", 500, 200, 5).unwrap();
        for engine in [EngineConfig::CompactBfs, EngineConfig::ClusterForest] {
            let ordered = build_ordered(engine, &w).unwrap();
            let scrambled = build_scrambled(engine, &w, 5).unwrap();
            let incremental = build_incremental(engine, &w.ids, &incremental_edges(&w, 5)).unwrap();
            for graph in [&ordered, &scrambled, &incremental] {
                assert_eq!(logical(graph), w.expected());
                let hub: Vec<u64> = graph
                    .incident_after(w.hub.unwrap(), None)
                    .unwrap()
                    .map(|e| e.0)
                    .collect();
                let leaves: Vec<u64> = w.spokes().iter().map(|e| e.1).collect();
                assert_eq!(hub, leaves);
            }
        }
    }

    #[test]
    fn mass_plan_counts_match_the_graph() {
        let w = Workload::generate("sparse", 2_000, 0, 11).unwrap();
        let plan = mass_plan(&w, 60, 11);
        assert_eq!(plan.removed.len(), 1_200);
        let mut graph = build_ordered(EngineConfig::CompactBfs, &w).unwrap();
        for &v in &plan.removed {
            assert!(graph.remove_node(v));
        }
        assert_eq!(logical(&graph), plan.after_removal);
        for &v in &plan.fresh {
            assert!(graph.add_node(v).unwrap());
        }
        assert_eq!(logical(&graph), plan.at_end);
    }

    #[test]
    fn cursor_ids_are_unregistered_and_distinct() {
        let w = Workload::generate("hub-in-sparse", 1_000, 100, 2).unwrap();
        let (ghosts, never) = w.cursor_ids(100, &mut Rng(1)).unwrap();
        assert!(ghosts.iter().all(|g| g % 4 == 2));
        assert!(never.iter().all(|g| g % 2 == 1));
        let mut all = ghosts.clone();
        all.sort_unstable();
        all.dedup();
        assert_eq!(all.len(), 100);
    }

    #[test]
    fn median_and_p99_use_lower_median_and_nearest_rank() {
        let values: Vec<u64> = (1..=300).collect();
        assert_eq!(median_p99(&values), (150, 297));
        assert_eq!(median_p99(&[5]), (5, 5));
    }
}
