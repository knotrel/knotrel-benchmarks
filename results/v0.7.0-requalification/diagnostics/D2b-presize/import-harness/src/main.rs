//! D2b diagnostic (DIAGNOSTICS-PLAN-2.md): import cost of component pre-sizing policies.
//! Not part of the qualification.
//!
//! Bulk import `LifecycleGraph::try_from_topology` of the C3/B5 graph (sparse, all active,
//! `--nodes`, `--seed`), with the `diag_d2b` policy applied at the end of the import (the
//! diagnostic build `d2b-core.diff`). Default build: import time, each variant paired with
//! frozen in alternating order. `count` feature: net heap retained by the imported graph.
//!
//! ```text
//! d2b-import --nodes 100000 --seed 5000001 --pairs 24 --warmup 2
//! ```

use knotrel_core::{EdgeSpec, EngineConfig, GraphLimits, LifecycleGraph, NodeSpec, diag_d2b};
use lifecycle_probes::{Topology, generate};
use serde_json::json;
use std::{collections::HashMap, time::Instant};

#[cfg(feature = "count")]
#[global_allocator]
static GLOBAL: &stats_alloc::StatsAlloc<std::alloc::System> = &stats_alloc::INSTRUMENTED_SYSTEM;

#[cfg(not(feature = "count"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

const VARIANTS: [(&str, [f64; 3]); 8] = [
    ("frozen", [0.0, 0.0, 0.0]), ("cat", [2.0, 0.0, 0.0]), ("ids", [0.0, 2.0, 0.0]),
    ("hdr-1.25", [0.0, 0.0, 1.25]), ("hdr-1.5", [0.0, 0.0, 1.5]), ("hdr-2", [0.0, 0.0, 2.0]),
    ("eng", [0.0, 2.0, 2.0]), ("full", [2.0, 2.0, 2.0]),
];

fn import(nodes: &[NodeSpec], edges: &[EdgeSpec], f: [f64; 3]) -> LifecycleGraph {
    diag_d2b::set(f[0], f[1], f[2]);
    LifecycleGraph::try_from_topology(EngineConfig::CompactBfs, GraphLimits::default(), nodes, edges).unwrap()
}

fn main() {
    let mut args = HashMap::new();
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        args.insert(k.trim_start_matches("--").to_owned(), it.next().unwrap_or_default());
    }
    let num = |k: &str| args.get(k).unwrap_or_else(|| panic!("--{k}")).parse::<u64>().unwrap();
    let (n, seed) = (num("nodes"), num("seed"));
    let edges: Vec<EdgeSpec> = generate(Topology::Sparse, n, seed)
        .into_iter().map(|(source, target)| EdgeSpec { source, target, enabled: true }).collect();
    let nodes: Vec<NodeSpec> = (0..n).map(|node| NodeSpec { node, active: true }).collect();
    #[cfg(feature = "count")]
    {
        for (name, f) in VARIANTS {
            let before = GLOBAL.stats();
            let graph = import(&nodes, &edges, f);
            let after = GLOBAL.stats();
            let net = (after.bytes_allocated as i64 - after.bytes_deallocated as i64)
                - (before.bytes_allocated as i64 - before.bytes_deallocated as i64);
            println!("{}", json!({"kind":"heap","variant":name,"net_heap_bytes":net,"nodes":graph.node_count(),"edges":graph.edge_count()}));
        }
    }
    #[cfg(not(feature = "count"))]
    {
        let (pairs, warmup) = (num("pairs"), num("warmup"));
        for (name, f) in VARIANTS.into_iter().skip(1) {
            for i in 0..(warmup + pairs) {
                let order = if i % 2 == 0 { [("frozen", [0.0; 3]), (name, f)] } else { [(name, f), ("frozen", [0.0; 3])] };
                let mut row = serde_json::Map::new();
                for (arm, factors) in order {
                    let start = Instant::now();
                    let graph = import(&nodes, &edges, factors);
                    let ns = start.elapsed().as_nanos() as u64;
                    drop(graph);
                    row.insert(if arm == "frozen" { "frozen".into() } else { "variant".into() }, json!(ns));
                }
                println!("{}", json!({"kind":"pair","variant":name,"index":i,"warmup":i < warmup,"ns":row}));
            }
        }
    }
}
