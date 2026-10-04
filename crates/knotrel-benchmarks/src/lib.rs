//! Reproducible workloads for exact connectivity benchmarks.
//!
//! The chain workload derives expected answers from topology, independently of
//! the engine being measured. This crate contains no GraphScope adapter yet.

use serde::{Deserialize, Serialize};

pub mod engines;
mod traces;
pub use traces::{WorkloadKind, generate, generate_with_query_percent};

/// A deterministic workload configuration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Config {
    /// Number of vertices.
    pub nodes: u64,
    /// Number of workload cycles; sustained families use 100 operations per cycle.
    pub rounds: usize,
    /// Deterministic generator seed.
    pub seed: u64,
}

/// An operation with independently known query results.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Operation {
    /// Insert an edge.
    Link {
        /// First endpoint.
        source: u64,
        /// Second endpoint.
        target: u64,
    },
    /// Delete an edge.
    Cut {
        /// First endpoint.
        source: u64,
        /// Second endpoint.
        target: u64,
    },
    /// Query connectivity.
    Connected {
        /// First endpoint.
        source: u64,
        /// Second endpoint.
        target: u64,
        /// Independently known answer.
        expected: bool,
    },
}

/// A deterministic initial graph and operation trace.
#[derive(Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Workload {
    /// Initial undirected edges; vertices are `0..config.nodes`.
    pub initial_edges: Vec<(u64, u64)>,
    /// Operations in execution order.
    pub operations: Vec<Operation>,
}

/// Creates a deterministic chain split/rejoin workload.
///
/// The initial graph is a path through `0, 1, ..., nodes-1`. Each round removes one
/// seeded edge, queries the endpoints of the path (false), restores the edge,
/// and queries again (true). All deletions are bridges. This deliberately
/// measures a narrow case; it is not a representative production distribution.
///
/// Construction takes O(nodes + rounds) time and space. A wrapping 64-bit LCG
/// fixes the trace across platforms; modulo selection is slightly biased and
/// is intended for repeatable variation, not cryptography or unbiased sampling.
///
/// # Errors
/// Rejects fewer than two nodes, zero rounds, sizes that overflow addressable
/// allocations, or a failed allocation for the complete trace.
pub fn chain_workload(config: Config) -> Result<Workload, &'static str> {
    if config.nodes < 2 {
        return Err("nodes must be at least 2");
    }
    if config.rounds == 0 {
        return Err("rounds must be at least 1");
    }
    let edge_count = usize::try_from(config.nodes - 1).map_err(|_| "too many nodes")?;
    let operation_count = config.rounds.checked_mul(4).ok_or("too many rounds")?;
    let mut initial_edges = Vec::new();
    initial_edges
        .try_reserve_exact(edge_count)
        .map_err(|_| "cannot allocate initial graph")?;
    let mut operations = Vec::new();
    operations
        .try_reserve_exact(operation_count)
        .map_err(|_| "cannot allocate operation trace")?;
    for source in 0..config.nodes - 1 {
        initial_edges.push((source, source + 1));
    }
    let mut seed = config.seed;
    for _ in 0..config.rounds {
        seed = seed
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let source = seed % (config.nodes - 1);
        let target = source + 1;
        // Removing any path edge separates its endpoints into two components.
        // Restoring that exact edge restores the path invariant for the next round.
        operations.extend([
            Operation::Cut { source, target },
            Operation::Connected {
                source: 0,
                target: config.nodes - 1,
                expected: false,
            },
            Operation::Link { source, target },
            Operation::Connected {
                source: 0,
                target: config.nodes - 1,
                expected: true,
            },
        ]);
    }
    Ok(Workload {
        initial_edges,
        operations,
    })
}

mod ett_baseline;

/// Frozen HDT v2 implementation for controlled comparisons.
pub mod hdt_baseline;
