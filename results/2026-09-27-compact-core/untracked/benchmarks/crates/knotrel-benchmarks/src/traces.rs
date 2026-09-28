//! Small topology-derived traces, independent of any measured engine.

use crate::{Config, Operation, Workload, chain_workload};

/// Versioned synthetic workload families; names fix the generation contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkloadKind {
    /// Path bridge deletions, preserving the original v1 sequence.
    Chain,
    /// Ring edges: redundant deletion followed by an actual split.
    Cycle,
    /// Two paths repeatedly joined by a bridge and separated.
    Components,
    /// Star with a path among leaves; isolate and restore a leaf.
    Hub,
}

impl WorkloadKind {
    /// Returns the stable trace family identifier.
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Chain => "chain-split-rejoin-v1",
            Self::Cycle => "cycle-alternatives-v1",
            Self::Components => "components-join-split-v1",
            Self::Hub => "hub-alternatives-v1",
        }
    }

    /// Resolves a versioned workload name.
    ///
    /// # Errors
    /// Rejects unknown names rather than silently selecting another workload.
    pub fn parse(name: &str) -> Result<Self, &'static str> {
        [Self::Chain, Self::Cycle, Self::Components, Self::Hub]
            .into_iter()
            .find(|kind| kind.name() == name)
            .ok_or("unknown workload")
    }
}

/// Builds a reusable trace whose answers follow from topology.
///
/// Chain preserves [`chain_workload`]. Other families require at least six
/// vertices. Each round restores its initial graph, so all updates change state.
/// Cycle removes both edges incident to a seeded vertex: one deletion retains
/// a spanning path, two isolate that vertex. Hub removes a seeded leaf's spoke
/// and its one or two leaf-path edges; only the final cut isolates the leaf.
/// Components starts with two paths and toggles a single cross-component bridge.
/// Each mutation is followed by a query, yielding 50% queries in every family.
///
/// Generation uses O(nodes + rounds) worst-case time and space. Selection uses
/// the same wrapping LCG as the chain; modulo selection is biased. These are
/// structured sparse stress cases, not samples from a production distribution.
///
/// # Errors
/// Rejects invalid sizes, arithmetic overflow and failed trace allocations.
pub fn generate(kind: WorkloadKind, config: Config) -> Result<Workload, &'static str> {
    if kind == WorkloadKind::Chain {
        return chain_workload(config);
    }
    if config.nodes < 6 || config.rounds == 0 {
        return Err("new workloads need nodes >= 6 and rounds >= 1");
    }
    let n = usize::try_from(config.nodes).map_err(|_| "too many nodes")?;
    let mut trace = Workload {
        initial_edges: Vec::new(),
        operations: Vec::new(),
    };
    trace
        .initial_edges
        .try_reserve_exact(n.checked_mul(2).ok_or("too many nodes")?)
        .map_err(|_| "cannot allocate initial graph")?;
    trace
        .operations
        .try_reserve_exact(config.rounds.checked_mul(12).ok_or("too many rounds")?)
        .map_err(|_| "cannot allocate operation trace")?;
    let split = config.nodes / 2;
    match kind {
        WorkloadKind::Cycle => {
            for v in 0..config.nodes {
                trace.initial_edges.push((v, (v + 1) % config.nodes));
            }
        }
        WorkloadKind::Components => {
            for v in 0..config.nodes - 1 {
                if v + 1 != split {
                    trace.initial_edges.push((v, v + 1));
                }
            }
        }
        WorkloadKind::Hub => {
            for v in 1..config.nodes {
                trace.initial_edges.push((0, v));
            }
            for v in 1..config.nodes - 1 {
                trace.initial_edges.push((v, v + 1));
            }
        }
        WorkloadKind::Chain => unreachable!(),
    }
    let mut seed = config.seed;
    for _ in 0..config.rounds {
        seed = seed
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        match kind {
            WorkloadKind::Components => {
                let a = seed % split;
                let b = split + seed.rotate_left(32) % (config.nodes - split);
                trace.operations.extend([
                    Operation::Link {
                        source: a,
                        target: b,
                    },
                    query(0, config.nodes - 1, true),
                    Operation::Cut {
                        source: a,
                        target: b,
                    },
                    query(0, config.nodes - 1, false),
                ]);
            }
            WorkloadKind::Cycle | WorkloadKind::Hub => {
                let v = if kind == WorkloadKind::Cycle {
                    seed % config.nodes
                } else {
                    1 + seed % (config.nodes - 1)
                };
                // At most three incident edges; stack storage avoids per-round
                // allocation. Other vertices remain connected after isolation.
                let mut neighbors = [0; 3];
                let count = if kind == WorkloadKind::Cycle {
                    neighbors[0] = (v + config.nodes - 1) % config.nodes;
                    neighbors[1] = (v + 1) % config.nodes;
                    2
                } else {
                    let mut count = 1; // The spoke (v, 0).
                    if v > 1 {
                        neighbors[count] = v - 1;
                        count += 1;
                    }
                    if v + 1 < config.nodes {
                        neighbors[count] = v + 1;
                        count += 1;
                    }
                    count
                };
                let target = if kind == WorkloadKind::Cycle {
                    (v + config.nodes / 2) % config.nodes
                } else {
                    0
                };
                for (i, &neighbor) in neighbors[..count].iter().enumerate() {
                    trace.operations.push(Operation::Cut {
                        source: v,
                        target: neighbor,
                    });
                    trace.operations.push(if kind == WorkloadKind::Hub {
                        query(0, v, i + 1 < count)
                    } else {
                        query(v, target, i + 1 < count)
                    });
                }
                for &neighbor in neighbors[..count].iter().rev() {
                    trace.operations.push(Operation::Link {
                        source: v,
                        target: neighbor,
                    });
                    trace.operations.push(if kind == WorkloadKind::Hub {
                        query(0, v, true)
                    } else {
                        query(v, target, true)
                    });
                }
            }
            WorkloadKind::Chain => unreachable!(),
        }
    }
    Ok(trace)
}

fn query(source: u64, target: u64, expected: bool) -> Operation {
    Operation::Connected {
        source,
        target,
        expected,
    }
}
