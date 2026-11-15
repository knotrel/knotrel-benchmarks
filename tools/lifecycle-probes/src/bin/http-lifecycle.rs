//! In-process HTTP probe of lifecycle costs through the complete router.
//!
//! ```text
//! http-lifecycle --scenario S --engine E --nodes N --requests R --pairs P
//!     --warmup K --seed SEED
//! ```
//!
//! Requests go through the real Axum router with `tower::ServiceExt::oneshot`
//! (no sockets). Every pair builds both arms fresh (untimed), then times
//! each arm's window, alternating which arm runs first. Request bodies are
//! serialized before the window. Scenarios (candidate vs reference):
//!
//! - `optin-mutation`: R standalone batches of 1,024 alternating `cut`/`link`
//!   on a sparse graph; lifecycle-enabled server vs disabled server.
//! - `optin-query`: R batches of 1,024 `connected`; same arms.
//! - `ops`: R batches of lifecycle mutations (a mutation-heavy trace without
//!   queries, 256 operations per batch) on a lifecycle server, vs a plain
//!   server driven by an application-side planner that keeps the same
//!   registered topology and flags and sends the equivalent `link`/`cut`
//!   operations. Planning runs before the window (untimed), so the reference
//!   window measures server work only, which favors the reference.
//! - `events`: the same trace as source-managed feeder events (128 per
//!   request) vs the planner's equivalent legacy events (chunked at 1,024).
//! - `import`: one import of N nodes with 20% inactive nodes and 10% disabled
//!   edges on a lifecycle server, vs a plain server importing the effective
//!   graph (the application keeps the flags); `--requests` is ignored.
//! - `import-optin`: one all-active import on a lifecycle server vs the same
//!   legacy payload on a plain server.
//!
//! After each pair, an untimed check compares `connected` answers on 200
//! random pairs between the arms (for the `optin-*` scenarios the graphs are
//! identical by construction and the check still runs). Output: JSON lines.

