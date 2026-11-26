//! Timed core cells of the knotrel#151 comparison (compact internal node
//! indices; knotrel `docs/design/compact-node-index.md`, section 6.4).
//!
//! Built once against each arm (base and candidate) from the same source, the
//! method of `release-cells`; the runner executes the two binaries in fresh
//! processes, one observation per process. Inputs come from
//! [`lifecycle_probes::compact`]; every graph is built untimed.
//!
//! ```text
//! compact-cells build  --workload W --nodes N [--degree D] --engine E --seed S --reps R
//! compact-cells window --workload W --nodes N [--degree D] --engine E --seed S
//!     --state ordered|scrambled --op link|cut|enable|disable|remove
//!     --pool spokes|edges|nodes --k K --reps R
//! compact-cells degree-remove --degree D --engine E --k K --reps R
//! compact-cells traverse --workload hub-in-sparse --nodes N --degree D --engine E
//!     --seed S --state ordered|scrambled --k K --reps R
//! compact-cells pages --workload hub-in-sparse --nodes N --degree D --engine E
//!     --seed S --state ordered|scrambled --cursors C
//! compact-cells mass-churn --workload W --nodes N --engine E --seed S --percent P
//! compact-cells emit --workload hub-in-sparse --nodes N --degree D --seed S --cursors C
//! ```
//!
//! - `build` (I1): incremental build in seeded random edge order (hub spokes
//!   last, ascending leaf); `observation_ns`: median of `R` builds.
//! - `window` (I2, I3, R1, R2, R3, R5): each of `R` repetitions draws `K`
//!   distinct targets from the pool (hub spokes, non-spoke edges, or non-hub
//!   nodes) and times one window of `K` calls; untimed preparation and restore
//!   keep the graph's registered topology unchanged between windows:
//!   `link` (targets cut before), `cut` (relinked after), `enable` (disabled
//!   before), `disable` (enabled after), `remove` (re-registered and relinked
//!   after; incident lists read before). Every timed call must report a change.
//!   `observation_ns`: median window time.
//! - `degree-remove` (R4): star of degree `D` (ordered); a window is `K`
//!   cycles of: remove the center, re-register it, re-link every leaf.
//!   `observation_ns`: median window; `per_cycle_ns = observation_ns / K`.
//! - `traverse` (P1): a window is `K` full traversals of the hub with
//!   `incident_after` in pages of 1000 into a preallocated buffer;
//!   `observation_ns`: median window. Page digests are computed after timing.
//! - `pages` (P2): ghosts set up (registered, linked to the hub, removed),
//!   then one page (limit 1000) at each of `3 C` shuffled cursors (registered
//!   neighbors, removed ghosts, never-registered IDs), each timed alone;
//!   `median_page_ns`, `p99_page_ns` (nearest rank).
//! - `mass-churn` (C2): ordered build, remove `P`% of the nodes (seeded), then
//!   register as many fresh IDs, each call timed; `observation_ns` = summed
//!   call time, `slowest_op_ns`.
//! - `emit`: the P3/P4 HTTP input for `scripts/http_pages_151.py`: one JSON
//!   header line (fingerprint, hub, cursor plan), then one `B COUNT BODY`
//!   line per `POST /v1/batch` request of at most 1024 operations: `add_node`
//!   in the scrambled order, every `link`, each ghost's `add_node` and `link`
//!   to the hub, then (in separate requests) every ghost's `remove_node`.
//!
//! Every observation prints one JSON object whose `gate` field holds what the
//! arms must agree on (input fingerprint, logical counts, storage entry counts
//! and, for P cells, page digests). Any failed check exits non-zero.

use knotrel_core::{EngineConfig, LifecycleGraph};
use lifecycle_probes::compact::{
    self, CursorKind, FNV_START, Workload, build_incremental, build_ordered, build_state,
    check_logical, cursor_plan, fnv, gate, ghost_setup, incremental_edges, logical, mass_plan,
    median_p99, page_digest, sample, storage_capacities,
};
use lifecycle_probes::{Rng, build_record, parse_engine, rss_bytes};
use serde_json::{Value, json};
use std::io::Write as _;
use std::{collections::HashMap, process::ExitCode, time::Instant};

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

