//! Shared CF5 graph generation (knotrel `docs/releases/v1.1.0-cf5-qualification-plan.md`).
//!
//! `cf5-core` (K2, K2x, K3) and `lifecycle-probes`' `memory-peak cf5-random`
//! (K4) both use these functions, so the K4 graphs and operation orders are
//! exactly the K2 ones; [`fingerprint`] lets a collector check it.

use std::collections::HashSet;

/// SplitMix64: deterministic and platform-independent.
#[derive(Debug, Clone)]
pub struct Rng(pub u64);

impl Rng {
    /// Next 64-bit value.
    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    /// A value in `0..bound` (slightly biased modulo; repeatable variation).
    pub fn below(&mut self, bound: u64) -> u64 {
        self.next_u64() % bound
    }
    /// Fisher–Yates shuffle.
    pub fn shuffle<T>(&mut self, items: &mut [T]) {
        for i in (1..items.len()).rev() {
            let j = self.below(i as u64 + 1) as usize;
            items.swap(i, j);
        }
    }
}

/// A seeded random simple graph on `0..vertices` with `degree · vertices / 2`
/// edges, in generation order.
///
/// # Errors
/// Rejects fewer than two vertices or a density above a quarter of all pairs
/// (rejection sampling would slow down sharply).
pub fn random_graph(vertices: u64, degree: u64, seed: u64) -> Result<Vec<(u64, u64)>, String> {
    let target = degree * vertices / 2;
    if vertices < 2 || target > vertices * (vertices - 1) / 4 {
        return Err("degree too high for a sparse random simple graph".into());
    }
    let mut rng = Rng(seed);
    let mut seen = HashSet::with_capacity(target as usize);
    let mut edges = Vec::with_capacity(target as usize);
    while (edges.len() as u64) < target {
        let (a, b) = (rng.below(vertices), rng.below(vertices));
        if a != b && seen.insert((a.min(b), a.max(b))) {
            edges.push((a, b));
        }
    }
    Ok(edges)
}

/// A generator state after drawing the orders, the insertion order and the
/// deletion order.
pub type Orders = (Rng, Vec<(u64, u64)>, Vec<(u64, u64)>);

/// The insertion and deletion orders of a cell, from `seed` and a
/// mode-specific salt (K2 and K4 share the salt [`STAGED_SALT`]).
#[must_use]
pub fn orders(edges: &[(u64, u64)], seed: u64, salt: u64) -> Orders {
    let mut rng = Rng(seed ^ salt);
    let mut insert = edges.to_vec();
    rng.shuffle(&mut insert);
    let mut delete = edges.to_vec();
    rng.shuffle(&mut delete);
    (rng, insert, delete)
}

/// Salt of the K2 staged orders, shared with K4.
pub const STAGED_SALT: u64 = 0x5AFE;
/// Salt of the K2x orders.
pub const ALL_SALT: u64 = 0xA11;

/// FNV-1a 64 fingerprint of an edge sequence (order-sensitive), as hex.
#[must_use]
pub fn fingerprint(edges: &[(u64, u64)]) -> String {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for &(a, b) in edges {
        for byte in a.to_le_bytes().into_iter().chain(b.to_le_bytes()) {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    format!("{hash:016x}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn graphs_are_simple_deterministic_and_sized() {
        let a = random_graph(1_000, 8, 3).unwrap();
        assert_eq!(a.len(), 4_000);
        assert_eq!(
            fingerprint(&a),
            fingerprint(&random_graph(1_000, 8, 3).unwrap())
        );
        let unique: HashSet<_> = a.iter().map(|&(x, y)| (x.min(y), x.max(y))).collect();
        assert_eq!(unique.len(), a.len());
        assert!(a.iter().all(|&(x, y)| x != y && x < 1_000 && y < 1_000));
        assert!(random_graph(10, 8, 1).is_err());
    }

    #[test]
    fn orders_are_permutations() {
        let edges = random_graph(200, 4, 9).unwrap();
        let (_, insert, delete) = orders(&edges, 9, STAGED_SALT);
        let mut sorted = edges.clone();
        sorted.sort_unstable();
        for order in [insert, delete] {
            let mut copy = order.clone();
            copy.sort_unstable();
            assert_eq!(copy, sorted);
        }
    }
}
