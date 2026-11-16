//! Allocation-level regression for engine incidence-set release.
//!
//! Run with `cargo test --release --features count-alloc`. Without the
//! feature this file compiles to nothing (it needs the counting allocator).
//!
//! Each engine keeps one ordered incidence set per vertex. Before the fix, a
//! set emptied by removals kept its B-tree leaf, so live heap grew with the
//! number of vertices that had ever held an incidence. The test gives the
//! non-tree incidence to one vertex subset at a time: after warming up on
//! subset A, a pass over the disjoint subset B must not add a leaf's worth of
//! heap per vertex. Allocation sizes are deterministic, so the bound has no
//! noise term; it allows any hash-table resize (which cannot recur after the
//! warm-up at the same item count) and fails at one retained leaf per
//! eight vertices of B.
#![cfg(feature = "count-alloc")]

use knotrel_core::{ForestGraph, HdtGraph};
use stats_alloc::{INSTRUMENTED_SYSTEM, Region, StatsAlloc};
use std::alloc::System;

#[global_allocator]
static GLOBAL: &StatsAlloc<System> = &INSTRUMENTED_SYSTEM;

const N: u64 = 4_096;
/// Smallest retained B-tree leaf for `usize` keys on 64-bit targets.
const LEAF_BYTES: i64 = 104;

fn net(region: &Region<System>) -> i64 {
    let stats = region.change();
    // `bytes_allocated`/`bytes_deallocated` already include reallocation
    // growth and shrinkage.
    stats.bytes_allocated as i64 - stats.bytes_deallocated as i64
}

/// One pass: for each vertex v of the subset, add the chord (v, v + 2) on
/// the path, which is a non-tree edge, then remove it. Exactly one chord is
/// present at a time.
fn pass(
    link: &mut dyn FnMut(u64, u64),
    cut: &mut dyn FnMut(u64, u64),
    subset: impl Iterator<Item = u64>,
) {
    for v in subset {
        link(v, v + 2);
        cut(v, v + 2);
    }
}

fn check(name: &str, link: &mut dyn FnMut(u64, u64), cut: &mut dyn FnMut(u64, u64)) {
    for v in 0..N - 1 {
        link(v, v + 1);
    }
    let half = (N - 2) / 2;
    pass(link, cut, 0..half); // warm-up on subset A
    let region = Region::new(GLOBAL);
    pass(link, cut, 0..half);
    let after_a = net(&region);
    pass(link, cut, half..2 * half); // disjoint subset B
    let growth_b = net(&region) - after_a;
    let bound = half as i64 * LEAF_BYTES / 8;
    assert!(
        growth_b < bound,
        "{name}: live heap grew by {growth_b} bytes over {half} fresh vertices (bound {bound})"
    );
}

#[test]
fn emptied_incidence_sets_release_their_storage() {
    let mut forest = ForestGraph::new();
    let forest = std::cell::RefCell::new(&mut forest);
    check(
        "ForestGraph",
        &mut |a, b| assert!(forest.borrow_mut().link(a, b).unwrap()),
        &mut |a, b| assert!(forest.borrow_mut().cut(a, b).unwrap()),
    );
    let mut hdt = HdtGraph::new();
    let hdt = std::cell::RefCell::new(&mut hdt);
    check(
        "HdtGraph",
        &mut |a, b| assert!(hdt.borrow_mut().link(a, b).unwrap()),
        &mut |a, b| assert!(hdt.borrow_mut().cut(a, b).unwrap()),
    );
}