/// Page size of every pagination cell.
const PAGE: usize = 1000;
/// Operations per `POST /v1/batch` request (the server's maximum).
const BATCH: usize = 1024;
/// Salt of the window target draws.
const TARGET_SALT: u64 = 0x7a46_0151;

struct Args(HashMap<String, String>);

impl Args {
    fn parse(items: impl Iterator<Item = String>) -> Result<Self, String> {
        let mut map = HashMap::new();
        let mut items = items;
        while let Some(flag) = items.next() {
            let key = flag
                .strip_prefix("--")
                .ok_or("flags must start with --")?
                .to_owned();
            map.insert(key, items.next().ok_or("missing value")?);
        }
        Ok(Self(map))
    }
    fn get(&self, key: &str) -> Result<&str, String> {
        self.0
            .get(key)
            .map(String::as_str)
            .ok_or_else(|| format!("--{key} is required"))
    }
    fn num<T: std::str::FromStr>(&self, key: &str) -> Result<T, String> {
        self.get(key)?
            .parse()
            .map_err(|_| format!("--{key} is invalid"))
    }
    fn num_or<T: std::str::FromStr>(&self, key: &str, default: T) -> Result<T, String> {
        if self.0.contains_key(key) {
            self.num(key)
        } else {
            Ok(default)
        }
    }
}

fn engine(args: &Args) -> Result<EngineConfig, String> {
    let name = args.get("engine")?;
    parse_engine(name)
        .filter(|e| LifecycleGraph::supports_engine(*e))
        .ok_or_else(|| format!("--engine {name} is not a lifecycle engine"))
}

fn workload(args: &Args) -> Result<Workload, String> {
    Workload::generate(
        args.get("workload")?,
        args.num_or("nodes", 0)?,
        args.num_or("degree", 0)?,
        args.num("seed")?,
    )
}

fn median(values: &[u64]) -> u64 {
    median_p99(values).0
}

/// I1: incremental build.
fn build(args: &Args) -> Result<Value, String> {
    let engine = engine(args)?;
    let w = workload(args)?;
    let seed: u64 = args.num("seed")?;
    let reps: usize = args.num("reps")?;
    let edges = incremental_edges(&w, seed);
    let order = edges.iter().fold(FNV_START, |d, &(a, b)| fnv(fnv(d, a), b));
    let mut times = Vec::with_capacity(reps);
    let mut last = None;
    for _ in 0..reps {
        let start = Instant::now();
        let graph = build_incremental(engine, &w.ids, &edges)?;
        times.push(start.elapsed().as_nanos() as u64);
        check_logical(&graph, w.expected(), "build")?;
        if let Some(old) = last.replace(graph) {
            drop(old);
        }
    }
    let graph = last.ok_or("--reps must be positive")?;
    let mut g = gate(&w, &graph);
    g["edge_order"] = json!(format!("{order:016x}"));
    Ok(
        json!({"kind":"build","engine":engine.as_str(),"workload":w.label,
              "observation_ns":median(&times),"times_ns":times,"gate":g,
              "capacities":storage_capacities(&graph),"rss_bytes":rss_bytes()}),
    )
}

/// Flags of a call that must report a change.
fn changed(result: Result<bool, String>, what: &str) -> Result<(), String> {
    match result {
        Ok(true) => Ok(()),
        Ok(false) => Err(format!("{what}: no change")),
        Err(e) => Err(format!("{what}: {e}")),
    }
}