use axum::{
    Router,
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_server::{ServerConfig, ServerMode, router_with_config};
use lifecycle_probes::{Mix, Op, Rng, Topology, generate, parse_engine, trace};
use rustc_hash::FxHashMap;
use serde_json::{Value, json};
use std::{collections::HashMap, process::ExitCode, time::Instant};
use tower::ServiceExt;

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

const BATCH: usize = 1_024;

async fn post(
    app: &Router,
    path: &str,
    instance: Option<&str>,
    body: String,
) -> (StatusCode, Value) {
    let mut request = Request::post(path).header("content-type", "application/json");
    if let Some(instance) = instance {
        request = request.header("x-knotrel-instance-id", instance);
    }
    let response = app
        .clone()
        .oneshot(request.body(Body::from(body)).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = to_bytes(response.into_body(), 64 << 20).await.unwrap();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn get(app: &Router, path: &str) -> Value {
    let response = app
        .clone()
        .oneshot(Request::get(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let bytes = to_bytes(response.into_body(), 1 << 20).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

fn config(engine: knotrel_core::EngineConfig, lifecycle: bool, mode: ServerMode) -> ServerConfig {
    ServerConfig::new("127.0.0.1:0".parse().unwrap(), engine, 32)
        .unwrap()
        .with_mode(mode)
        .with_topology_lifecycle(lifecycle)
        .with_graph_limits(knotrel_core::GraphLimits::default())
}

fn wire(op: &Op) -> Value {
    match *op {
        Op::AddNode(v) => json!({"op":"add_node","node":v.to_string()}),
        Op::Link(a, b) => json!({"op":"link","source":a.to_string(),"target":b.to_string()}),
        Op::Cut(a, b) => json!({"op":"cut","source":a.to_string(),"target":b.to_string()}),
        Op::Connected(a, b) => {
            json!({"op":"connected","source":a.to_string(),"target":b.to_string()})
        }
        Op::SetNode(v, f) => json!({"op":"set_node_active","node":v.to_string(),"active":f}),
        Op::SetEdge(a, b, f) => {
            json!({"op":"set_edge_enabled","source":a.to_string(),"target":b.to_string(),"enabled":f})
        }
        Op::Remove(v) => json!({"op":"remove_node","node":v.to_string()}),
    }
}

/// Application-side planner: keeps registered topology and flags and emits
/// the legacy operations that make a plain server's graph equal the
/// effective graph. Removed nodes stay registered in the plain server.
#[derive(Default)]
struct Planner {
    nodes: FxHashMap<u64, (bool, FxHashMap<u64, bool>)>,
}

impl Planner {
    fn new(n: u64, edges: &[(u64, u64)]) -> Self {
        let mut planner = Self::default();
        let mut sink = Vec::new();
        for v in 0..n {
            planner.plan(Op::AddNode(v), &mut sink);
        }
        for &(a, b) in edges {
            planner.plan(Op::Link(a, b), &mut sink);
        }
        planner
    }

    fn active(&self, v: u64) -> bool {
        self.nodes.get(&v).is_some_and(|node| node.0)
    }

    /// Appends the legacy operations equivalent to `op`.
    fn plan(&mut self, op: Op, out: &mut Vec<Op>) {
        match op {
            Op::AddNode(v) => {
                if let std::collections::hash_map::Entry::Vacant(entry) = self.nodes.entry(v) {
                    entry.insert((true, FxHashMap::default()));
                    out.push(Op::AddNode(v));
                }
            }
            Op::Link(a, b) => {
                if a == b || self.nodes.get(&a).is_some_and(|n| n.1.contains_key(&b)) {
                    return;
                }
                self.plan(Op::AddNode(a), out);
                self.plan(Op::AddNode(b), out);
                self.nodes.get_mut(&a).unwrap().1.insert(b, true);
                self.nodes.get_mut(&b).unwrap().1.insert(a, true);
                if self.active(a) && self.active(b) {
                    out.push(Op::Link(a, b));
                }
            }
            Op::Cut(a, b) => {
                let Some(enabled) = self.nodes.get(&a).and_then(|n| n.1.get(&b).copied()) else {
                    return;
                };
                let effective = enabled && self.active(a) && self.active(b);
                self.nodes.get_mut(&a).unwrap().1.remove(&b);
                self.nodes.get_mut(&b).unwrap().1.remove(&a);
                if effective {
                    out.push(Op::Cut(a, b));
                }
            }
            Op::SetNode(v, active) => {
                let Some(node) = self.nodes.get(&v) else {
                    return;
                };
                if node.0 == active {
                    return;
                }
                for (&w, &enabled) in &node.1 {
                    if enabled && self.active(w) {
                        out.push(if active {
                            Op::Link(v, w)
                        } else {
                            Op::Cut(v, w)
                        });
                    }
                }
                self.nodes.get_mut(&v).unwrap().0 = active;
            }
            Op::SetEdge(a, b, enabled) => {
                let Some(&current) = self.nodes.get(&a).and_then(|n| n.1.get(&b)) else {
                    return;
                };
                if current == enabled || !self.nodes.contains_key(&b) {
                    return;
                }
                self.nodes.get_mut(&a).unwrap().1.insert(b, enabled);
                self.nodes.get_mut(&b).unwrap().1.insert(a, enabled);
                if self.active(a) && self.active(b) {
                    out.push(if enabled {
                        Op::Link(a, b)
                    } else {
                        Op::Cut(a, b)
                    });
                }
            }
            Op::Remove(v) => {
                let Some((active, neighbors)) = self.nodes.remove(&v) else {
                    return;
                };
                for (w, enabled) in neighbors {
                    let node = self.nodes.get_mut(&w).unwrap();
                    node.1.remove(&v);
                    if enabled && active && node.0 {
                        out.push(Op::Cut(v, w));
                    }
                }
            }
            Op::Connected(..) => {}
        }
    }
}

struct Feeder {
    instance: String,
    sequence: u64,
}

impl Feeder {
    async fn start(app: &Router, nodes: Value, edges: Value) -> Self {
        let instance = get(app, "/v1/info").await["instance_id"]
            .as_str()
            .unwrap()
            .to_owned();
        let (status, _) = post(
            app,
            "/v1/feeder/session",
            Some(&instance),
            json!({"instance_id":instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000}).to_string(),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        let (status, body) = post(
            app,
            "/v1/feeder/import",
            Some(&instance),
            import_body(&instance, nodes, edges),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED, "{body}");
        Self {
            instance,
            sequence: 0,
        }
    }

    fn events(&mut self, ops: &[Op]) -> String {
        let events: Vec<Value> = ops
            .iter()
            .map(|op| {
                let mut event = wire(op);
                self.sequence += 1;
                let s = self.sequence;
                event["event_id"] = json!(format!("e{s}"));
                event["delivery_sequence"] = json!(s);
                event["prev_delivery_sequence"] = json!(s - 1);
                event["source_position"] = json!(format!("p{s}"));
                event["prev_source_position"] = json!(format!("p{}", s - 1));
                event
            })
            .collect();
        json!({"instance_id":self.instance,"graph_id":"default","generation":1,
               "feeder_session_id":"s","feeder_epoch":1,"source_id":"src","source_epoch":"e1",
               "events":events})
        .to_string()
    }
}

fn import_body(instance: &str, nodes: Value, edges: Value) -> String {
    json!({"mode":"create_only","instance_id":instance,"graph_id":"default","source_id":"src",
           "source_epoch":"e1","source_position":"p0","feeder_session_id":"s","feeder_epoch":1,
           "nodes":nodes,"edges":edges})
    .to_string()
}

fn legacy_nodes(n: u64) -> Value {
    json!((0..n).map(|v| v.to_string()).collect::<Vec<_>>())
}

fn legacy_edges(edges: &[(u64, u64)]) -> Value {
    json!(
        edges
            .iter()
            .map(|(a, b)| json!({"source":a.to_string(),"target":b.to_string()}))
            .collect::<Vec<_>>()
    )
}

async fn standalone(
    engine: knotrel_core::EngineConfig,
    lifecycle: bool,
    n: u64,
    edges: &[(u64, u64)],
) -> Router {
    let app = router_with_config(config(engine, lifecycle, ServerMode::Standalone));
    let mut ops: Vec<Op> = (0..n).map(Op::AddNode).collect();
    ops.extend(edges.iter().map(|&(a, b)| Op::Link(a, b)));
    for chunk in ops.chunks(BATCH) {
        let body = json!({"operations": chunk.iter().map(wire).collect::<Vec<_>>()}).to_string();
        assert_eq!(post(&app, "/v1/batch", None, body).await.0, StatusCode::OK);
    }
    app
}

/// One prepared arm: an app plus the request bodies of its window.
struct Arm {
    app: Router,
    path: &'static str,
    instance: Option<String>,
    bodies: Vec<String>,
    /// Lifecycle server: `connected` answers come from it. Plain reference:
    /// the planner answers inactive/absent endpoints.
    planner: Option<Planner>,
}

async fn run_window(arm: &Arm) -> u128 {
    let start = Instant::now();
    for body in &arm.bodies {
        let (status, _) = post(&arm.app, arm.path, arm.instance.as_deref(), body.clone()).await;
        assert!(status.is_success(), "{status}");
    }
    start.elapsed().as_nanos()
}

async fn answers(arm: &Arm, pairs: &[(u64, u64)]) -> Vec<Value> {
    let mut out = Vec::new();
    for &(a, b) in pairs {
        if let Some(planner) = &arm.planner
            && (!planner.active(a) || !planner.active(b))
        {
            let registered = planner.nodes.contains_key(&a) && planner.nodes.contains_key(&b);
            out.push(if registered {
                json!(false)
            } else {
                json!("unknown")
            });
            continue;
        }
        let (status, body) = post(
            &arm.app,
            "/v1/operations",
            None,
            wire(&Op::Connected(a, b)).to_string(),
        )
        .await;
        out.push(if status == StatusCode::NOT_FOUND {
            json!("unknown")
        } else {
            body["connected"].clone()
        });
    }
    out
}

struct Plan {
    engine: knotrel_core::EngineConfig,
    n: u64,
    edges: Vec<(u64, u64)>,
    requests: usize,
    seed: u64,
}

async fn prepare(scenario: &str, plan: &Plan, candidate: bool) -> Result<Arm, String> {
    let Plan {
        engine,
        n,
        ref edges,
        requests,
        seed,
    } = *plan;
    match scenario {
        "optin-mutation" | "optin-query" => {
            let app = standalone(engine, candidate, n, edges).await;
            let mut rng = Rng(seed ^ 0x51);
            let bodies = (0..requests)
                .map(|_| {
                    let ops: Vec<Value> = (0..BATCH)
                        .map(|i| {
                            if scenario == "optin-query" {
                                wire(&Op::Connected(rng.below(n), rng.below(n)))
                            } else {
                                let (a, b) = edges[(i / 2) % edges.len()];
                                wire(&if i % 2 == 0 {
                                    Op::Cut(a, b)
                                } else {
                                    Op::Link(a, b)
                                })
                            }
                        })
                        .collect();
                    json!({"operations": ops}).to_string()
                })
                .collect();
            Ok(Arm {
                app,
                path: "/v1/batch",
                instance: None,
                bodies,
                planner: None,
            })
        }
        "ops" | "events" => {
            let ops: Vec<Op> = trace(n, edges, Mix::MutationHeavy, requests * 256, seed)
                .into_iter()
                .filter(|op| !matches!(op, Op::Connected(..)))
                .collect();
            let per = if scenario == "ops" { 256 } else { 128 };
            if scenario == "ops" {
                let app = standalone(engine, candidate, n, edges).await;
                if candidate {
                    let bodies = ops
                        .chunks(per)
                        .map(|c| {
                            json!({"operations": c.iter().map(wire).collect::<Vec<_>>()})
                                .to_string()
                        })
                        .collect();
                    return Ok(Arm {
                        app,
                        path: "/v1/batch",
                        instance: None,
                        bodies,
                        planner: None,
                    });
                }
                // Planning is untimed: bodies are built here, before the window.
                let mut planner = Planner::new(n, edges);
                let mut bodies = Vec::new();
                for chunk in ops.chunks(per) {
                    let mut legacy = Vec::new();
                    for &op in chunk {
                        planner.plan(op, &mut legacy);
                    }
                    for part in legacy.chunks(BATCH) {
                        bodies.push(
                            json!({"operations": part.iter().map(wire).collect::<Vec<_>>()})
                                .to_string(),
                        );
                    }
                }
                return Ok(Arm {
                    app,
                    path: "/v1/batch",
                    instance: None,
                    bodies,
                    planner: Some(planner),
                });
            }
            let app = router_with_config(config(engine, candidate, ServerMode::SourceManaged));
            let mut feeder = Feeder::start(&app, legacy_nodes(n), legacy_edges(edges)).await;
            let mut planner = (!candidate).then(|| Planner::new(n, edges));
            let mut bodies = Vec::new();
            for chunk in ops.chunks(per) {
                match planner.as_mut() {
                    None => bodies.push(feeder.events(chunk)),
                    Some(planner) => {
                        let mut legacy = Vec::new();
                        for &op in chunk {
                            planner.plan(op, &mut legacy);
                        }
                        for part in legacy.chunks(BATCH) {
                            bodies.push(feeder.events(part));
                        }
                    }
                }
            }
            Ok(Arm {
                app,
                path: "/v1/feeder/events",
                instance: Some(feeder.instance),
                bodies,
                planner,
            })
        }
        "import" | "import-optin" => {
            let app = router_with_config(config(engine, candidate, ServerMode::SourceManaged));
            let instance = get(&app, "/v1/info").await["instance_id"]
                .as_str()
                .unwrap()
                .to_owned();
            let (status, _) = post(
                &app,
                "/v1/feeder/session",
                Some(&instance),
                json!({"instance_id":instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000}).to_string(),
            )
            .await;
            assert_eq!(status, StatusCode::OK);
            let mut rng = Rng(seed ^ 0x1a);
            let inactive: Vec<bool> = (0..n)
                .map(|_| scenario == "import" && rng.below(100) < 20)
                .collect();
            let disabled: Vec<bool> = edges
                .iter()
                .map(|_| scenario == "import" && rng.below(100) < 10)
                .collect();
            let (nodes, wire_edges, planner) = if candidate {
                let nodes: Vec<Value> = (0..n)
                    .map(|v| {
                        if inactive[v as usize] {
                            json!({"node":v.to_string(),"active":false})
                        } else {
                            json!(v.to_string())
                        }
                    })
                    .collect();
                let wire_edges: Vec<Value> = edges
                    .iter()
                    .zip(&disabled)
                    .map(|(&(a, b), &off)| {
                        if off {
                            json!({"source":a.to_string(),"target":b.to_string(),"enabled":false})
                        } else {
                            json!({"source":a.to_string(),"target":b.to_string()})
                        }
                    })
                    .collect();
                (json!(nodes), json!(wire_edges), None)
            } else {
                // The application keeps the flags (planner) and imports the
                // effective graph: every node, effective edges only.
                let mut planner = Planner::new(n, edges);
                let mut sink = Vec::new();
                for (index, &(a, b)) in edges.iter().enumerate() {
                    if disabled[index] {
                        planner.plan(Op::SetEdge(a, b, false), &mut sink);
                    }
                }
                for v in 0..n {
                    if inactive[v as usize] {
                        planner.plan(Op::SetNode(v, false), &mut sink);
                    }
                }
                let effective: Vec<(u64, u64)> = edges
                    .iter()
                    .zip(&disabled)
                    .filter(|&(&(a, b), &off)| {
                        !off && !inactive[a as usize] && !inactive[b as usize]
                    })
                    .map(|(&e, _)| e)
                    .collect();
                (legacy_nodes(n), legacy_edges(&effective), Some(planner))
            };
            let bodies = vec![import_body(&instance, nodes, wire_edges)];
            Ok(Arm {
                app,
                path: "/v1/feeder/import",
                instance: Some(instance),
                bodies,
                planner,
            })
        }
        _ => Err("unknown --scenario".into()),
    }
}

struct Args(HashMap<String, String>);

impl Args {
    fn num<T: std::str::FromStr>(&self, key: &str) -> Result<T, String> {
        self.0
            .get(key)
            .ok_or_else(|| format!("--{key} is required"))?
            .parse()
            .map_err(|_| format!("--{key} is invalid"))
    }
}

async fn main_async() -> Result<(), String> {
    let mut map = HashMap::new();
    let mut items = std::env::args().skip(1);
    while let Some(flag) = items.next() {
        let key = flag
            .strip_prefix("--")
            .ok_or("flags must start with --")?
            .to_owned();
        map.insert(key, items.next().ok_or("missing value")?);
    }
    let args = Args(map);
    let scenario = args
        .0
        .get("scenario")
        .ok_or("--scenario is required")?
        .clone();
    let engine = parse_engine(args.0.get("engine").ok_or("--engine is required")?)
        .ok_or("unknown --engine")?;
    let n: u64 = args.num("nodes")?;
    let seed: u64 = args.num("seed")?;
    let plan = Plan {
        engine,
        n,
        edges: generate(Topology::Sparse, n, seed),
        requests: args.num("requests")?,
        seed,
    };
    let pairs: usize = args.num("pairs")?;
    let warmup: usize = args.num("warmup")?;
    let mut rng = Rng(seed ^ 0xc4ec);
    let checks: Vec<(u64, u64)> = (0..200).map(|_| (rng.below(n), rng.below(n))).collect();
    for index in 0..warmup + pairs {
        let candidate = prepare(&scenario, &plan, true).await?;
        let reference = prepare(&scenario, &plan, false).await?;
        let candidate_first = index % 2 == 0;
        let (c, r) = if candidate_first {
            let c = run_window(&candidate).await;
            (c, run_window(&reference).await)
        } else {
            let r = run_window(&reference).await;
            (run_window(&candidate).await, r)
        };
        let agree = answers(&candidate, &checks).await == answers(&reference, &checks).await;
        if !agree {
            return Err(format!(
                "connectivity answers differ between arms in pair {index}"
            ));
        }
        let pair = index as i64 - warmup as i64;
        println!(
            "{}",
            json!({"kind": if pair < 0 {"warmup"} else {"pair"}, "pair": pair, "scenario": scenario,
                   "candidate_first": candidate_first, "candidate_ns": c as u64, "reference_ns": r as u64,
                   "candidate_requests": candidate.bodies.len(), "reference_requests": reference.bodies.len(),
                   "answers_agree": agree})
        );
    }
    Ok(())
}

fn main() -> ExitCode {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();
    match runtime.block_on(main_async()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
