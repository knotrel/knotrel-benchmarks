//! Churn schedules for the sustained-resource experiment (C) and the memory
//! diagnostics, shared by `core-lifecycle` and `memory-peak` so both replay
//! exactly the same operations. Moved unchanged from `core-lifecycle.rs`
//! (probes `444806d3`/`f1d099cc`); only visibility and documentation changed,
//! plus `Model::effective`, previously a copy in `memory-peak.rs`.

use crate::{Op, Rng};
use rustc_hash::{FxHashMap, FxHashSet};

/// Independent model of registered topology and flags for expected counts.
#[derive(Default)]
pub struct Model {
    /// Registered nodes and their active flags.
    pub active: FxHashMap<u64, bool>,
    /// Registered edges (normalized endpoints) and their enabled flags.
    pub edges: FxHashMap<(u64, u64), bool>,
    /// Registered neighbors of every node.
    pub adjacency: FxHashMap<u64, FxHashSet<u64>>,
}

/// Normalized key of an undirected edge.
pub fn key(a: u64, b: u64) -> (u64, u64) {
    (a.min(b), a.max(b))
}

impl Model {
    /// Applies one churn operation with the facade's semantics.
    pub fn apply(&mut self, op: Op) {
        match op {
            Op::AddNode(v) => {
                if let std::collections::hash_map::Entry::Vacant(entry) = self.active.entry(v) {
                    entry.insert(true);
                    self.adjacency.insert(v, FxHashSet::default());
                }
            }
            Op::Link(a, b) => {
                if a == b || self.edges.contains_key(&key(a, b)) {
                    return;
                }
                self.apply(Op::AddNode(a));
                self.apply(Op::AddNode(b));
                self.edges.insert(key(a, b), true);
                self.adjacency.get_mut(&a).unwrap().insert(b);
                self.adjacency.get_mut(&b).unwrap().insert(a);
            }
            Op::Remove(v) => {
                if self.active.remove(&v).is_none() {
                    return;
                }
                for w in self.adjacency.remove(&v).unwrap() {
                    self.edges.remove(&key(v, w));
                    self.adjacency.get_mut(&w).unwrap().remove(&v);
                }
            }
            Op::SetNode(v, f) => {
                if let Some(flag) = self.active.get_mut(&v) {
                    *flag = f;
                }
            }
            Op::SetEdge(a, b, f) => {
                if let Some(flag) = self.edges.get_mut(&key(a, b)) {
                    *flag = f;
                }
            }
            Op::Cut(..) | Op::Connected(..) => unreachable!("not used by churn schedules"),
        }
    }

    /// `[nodes, edges, active nodes, enabled edges, effective edges]`.
    pub fn counts(&self) -> [usize; 5] {
        let effective = self
            .edges
            .iter()
            .filter(|&(&(a, b), &enabled)| enabled && self.active[&a] && self.active[&b])
            .count();
        [
            self.active.len(),
            self.edges.len(),
            self.active.values().filter(|&&a| a).count(),
            self.edges.values().filter(|&&e| e).count(),
            effective,
        ]
    }

    /// Whether `{a, b}` is registered, enabled and has two active endpoints.
    pub fn effective(&self, a: u64, b: u64) -> bool {
        self.edges.get(&key(a, b)).copied().unwrap_or(false)
            && self.active.get(&a).copied().unwrap_or(false)
            && self.active.get(&b).copied().unwrap_or(false)
    }
}

/// Operations per cycle, and expected counts after construction and every cycle.
pub type Schedule = (Vec<Vec<Op>>, Vec<[usize; 5]>);

/// Builds the churn schedule (operations per cycle) and the expected counts
/// after construction and after every cycle. Every scheduled operation is
/// applied to the model as it is scheduled.
///
/// Each cycle touches `percent`% of the live IDs:
/// - `fresh`: remove, register a never-used ID, link it to `relink` live IDs;
/// - `same`: remove, re-register the same ID, link it to `relink` live IDs;
/// - `toggle`: first restore the previous cycle's picks (reactivate, re-enable
///   the edge disabled for them), then deactivate new active picks and
///   disable one enabled incident edge of each. About `percent`% of the nodes
///   therefore stay inactive across checkpoints, with as many edges disabled.
pub fn schedule(
    n: u64,
    edges: &[(u64, u64)],
    reuse: &str,
    cycles: usize,
    percent: u64,
    seed: u64,
) -> Result<Schedule, String> {
    let mut model = Model::default();
    (0..n).for_each(|v| model.apply(Op::AddNode(v)));
    edges.iter().for_each(|&(a, b)| model.apply(Op::Link(a, b)));
    let relink = (2 * edges.len() as u64 / n.max(1)).max(1);
    let mut expected = vec![model.counts()];
    let mut plan = Vec::with_capacity(cycles);
    let mut rng = Rng(seed ^ 0xc0ffee);
    let mut live: Vec<u64> = (0..n).collect();
    let mut next_id = n;
    let mut previous: Vec<(u64, Option<u64>)> = Vec::new();
    for _ in 0..cycles {
        let mut ops = Vec::new();
        let mut push = |op: Op, model: &mut Model| {
            model.apply(op);
            ops.push(op);
        };
        if reuse == "toggle" {
            for (v, w) in previous.drain(..) {
                push(Op::SetNode(v, true), &mut model);
                if let Some(w) = w {
                    push(Op::SetEdge(v, w, true), &mut model);
                }
            }
        }
        let picks = (live.len() as u64 * percent / 100).max(1);
        for _ in 0..picks {
            let index = rng.below(live.len() as u64) as usize;
            let v = live[index];
            match reuse {
                "fresh" | "same" => {
                    push(Op::Remove(v), &mut model);
                    let id = if reuse == "fresh" {
                        let id = next_id;
                        next_id += 1;
                        id
                    } else {
                        v
                    };
                    live[index] = id;
                    push(Op::AddNode(id), &mut model);
                    for _ in 0..relink {
                        let w = live[rng.below(live.len() as u64) as usize];
                        push(Op::Link(id, w), &mut model);
                    }
                }
                "toggle" => {
                    if !model.active[&v] {
                        continue;
                    }
                    let enabled: Vec<u64> = model.adjacency[&v]
                        .iter()
                        .copied()
                        .filter(|&w| model.edges[&key(v, w)])
                        .collect();
                    let w = (!enabled.is_empty())
                        .then(|| enabled[rng.below(enabled.len() as u64) as usize]);
                    push(Op::SetNode(v, false), &mut model);
                    if let Some(w) = w {
                        push(Op::SetEdge(v, w, false), &mut model);
                    }
                    previous.push((v, w));
                }
                _ => return Err("unknown --reuse".into()),
            }
        }
        expected.push(model.counts());
        plan.push(ops);
    }
    Ok((plan, expected))
}