/// I2, I3, R1, R2, R3, R5: one timed window per repetition.
fn window(args: &Args) -> Result<Value, String> {
    let engine = engine(args)?;
    let w = workload(args)?;
    let seed: u64 = args.num("seed")?;
    let state = args.get("state")?;
    let op = args.get("op")?;
    let pool_name = args.get("pool")?;
    let k: usize = args.num("k")?;
    let reps: usize = args.num("reps")?;
    let mut graph = build_state(engine, &w, state, seed)?;
    check_logical(&graph, w.expected(), "build")?;
    let edges: Vec<(u64, u64)> = match pool_name {
        "spokes" => w.spokes().to_vec(),
        "edges" => w.base().to_vec(),
        "nodes" => Vec::new(),
        other => return Err(format!("unknown --pool {other:?}")),
    };
    let nodes = if pool_name == "nodes" {
        w.ordinary()
    } else {
        Vec::new()
    };
    let available = if pool_name == "nodes" {
        nodes.len()
    } else {
        edges.len()
    };
    if k == 0 || k > available {
        return Err(format!("--k {k} outside 1..={available}"));
    }
    if (op == "remove") != (pool_name == "nodes") {
        return Err("--op remove goes with --pool nodes, and only it".into());
    }
    let mut rng = Rng(seed ^ TARGET_SALT);
    let mut times = Vec::with_capacity(reps);
    let mut targets_digest = FNV_START;
    for _ in 0..reps {
        if op == "remove" {
            let targets = sample(&nodes, k, &mut rng);
            let mut incident = Vec::with_capacity(k);
            for &v in &targets {
                targets_digest = fnv(targets_digest, v);
                let list: Vec<(u64, bool)> = graph
                    .incident_after(v, None)
                    .ok_or("target not registered")?
                    .map(|(n, s)| (n, s.enabled))
                    .collect();
                incident.push(list);
            }
            let start = Instant::now();
            let mut removed = 0;
            for &v in &targets {
                removed += usize::from(graph.remove_node(v));
            }
            times.push(start.elapsed().as_nanos() as u64);
            if removed != k {
                return Err(format!("remove_node changed {removed} of {k}"));
            }
            for &v in &targets {
                changed(graph.add_node(v).map_err(|e| e.to_string()), "re-add")?;
            }
            for (&v, list) in targets.iter().zip(&incident) {
                for &(n, enabled) in list {
                    graph.link(v, n).map_err(|e| e.to_string())?;
                    if !enabled {
                        graph
                            .set_edge_enabled(v, n, false)
                            .map_err(|e| e.to_string())?;
                    }
                }
            }
        } else {
            let targets = sample(&edges, k, &mut rng);
            for &(a, b) in &targets {
                targets_digest = fnv(fnv(targets_digest, a), b);
            }
            let set = |g: &mut LifecycleGraph, on: bool| -> Result<(), String> {
                for &(a, b) in &targets {
                    changed(
                        g.set_edge_enabled(a, b, on).map_err(|e| e.to_string()),
                        "set_edge_enabled",
                    )?;
                }
                Ok(())
            };
            let relink = |g: &mut LifecycleGraph| -> Result<(), String> {
                for &(a, b) in &targets {
                    changed(g.link(a, b).map_err(|e| e.to_string()), "link")?;
                }
                Ok(())
            };
            let cut = |g: &mut LifecycleGraph| -> Result<(), String> {
                for &(a, b) in &targets {
                    changed(g.cut(a, b).map_err(|e| e.to_string()), "cut")?;
                }
                Ok(())
            };
            match op {
                "link" => cut(&mut graph)?,
                "enable" => set(&mut graph, false)?,
                "cut" | "disable" => {}
                other => return Err(format!("unknown --op {other:?}")),
            }
            let start = Instant::now();
            let mut done = 0;
            match op {
                "link" => {
                    for &(a, b) in &targets {
                        done += usize::from(graph.link(a, b).map_err(|e| e.to_string())?);
                    }
                }
                "cut" => {
                    for &(a, b) in &targets {
                        done += usize::from(graph.cut(a, b).map_err(|e| e.to_string())?);
                    }
                }
                _ => {
                    let on = op == "enable";
                    for &(a, b) in &targets {
                        done += usize::from(
                            graph
                                .set_edge_enabled(a, b, on)
                                .map_err(|e| e.to_string())?,
                        );
                    }
                }
            }
            times.push(start.elapsed().as_nanos() as u64);
            if done != k {
                return Err(format!("{op} changed {done} of {k}"));
            }
            match op {
                "cut" => relink(&mut graph)?,
                "disable" => set(&mut graph, true)?,
                _ => {}
            }
        }
        check_logical(&graph, w.expected(), "after restore")?;
    }
    let mut g = gate(&w, &graph);
    g["targets"] = json!(format!("{targets_digest:016x}"));
    Ok(
        json!({"kind":"window","engine":engine.as_str(),"workload":w.label,"state":state,
              "op":op,"pool":pool_name,"k":k,"reps":reps,
              "observation_ns":median(&times),"times_ns":times,"gate":g,
              "capacities":storage_capacities(&graph),"rss_bytes":rss_bytes()}),
    )
}

