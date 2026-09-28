//! Small topology-derived traces, independent of any measured engine.

use std::collections::BTreeSet;

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
    /// Path edges toggle continuously, with interval-derived answers.
    SustainedPath,
    /// Connected cycle blocks with continuously toggled backbone bridges.
    SustainedBlocks,
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
            Self::SustainedPath => "sustained-churn-path-v1",
            Self::SustainedBlocks => "sustained-churn-blocks-v1",
        }
    }

    /// Whether rounds represent 100-operation sustained churn cycles.
    #[must_use]
    pub fn is_sustained(self) -> bool {
        matches!(self, Self::SustainedPath | Self::SustainedBlocks)
    }

    /// Resolves a versioned workload name.
    ///
    /// # Errors
    /// Rejects unknown names rather than silently selecting another workload.
    pub fn parse(name: &str) -> Result<Self, &'static str> {
        [
            Self::Chain,
            Self::Cycle,
            Self::Components,
            Self::Hub,
            Self::SustainedPath,
            Self::SustainedBlocks,
        ]
        .into_iter()
        .find(|kind| kind.name() == name)
        .ok_or("unknown workload")
    }
}

/// Builds a reusable trace whose answers follow from topology.
///
/// Chain preserves [`chain_workload`]. Sustained families delegate to
/// [`generate_with_query_percent`] with 50% queries and retain state across
/// rounds. The remaining families require at least six vertices and restore
/// their initial graph each round, so all updates change state.
/// Cycle removes both edges incident to a seeded vertex: one deletion retains
/// a spanning path, two isolate that vertex. Hub removes a seeded leaf's spoke
/// and its one or two leaf-path edges; only the final cut isolates the leaf.
/// Components starts with two paths and toggles a single cross-component bridge.
/// Historical families follow each mutation with one query.
///
/// Historical generation uses O(nodes + rounds) worst-case time and space. Selection uses
/// the same wrapping LCG as the chain; modulo selection is biased. These are
/// structured sparse stress cases, not samples from a production distribution.
///
/// # Errors
/// Rejects invalid sizes, arithmetic overflow and failed trace allocations.
pub fn generate(kind: WorkloadKind, config: Config) -> Result<Workload, &'static str> {
    if kind.is_sustained() {
        return generate_with_query_percent(kind, config, 50);
    }
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
        WorkloadKind::Chain | WorkloadKind::SustainedPath | WorkloadKind::SustainedBlocks => {
            unreachable!()
        }
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
            WorkloadKind::Chain | WorkloadKind::SustainedPath | WorkloadKind::SustainedBlocks => {
                unreachable!()
            }
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

/// Generates sustained churn with exactly `query_percent` queries per 100
/// operations. Historical families accept only 50 and preserve their v1 traces.
///
/// Sustained path toggles seeded path edges. Blocks comprise up to 16 vertices
/// each (at least three in a cycle), connected by single backbone bridges. A
/// cycle has at most one absent edge; toggling cycle edges therefore preserves
/// internal connectivity while exercising redundant/tree-edge deletion. Small
/// trailing blocks retain their fixed internal path. Bridge and cycle updates
/// alternate when cycles exist. State persists across every round boundary.
/// Queries choose arbitrary vertices; a sorted set of absent path/bridge
/// boundaries supplies independent answers without graph traversal.
///
/// Generation takes O(nodes + operations * log(nodes)) time and
/// O(nodes + operations) space. Seeded modulo selection is biased, reproducible,
/// and intended for structured stress testing rather than production modelling.
///
/// # Errors
/// Rejects query percentages outside 1..=99, non-50 percentages for historical
/// families, fewer than two nodes, zero rounds, overflow or failed allocations.
pub fn generate_with_query_percent(
    kind: WorkloadKind,
    config: Config,
    query_percent: u8,
) -> Result<Workload, &'static str> {
    if !(1..=99).contains(&query_percent) {
        return Err("query percent must be between 1 and 99");
    }
    if !kind.is_sustained() {
        if query_percent != 50 {
            return Err("query percent is configurable only for sustained workloads");
        }
        return generate(kind, config);
    }
    if config.nodes < 2 || config.rounds == 0 {
        return Err("sustained workloads need nodes >= 2 and rounds >= 1");
    }
    let n = usize::try_from(config.nodes).map_err(|_| "too many nodes")?;
    let count = config.rounds.checked_mul(100).ok_or("too many rounds")?;
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
        .try_reserve_exact(count)
        .map_err(|_| "cannot allocate operation trace")?;
    let block_size = if kind == WorkloadKind::SustainedPath || config.nodes < 3 {
        1
    } else {
        16
    };
    let blocks = config.nodes.div_ceil(block_size);
    for v in 0..config.nodes - 1 {
        trace.initial_edges.push((v, v + 1));
    }
    let cycle_blocks = if block_size == 1 {
        0
    } else {
        config.nodes / block_size + u64::from(config.nodes % block_size >= 3)
    };
    for block in 0..cycle_blocks {
        let start = block * block_size;
        let end = (start + block_size).min(config.nodes);
        trace.initial_edges.push((start, end - 1));
    }
    let mut gaps = vec![None; usize::try_from(cycle_blocks).map_err(|_| "too many blocks")?];
    let mut absent = BTreeSet::new();
    let mut seed = config.seed;
    let mut updates = 0_usize;
    for index in 0..count {
        let slot = index % 100;
        if (slot + 1) * usize::from(query_percent) / 100 > slot * usize::from(query_percent) / 100 {
            let source = next_random(&mut seed) % config.nodes;
            let target = next_random(&mut seed) % config.nodes;
            let a = source.min(target) / block_size;
            let b = source.max(target) / block_size;
            trace
                .operations
                .push(query(source, target, absent.range(a..b).next().is_none()));
        } else {
            let internal = cycle_blocks > 0 && (blocks == 1 || updates % 2 == 1);
            let (source, target, insert) = if internal {
                let block = next_random(&mut seed) % cycle_blocks;
                let start = block * block_size;
                let end = (start + block_size).min(config.nodes);
                let gap = &mut gaps[block as usize];
                if let Some(edge) = gap.take() {
                    (edge, if edge + 1 == end { start } else { edge + 1 }, true)
                } else {
                    let edge = start + next_random(&mut seed) % (end - start);
                    *gap = Some(edge);
                    (edge, if edge + 1 == end { start } else { edge + 1 }, false)
                }
            } else {
                let boundary = next_random(&mut seed) % (blocks - 1);
                let insert = !absent.insert(boundary);
                if insert {
                    absent.remove(&boundary);
                }
                let source = (boundary + 1) * block_size - 1;
                (source, source + 1, insert)
            };
            trace.operations.push(if insert {
                Operation::Link { source, target }
            } else {
                Operation::Cut { source, target }
            });
            updates += 1;
        }
    }
    Ok(trace)
}

fn next_random(seed: &mut u64) -> u64 {
    *seed = seed
        .wrapping_mul(6364136223846793005)
        .wrapping_add(1442695040888963407);
    // High bits avoid short low-bit cycles for power-of-two graph sizes.
    seed.rotate_left(29)
}