/// R4: hub removal cycles on a star.
fn degree_remove(args: &Args) -> Result<Value, String> {
    let engine = engine(args)?;
    let degree: u64 = args.num("degree")?;
    let k: usize = args.num("k")?;
    let reps: usize = args.num("reps")?;
    let w = Workload::generate("star", 0, degree, 0)?;
    let mut graph = build_ordered(engine, &w)?;
    check_logical(&graph, w.expected(), "build")?;
    let mut times = Vec::with_capacity(reps);
    for _ in 0..reps {
        let start = Instant::now();
        let mut ok = true;
        for _ in 0..k {
            ok &= graph.remove_node(0);
            ok &= graph.add_node(0).unwrap_or(false);
            for leaf in 1..=degree {
                ok &= graph.link(0, leaf).unwrap_or(false);
            }
        }
        times.push(start.elapsed().as_nanos() as u64);
        if !ok {
            return Err("a cycle call reported no change or failed".into());
        }
        check_logical(&graph, w.expected(), "after window")?;
    }
    let observation = median(&times);
    Ok(
        json!({"kind":"degree-remove","engine":engine.as_str(),"workload":w.label,"k":k,
              "reps":reps,"observation_ns":observation,"per_cycle_ns":observation as f64 / k as f64,
              "times_ns":times,"gate":gate(&w, &graph),
              "capacities":storage_capacities(&graph),"rss_bytes":rss_bytes()}),
    )
}

fn hub_of(w: &Workload) -> Result<u64, String> {
    w.hub
        .ok_or_else(|| "this cell needs a hub workload".to_owned())
}

/// P1: full traversals in pages of 1000.
fn traverse(args: &Args) -> Result<Value, String> {
    let engine = engine(args)?;
    let w = workload(args)?;
    let seed: u64 = args.num("seed")?;
    let state = args.get("state")?;
    let k: usize = args.num("k")?;
    let reps: usize = args.num("reps")?;
    let hub = hub_of(&w)?;
    let graph = build_state(engine, &w, state, seed)?;
    check_logical(&graph, w.expected(), "build")?;
    let degree = w.spokes().len();
    let mut buffer: Vec<(u64, bool, bool)> = Vec::with_capacity(degree + PAGE);
    let mut bounds: Vec<usize> = Vec::with_capacity(degree / PAGE + 2);
    let mut times = Vec::with_capacity(reps);
    let mut digests: Option<Vec<String>> = None;
    for _ in 0..reps {
        let start = Instant::now();
        for _ in 0..k {
            buffer.clear();
            bounds.clear();
            let mut cursor = None;
            loop {
                let before = buffer.len();
                buffer.extend(
                    graph
                        .incident_after(hub, cursor)
                        .ok_or("hub not registered")?
                        .take(PAGE)
                        .map(|(n, s)| (n, s.enabled, s.effective)),
                );
                bounds.push(buffer.len());
                if buffer.len() - before < PAGE {
                    break;
                }
                cursor = buffer.last().map(|e| e.0);
            }
        }
        times.push(start.elapsed().as_nanos() as u64);
        let mut from = 0;
        let pages: Vec<String> = bounds
            .iter()
            .map(|&to| {
                let d = page_digest(&buffer[from..to]);
                from = to;
                format!("{d:016x}")
            })
            .collect();
        if buffer.len() != degree {
            return Err(format!(
                "traversal returned {} of {degree} edges",
                buffer.len()
            ));
        }
        if digests.get_or_insert_with(|| pages.clone()) != &pages {
            return Err("page digests differ between traversals".into());
        }
    }
    let pages = digests.ok_or("--reps must be positive")?;
    let combined = pages.iter().fold(FNV_START, |d, p| {
        fnv(d, u64::from_str_radix(p, 16).unwrap_or(0))
    });
    let mut g = gate(&w, &graph);
    g["pages"] = json!(pages.len());
    g["pages_digest"] = json!(format!("{combined:016x}"));
    Ok(
        json!({"kind":"traverse","engine":engine.as_str(),"workload":w.label,"state":state,
              "k":k,"reps":reps,"observation_ns":median(&times),"times_ns":times,
              "page_digests":pages,"gate":g,"capacities":storage_capacities(&graph),
              "rss_bytes":rss_bytes()}),
    )
}

/// P2: single pages at seeded cursors.
fn pages(args: &Args) -> Result<Value, String> {
    let engine = engine(args)?;
    let w = workload(args)?;
    let seed: u64 = args.num("seed")?;
    let state = args.get("state")?;
    let each: usize = args.num_or("cursors", 100)?;
    let hub = hub_of(&w)?;
    let plan = cursor_plan(&w, each, seed)?;
    let mut graph = build_state(engine, &w, state, seed)?;
    ghost_setup(&mut graph, hub, &plan.ghosts)?;
    check_logical(&graph, w.expected(), "after ghost setup")?;
    let mut buffer: Vec<(u64, bool, bool)> = Vec::with_capacity(PAGE);
    let mut times = Vec::with_capacity(plan.cursors.len());
    let mut digests = Vec::with_capacity(plan.cursors.len());
    let mut by_kind: HashMap<&str, Vec<u64>> = HashMap::new();
    for &(kind, cursor) in &plan.cursors {
        buffer.clear();
        let start = Instant::now();
        buffer.extend(
            graph
                .incident_after(hub, Some(cursor))
                .ok_or("hub not registered")?
                .take(PAGE)
                .map(|(n, s)| (n, s.enabled, s.effective)),
        );
        let elapsed = start.elapsed().as_nanos() as u64;
        times.push(elapsed);
        by_kind.entry(kind.name()).or_default().push(elapsed);
        if buffer.first().is_some_and(|e| e.0 <= cursor) {
            return Err(format!("page after {cursor} starts at {}", buffer[0].0));
        }
        digests.push(format!("{:016x}", page_digest(&buffer)));
    }
    let (median_ns, p99_ns) = median_p99(&times);
    let combined = digests.iter().fold(FNV_START, |d, p| {
        fnv(d, u64::from_str_radix(p, 16).unwrap_or(0))
    });
    let kinds: Value = by_kind
        .iter()
        .map(|(k, v)| (k.to_string(), json!(median_p99(v).0)))
        .collect::<serde_json::Map<_, _>>()
        .into();
    let mut g = gate(&w, &graph);
    g["pages"] = json!(digests.len());
    g["pages_digest"] = json!(format!("{combined:016x}"));
    g["cursors"] = json!(format!(
        "{:016x}",
        plan.cursors
            .iter()
            .fold(FNV_START, |d, &(k, c)| fnv(fnv(d, k as u64), c))
    ));
    Ok(
        json!({"kind":"pages","engine":engine.as_str(),"workload":w.label,"state":state,
              "median_page_ns":median_ns,"p99_page_ns":p99_ns,"median_page_ns_by_kind":kinds,
              "times_ns":times,"page_digests":digests,"gate":g,
              "capacities":storage_capacities(&graph),"rss_bytes":rss_bytes()}),
    )
}

/// C2: timed mass removal and re-registration.
fn mass_churn(args: &Args) -> Result<Value, String> {
    let engine = engine(args)?;
    let w = workload(args)?;
    let seed: u64 = args.num("seed")?;
    let percent: u64 = args.num("percent")?;
    let plan = mass_plan(&w, percent, seed);
    let mut graph = build_ordered(engine, &w)?;
    check_logical(&graph, w.expected(), "build")?;
    let (mut total, mut slowest, mut ok) = (0_u64, 0_u64, true);
    let mut removal_ns = 0;
    for &v in &plan.removed {
        let start = Instant::now();
        ok &= graph.remove_node(v);
        let elapsed = start.elapsed().as_nanos() as u64;
        total += elapsed;
        removal_ns += elapsed;
        slowest = slowest.max(elapsed);
    }
    check_logical(&graph, plan.after_removal, "after removal")?;
    let after_removal =
        json!({"logical": logical(&graph), "storage": compact::storage_entries(&graph)});
    for &v in &plan.fresh {
        let start = Instant::now();
        ok &= graph.add_node(v).unwrap_or(false);
        let elapsed = start.elapsed().as_nanos() as u64;
        total += elapsed;
        slowest = slowest.max(elapsed);
    }
    if !ok {
        return Err("a call reported no change or failed".into());
    }
    check_logical(&graph, plan.at_end, "at end")?;
    let mut g = gate(&w, &graph);
    g["after_removal"] = after_removal;
    Ok(
        json!({"kind":"mass-churn","engine":engine.as_str(),"workload":w.label,
              "operations": plan.removed.len() + plan.fresh.len(),
              "observation_ns":total,"removal_ns":removal_ns,"slowest_op_ns":slowest,"gate":g,
              "capacities":storage_capacities(&graph),"rss_bytes":rss_bytes()}),
    )
}

/// The HTTP input of P3/P4 (see the module documentation).
fn emit(args: &Args) -> Result<(), String> {
    let w = workload(args)?;
    let seed: u64 = args.num("seed")?;
    let each: usize = args.num_or("cursors", 100)?;
    let hub = hub_of(&w)?;
    let plan = cursor_plan(&w, each, seed)?;
    let kind = |k: CursorKind| k.name();
    let header = json!({"kind":"emit","workload":w.label,"fingerprint":w.fingerprint(),"hub":hub,
        "nodes":w.ids.len(),"edges":w.edges.len(),"degree":w.spokes().len(),
        "cursors":plan.cursors.iter().map(|&(k, c)| json!([kind(k), c])).collect::<Vec<_>>(),
        "edge_cursors":plan.edge_cursors.iter().map(|&(k, s, t)| json!([kind(k), s, t])).collect::<Vec<_>>()});
    let stdout = std::io::stdout();
    let mut out = std::io::BufWriter::new(stdout.lock());
    let io = |e: std::io::Error| e.to_string();
    writeln!(out, "{header}").map_err(io)?;
    let mut ops: Vec<String> = compact::scrambled_order(&w, seed)
        .into_iter()
        .map(|v| format!(r#"{{"op":"add_node","node":"{v}"}}"#))
        .collect();
    ops.extend(
        w.edges
            .iter()
            .map(|(a, b)| format!(r#"{{"op":"link","source":"{a}","target":"{b}"}}"#)),
    );
    for g in &plan.ghosts {
        ops.push(format!(r#"{{"op":"add_node","node":"{g}"}}"#));
        ops.push(format!(
            r#"{{"op":"link","source":"{hub}","target":"{g}"}}"#
        ));
    }
    ops.extend(
        plan.ghosts
            .iter()
            .map(|g| format!(r#"{{"op":"remove_node","node":"{g}"}}"#)),
    );
    // Phase boundaries are respected: ghosts are removed only after every ghost is linked.
    let boundary = ops.len() - plan.ghosts.len();
    for (start, end) in [(0, boundary), (boundary, ops.len())] {
        for chunk in ops[start..end].chunks(BATCH) {
            writeln!(
                out,
                "B {} {{\"operations\":[{}]}}",
                chunk.len(),
                chunk.join(",")
            )
            .map_err(io)?;
        }
    }
    out.flush().map_err(io)
}

fn main() -> ExitCode {
    let mut items = std::env::args().skip(1);
    let command = items.next().unwrap_or_default();
    if command != "emit" {
        println!("{}", build_record("compact-cells"));
    }
    let result = Args::parse(items).and_then(|args| match command.as_str() {
        "build" => build(&args).map(Some),
        "window" => window(&args).map(Some),
        "degree-remove" => degree_remove(&args).map(Some),
        "traverse" => traverse(&args).map(Some),
        "pages" => pages(&args).map(Some),
        "mass-churn" => mass_churn(&args).map(Some),
        "emit" => emit(&args).map(|()| None),
        other => Err(format!("unknown command {other:?}")),
    });
    match result {
        Ok(value) => {
            if let Some(value) = value {
                println!("{value}");
            }
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("compact-cells: {error}");
            ExitCode::FAILURE
        }
    }
}
