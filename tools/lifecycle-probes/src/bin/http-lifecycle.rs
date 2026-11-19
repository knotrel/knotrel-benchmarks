//! In-process HTTP probe of lifecycle costs through the complete router.
//!
//! ```text
//! http-lifecycle --scenario S --engine E --topology T --nodes N
//!     --requests R --pairs P --warmup K --seed SEED
//!     [--inactive-percent I --disabled-percent D]
//! ```
//!
//! Requests go through the real Axum router with `tower::ServiceExt::oneshot`
//! (no sockets). The first output line is a `build` record. Every pair builds
//! both arms fresh (untimed), then times each arm's window, alternating which
//! arm runs first. Request bodies are prebuilt `Bytes` (cloning is a reference
//! count); the window sends them in order and drains each response body
//! without parsing it. After both windows, an untimed check compares
//! `connected` answers on 200 random pairs between the arms. Both arms stay
//! alive during both windows (balanced by alternation); every request crosses
//! the server's blocking-pool hop, as in production.
//!
//! Scenarios (candidate vs reference):
//! - `optin-mutation`: R batches of 1,024 alternating `cut`/`link`;
//!   lifecycle-enabled vs disabled server.
//! - `optin-query`: R batches of 1,024 `connected`; same arms.
//! - `ops`: a mutation-heavy lifecycle trace without queries in batches of
//!   256 on a lifecycle server, vs a plain server driven by an
//!   application-side planner that keeps the same registered topology and
//!   flags and sends the equivalent `link`/`cut`. Planning is untimed.
//! - `ops-query`: a query-heavy lifecycle trace (90% `connected`); the planner
//!   answers `connected` locally when an endpoint is inactive or absent and
//!   forwards the rest. Planning is untimed.
//! - `events`: the `ops` trace as feeder events, 128 lifecycle events per
//!   request, vs the planner's equivalent legacy events chunked at 1,024 per
//!   request (request counts can differ). Planning is untimed.
//! - `import`: R imports (one fresh source-managed server each) with I%
//!   inactive nodes and D% disabled edges, vs R plain imports of the
//!   effective graph where the application keeps the flags: a lean store
//!   (registered edge list, node and edge flag vectors) is copied and the
//!   effective edge list derived from it once per import call inside the
//!   reference window (amendment 2: the derivation is necessary reference
//!   work; the request body itself is serialized untimed in both arms).
//! - `import-optin`: R all-active legacy imports, lifecycle vs plain server.
//! - `metrics-ops`: the `ops` requests on two lifecycle servers, metrics
//!   enabled vs disabled.
//! - `metrics-legacy`: the `optin-mutation` requests on two
//!   lifecycle-disabled servers, metrics enabled vs disabled.
//!
//! Capability-equivalent references (v0.7.0 qualification 3): the suffix
//! `-equivalent` on `ops`, `ops-query`, `events`, `import` keeps the
//! candidate arm unchanged and changes only the reference window.
//! - `ops-equivalent`, `ops-query-equivalent`, `events-equivalent`: the
//!   planner's planning of each lifecycle chunk (256, or 128 for events) runs
//!   inside the reference window, right before that chunk's requests, from a
//!   planner in the state it had when the window began. For each operation
//!   the application first computes the outcome the lifecycle server reports
//!   per operation (changed or not, or the error code), then updates its
//!   catalog and plans the plain operations; the plain request publishes them.
//!   Request bodies stay prebuilt and untimed in both arms, as before.
//! - `import-equivalent`: per import call, inside the reference window, the
//!   application builds an [`EquivalentStore`] from its source records
//!   (validated as the lifecycle import validates: conflicting repeated node or
//!   edge, self-loop), derives the effective edges, sends the plain import,
//!   and adopts the new store only when the server answers 201.
//!   With `--inactive-percent 60 --disabled-percent 30` it is the
//!   equivalent of `import-high`.
//!
//! After both windows of an equivalent pair, [`equivalence_check`] compares
//! every per-operation outcome with the candidate's per-item results (ops,
//! ops-query; the lifecycle feeder reports no per-event results), the final
//! counts with the candidate's `/v1/stats`, and the registered content (every
//! node ID and flag, every edge, its flag and effectiveness, through
//! `node_state`/`edge_state`), and the plain server's content (every node of
//! catalog ∪ removed present, read-only; every effective edge present and no
//! other, by cutting them after the windows); a mismatch stops the probe.

use axum::{
    Router,
    body::{Body, Bytes, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_server::{ServerConfig, ServerMode, router_with_config};
use lifecycle_probes::{Mix, Op, Rng, Topology, build_record, generate, parse_engine, trace};
use rustc_hash::FxHashMap;
use serde_json::{Value, json};
use std::{collections::HashMap, process::ExitCode, time::Instant};
use tower::ServiceExt;

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

const BATCH: usize = 1_024;

/// One request with a prebuilt body.
#[derive(Clone)]
struct Call {
    app: Router,
    path: &'static str,
    instance: Option<String>,
    body: Bytes,
}

impl Call {
    fn request(&self) -> Request<Body> {
        let mut request = Request::post(self.path).header("content-type", "application/json");
        if let Some(instance) = &self.instance {
            request = request.header("x-knotrel-instance-id", instance.as_str());
        }
        request.body(Body::from(self.body.clone())).unwrap()
    }
}

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

fn config(
    engine: knotrel_core::EngineConfig,
    lifecycle: bool,
    mode: ServerMode,
    metrics: bool,
) -> ServerConfig {
    ServerConfig::new("127.0.0.1:0".parse().unwrap(), engine, 32)
        .unwrap()
        .with_mode(mode)
        .with_topology_lifecycle(lifecycle)
        .expect("lifecycle servers use a supported engine")
        .with_metrics_enabled(metrics)
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

fn batch_body(ops: &[Op]) -> Bytes {
    Bytes::from(json!({"operations": ops.iter().map(wire).collect::<Vec<_>>()}).to_string())
}

/// The per-operation outcome a lifecycle server reports (equivalent references):
/// `changed`, an error code, or a `connected` answer (`None`: forwarded to the plain
/// server, compared by the connectivity check instead).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Expect {
    Changed(bool),
    Error(&'static str),
    Connected(Option<bool>),
}

impl Expect {
    /// Whether the lifecycle server's per-item `result` matches.
    fn matches(&self, item: &Value) -> bool {
        match *self {
            Self::Changed(c) => item["result"] == "changed" && item["changed"] == c,
            Self::Error(code) => item["result"] == "error" && item["code"] == code,
            Self::Connected(Some(v)) => item["result"] == "connected" && item["connected"] == v,
            Self::Connected(None) => item["result"] == "connected",
        }
    }
}

/// Application-side planner: keeps registered topology and flags and emits
/// the legacy operations that make a plain server's graph equal the
/// effective graph. Removed nodes stay registered in the plain server.
#[derive(Default, Clone)]
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

    /// The outcome the lifecycle server reports for `op` in this planner
    /// state (qualification 3, equivalent references): what an application
    /// offering the same service computes for its caller before planning.
    fn expect(&self, op: Op) -> Expect {
        let edge = |a: u64, b: u64| self.nodes.get(&a).and_then(|n| n.1.get(&b).copied());
        match op {
            Op::AddNode(v) => Expect::Changed(!self.nodes.contains_key(&v)),
            Op::Link(a, b) | Op::Cut(a, b) | Op::SetEdge(a, b, _) if a == b => {
                Expect::Error("self_loop")
            }
            Op::Link(a, b) => Expect::Changed(edge(a, b).is_none()),
            Op::Cut(a, b) => Expect::Changed(edge(a, b).is_some()),
            Op::SetNode(v, active) => match self.nodes.get(&v) {
                None => Expect::Error("unknown_node"),
                Some(node) => Expect::Changed(node.0 != active),
            },
            Op::SetEdge(a, b, enabled) => {
                if !self.nodes.contains_key(&a) || !self.nodes.contains_key(&b) {
                    Expect::Error("unknown_node")
                } else {
                    match edge(a, b) {
                        None => Expect::Error("unknown_edge"),
                        Some(current) => Expect::Changed(current != enabled),
                    }
                }
            }
            Op::Remove(v) => Expect::Changed(self.nodes.contains_key(&v)),
            Op::Connected(a, b) => {
                if !self.nodes.contains_key(&a) || !self.nodes.contains_key(&b) {
                    Expect::Error("unknown_node")
                } else if !self.active(a) || !self.active(b) {
                    Expect::Connected(Some(false))
                } else {
                    Expect::Connected(None)
                }
            }
        }
    }

    /// Registered nodes, registered edges, active nodes, enabled edges,
    /// effective edges.
    fn counts(&self) -> [usize; 5] {
        let mut out = [self.nodes.len(), 0, 0, 0, 0];
        for (&v, (active, incident)) in &self.nodes {
            out[2] += usize::from(*active);
            for (&w, &enabled) in incident {
                if v < w {
                    out[1] += 1;
                    out[3] += usize::from(enabled);
                    out[4] += usize::from(enabled && *active && self.active(w));
                }
            }
        }
        out
    }

    /// Appends the legacy operations equivalent to `op`. `connected` is
    /// forwarded only when both endpoints are active (otherwise the
    /// application answers it locally).
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
            Op::Connected(a, b) => {
                if self.active(a) && self.active(b) {
                    out.push(Op::Connected(a, b));
                }
            }
        }
    }
}

struct Feeder {
    instance: String,
    sequence: u64,
}

impl Feeder {
    async fn session(app: &Router) -> String {
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
        instance
    }

    async fn start(app: &Router, n: u64, edges: &[(u64, u64)]) -> Self {
        let instance = Self::session(app).await;
        let body = import_body(&instance, legacy_nodes(n), legacy_edges(edges));
        let (status, reply) = post(app, "/v1/feeder/import", Some(&instance), body).await;
        assert_eq!(status, StatusCode::CREATED, "{reply}");
        Self {
            instance,
            sequence: 0,
        }
    }

    fn events(&mut self, ops: &[Op]) -> Bytes {
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
        Bytes::from(
            json!({"instance_id":self.instance,"graph_id":"default","generation":1,
                   "feeder_session_id":"s","feeder_epoch":1,"source_id":"src","source_epoch":"e1",
                   "events":events})
            .to_string(),
        )
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
    metrics: bool,
    n: u64,
    edges: &[(u64, u64)],
) -> Router {
    let app = router_with_config(config(engine, lifecycle, ServerMode::Standalone, metrics));
    let mut ops: Vec<Op> = (0..n).map(Op::AddNode).collect();
    ops.extend(edges.iter().map(|&(a, b)| Op::Link(a, b)));
    for chunk in ops.chunks(BATCH) {
        let body = String::from_utf8(batch_body(chunk).to_vec()).unwrap();
        assert_eq!(post(&app, "/v1/batch", None, body).await.0, StatusCode::OK);
    }
    app
}

/// The import reference's application-side flag store: a lean copy of what
/// the application must keep beside a plain server holding only the
/// effective graph (the registered edge list, one inactive flag per node and
/// one disabled flag per edge), plus the effective edge list it derives for
/// the plain import. One store is built per import call, inside the
/// reference window; node IDs are `0..n`.
#[derive(Clone)]
struct FlagStore {
    edges: Vec<(u64, u64)>,
    inactive: Vec<bool>,
    disabled: Vec<bool>,
    effective: Vec<(u64, u64)>,
    /// Effective edges actually sent in the plain payload (untimed copy).
    imported_effective: Vec<(u64, u64)>,
}

impl FlagStore {
    /// Copies the payload's topology and flags and derives the effective
    /// edge list (timed).
    fn build(&self) -> Self {
        let effective = self
            .edges
            .iter()
            .zip(&self.disabled)
            .filter(|&(&(a, b), &off)| !off && self.active(a) && self.active(b))
            .map(|(&edge, _)| edge)
            .collect();
        Self {
            edges: self.edges.clone(),
            inactive: self.inactive.clone(),
            disabled: self.disabled.clone(),
            effective,
            imported_effective: Vec::new(),
        }
    }

    fn active(&self, v: u64) -> bool {
        !self.inactive[v as usize]
    }

    /// Registered edges and their flags line up and the derived effective
    /// list equals the one sent in the plain payload (checked after the
    /// window; a mismatch aborts the probe).
    fn consistent(&self, sent: &[(u64, u64)]) -> bool {
        self.edges.len() == self.disabled.len() && self.effective == sent
    }
}

/// The application side of the capability-equivalent import reference
/// (qualification 3): the registered topology with flags, held so the
/// application can answer node and edge state and plan later lifecycle
/// changes, as the lifecycle server can.
#[derive(Default)]
struct EquivalentStore {
    nodes: FxHashMap<u64, (bool, FxHashMap<u64, bool>)>,
    effective: Vec<(u64, u64)>,
}

/// The source records the application imports from (node IDs `0..n`).
struct EquivalentSource {
    n: u64,
    edges: Vec<(u64, u64)>,
    inactive: Vec<bool>,
    disabled: Vec<bool>,
    /// Effective edges actually sent in the plain payload (untimed copy).
    sent_effective: Vec<(u64, u64)>,
}

impl EquivalentSource {
    /// Builds and validates a fresh store (timed). Validation is that of
    /// `LifecycleGraph::try_from_topology`: a repeated node or edge with a
    /// different flag, or a self-loop, rejects the whole import; identical
    /// repeats are accepted once; missing edge endpoints are registered
    /// active. (Graph limits are not configured in these cells.)
    fn build(&self) -> Result<EquivalentStore, String> {
        let mut store = EquivalentStore::default();
        store.nodes.reserve(self.n as usize);
        for v in 0..self.n {
            let active = !self.inactive[v as usize];
            match store.nodes.entry(v) {
                std::collections::hash_map::Entry::Occupied(entry) => {
                    if entry.get().0 != active {
                        return Err(format!("conflicting node {v}"));
                    }
                }
                std::collections::hash_map::Entry::Vacant(entry) => {
                    entry.insert((active, FxHashMap::default()));
                }
            }
        }
        for (&(a, b), &off) in self.edges.iter().zip(&self.disabled) {
            if a == b {
                return Err(format!("self-loop {a}"));
            }
            let enabled = !off;
            for v in [a, b] {
                store
                    .nodes
                    .entry(v)
                    .or_insert_with(|| (true, FxHashMap::default()));
            }
            if let Some(&existing) = store.nodes[&a].1.get(&b) {
                if existing != enabled {
                    return Err(format!("conflicting edge {a}-{b}"));
                }
                continue;
            }
            store.nodes.get_mut(&a).unwrap().1.insert(b, enabled);
            store.nodes.get_mut(&b).unwrap().1.insert(a, enabled);
            if enabled && store.nodes[&a].0 && store.nodes[&b].0 {
                store.effective.push((a, b));
            }
        }
        Ok(store)
    }
}

impl EquivalentStore {
    fn active(&self, v: u64) -> bool {
        self.nodes.get(&v).is_some_and(|node| node.0)
    }

    /// Registered nodes, registered edges, active nodes, enabled edges,
    /// effective edges.
    fn counts(&self) -> [usize; 5] {
        let registered: usize = self.nodes.values().map(|n| n.1.len()).sum::<usize>() / 2;
        let enabled: usize = self
            .nodes
            .values()
            .map(|n| n.1.values().filter(|&&e| e).count())
            .sum::<usize>()
            / 2;
        [
            self.nodes.len(),
            registered,
            self.nodes.values().filter(|n| n.0).count(),
            enabled,
            self.effective.len(),
        ]
    }
}

/// Each lifecycle chunk of an equivalent ops reference, with the number of
/// requests that follow it.
type PlanSteps = Vec<(Vec<Op>, usize)>;

/// One prepared arm: its window's calls, and how to check its answers.
struct Arm {
    calls: Vec<Call>,
    /// App used for the connectivity check.
    check: Router,
    planner: Option<Planner>,
    /// Import reference: the source of one flag store per import call,
    /// built inside the window; the last one built answers the check.
    flag_store: Option<FlagStore>,
    built_store: Option<FlagStore>,
    /// Equivalent ops references: a planner in its state at the window's start,
    /// and each lifecycle chunk with the number of calls that follow it.
    plan_steps: Option<(Planner, PlanSteps)>,
    /// Equivalent import reference: the source of one store per import call,
    /// and the store adopted after the last successful import.
    equivalent_source: Option<EquivalentSource>,
    built_equivalent: Option<EquivalentStore>,
    /// Equivalent ops references: the outcomes computed in the window, and
    /// the planner state at the window's end (for the final-state check).
    expected: Option<Vec<Expect>>,
    planned: Option<Planner>,
    /// Equivalent ops references: IDs removed in the window. The plain server
    /// keeps a removed node as an isolated vertex (it has no node removal).
    removed: Option<Vec<u64>>,
    /// Source-managed equivalent references (events, import): the feeder state
    /// after the window, for the post-window plain edge check (direct
    /// mutations are disabled in source-managed mode).
    feeder: Option<Feeder>,
    /// Candidate arms of equivalent scenarios: the response bodies, kept
    /// (reference-counted, no copy) for the per-operation outcome check.
    responses: Option<Vec<Bytes>>,
}

async fn send(call: &Call) -> (StatusCode, Bytes) {
    let response = call.app.clone().oneshot(call.request()).await.unwrap();
    let status = response.status();
    let body = to_bytes(response.into_body(), 64 << 20).await.unwrap();
    assert!(status.is_success(), "{status}");
    (status, body)
}

async fn run_window(arm: &mut Arm) -> u128 {
    let steps = arm.plan_steps.take();
    let start = Instant::now();
    if let Some((mut planner, steps)) = steps {
        let mut next = 0;
        let mut expected = Vec::new();
        let mut removed = Vec::new();
        for (ops, count) in &steps {
            let mut legacy = Vec::new();
            for &op in ops {
                // Outcome for the caller, then catalog update and plain operations.
                let outcome = planner.expect(op);
                if let (Op::Remove(v), Expect::Changed(true)) = (op, outcome) {
                    removed.push(v);
                }
                expected.push(outcome);
                planner.plan(op, &mut legacy);
            }
            std::hint::black_box(&legacy);
            for call in &arm.calls[next..next + count] {
                send(call).await;
            }
            next += count;
        }
        let elapsed = start.elapsed().as_nanos();
        assert_eq!(next, arm.calls.len(), "planned chunks cover every call");
        arm.expected = Some(expected);
        arm.planned = Some(planner);
        arm.removed = Some(removed);
        return elapsed;
    }
    for call in &arm.calls {
        if let Some(store) = &arm.flag_store {
            arm.built_store = Some(store.build());
        }
        let pending = arm.equivalent_source.as_ref().map(EquivalentSource::build);
        let (status, body) = send(call).await;
        if let Some(responses) = arm.responses.as_mut() {
            responses.push(body);
        }
        if let Some(pending) = pending {
            let store = pending.expect("the equivalent store validates the source records");
            if status == StatusCode::CREATED {
                arm.built_equivalent = Some(store);
            }
        }
    }
    start.elapsed().as_nanos()
}

async fn answers(arm: &Arm, pairs: &[(u64, u64)]) -> Vec<Value> {
    let mut out = Vec::new();
    if let (Some(template), Some(store)) = (&arm.flag_store, &arm.built_store) {
        // A store whose derived effective list differs from the payload
        // actually imported invalidates the run instead of skewing answers.
        assert!(
            store.consistent(&template.imported_effective),
            "flag store inconsistent with the imported effective graph"
        );
    }
    if let (Some(source), Some(store)) = (&arm.equivalent_source, &arm.built_equivalent) {
        assert_eq!(
            store.effective, source.sent_effective,
            "equivalent store differs from the imported effective graph"
        );
        let expected_registered = {
            let mut seen = std::collections::HashSet::new();
            source
                .edges
                .iter()
                .filter(|&&(a, b)| seen.insert((a.min(b), a.max(b))))
                .count()
        };
        let counts = store.counts();
        assert_eq!(counts[0], source.n as usize, "equivalent store node count");
        assert_eq!(
            counts[1], expected_registered,
            "equivalent store registered edges"
        );
        assert_eq!(
            counts[2],
            source.inactive.iter().filter(|&&off| !off).count(),
            "equivalent store active nodes"
        );
    }
    for &(a, b) in pairs {
        if let Some(store) = &arm.built_equivalent
            && (!store.active(a) || !store.active(b))
        {
            out.push(json!(false));
            continue;
        }
        if let Some(store) = &arm.built_store
            && (!store.active(a) || !store.active(b))
        {
            out.push(json!(false));
            continue;
        }
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
            &arm.check,
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

/// Equivalence checks after both windows of an `*-equivalent` pair
/// (qualification 3), run sequentially with no request in flight (no
/// concurrent mutation): connectivity agreement alone does not show
/// equivalence.
/// - **Per operation (ops, ops-query):** every outcome the reference computed
///   in its window equals the candidate's per-item result (`connected` answers
///   forwarded to the plain server are compared by the connectivity check).
/// - **Final state:** the candidate's `/v1/stats` registered nodes and edges,
///   active nodes, enabled and effective edges equal the application
///   catalog's, and the plain server's edge count equals the effective edges.
async fn equivalence_check(candidate: &Arm, reference: &mut Arm) -> Result<(), String> {
    if let (Some(responses), Some(expected)) = (&candidate.responses, &reference.expected) {
        let mut items = Vec::new();
        for body in responses {
            let value: Value =
                serde_json::from_slice(body).map_err(|e| format!("candidate response: {e}"))?;
            items.extend(
                value["results"]
                    .as_array()
                    .cloned()
                    .ok_or("candidate response without results")?,
            );
        }
        if items.len() != expected.len() {
            return Err(format!(
                "{} candidate results for {} reference outcomes",
                items.len(),
                expected.len()
            ));
        }
        for (i, (expect, item)) in expected.iter().zip(&items).enumerate() {
            if !expect.matches(item) {
                return Err(format!(
                    "operation {i}: reference outcome {expect:?}, candidate result {item}"
                ));
            }
        }
    }
    let (catalog, entries) = match (&reference.planned, &reference.built_equivalent) {
        (Some(planner), _) => (planner.counts(), planner.nodes.clone()),
        (None, Some(store)) => (store.counts(), store.nodes.clone()),
        (None, None) => return Err("equivalent reference without an application catalog".into()),
    };
    let entries = &entries;
    let stats = get(&candidate.check, "/v1/stats").await;
    let field = |v: &Value, k: &str| v[k].as_u64().map(|x| x as usize);
    let lifecycle = [
        field(&stats, "node_count"),
        field(&stats, "edge_count"),
        field(&stats, "active_node_count"),
        field(&stats, "enabled_edge_count"),
        field(&stats, "effective_edge_count"),
    ];
    if lifecycle != catalog.map(Some) {
        return Err(format!(
            "candidate lifecycle counts {lifecycle:?} differ from the application catalog {catalog:?}"
        ));
    }
    let plain = get(&reference.check, "/v1/stats").await;
    if field(&plain, "edge_count") != Some(catalog[4]) {
        return Err(format!(
            "plain server edge count {:?} differs from the effective edges {}",
            plain["edge_count"], catalog[4]
        ));
    }
    // Plain nodes: the catalog's, plus removed IDs kept as isolated vertices, nothing else.
    let mut expected_nodes: std::collections::HashSet<u64> = entries.keys().copied().collect();
    expected_nodes.extend(reference.removed.iter().flatten().copied());
    if field(&plain, "node_count") != Some(expected_nodes.len()) {
        return Err(format!(
            "plain server node count {:?}, expected {} (catalog plus removed)",
            plain["node_count"],
            expected_nodes.len()
        ));
    }
    registered_content_check(candidate, reference, entries, &expected_nodes).await
}

/// Content of the registered topology (qualification 3): every node of the
/// application catalog has the same ID and `active` flag in the candidate
/// (`node_state`), and every registered edge the same endpoints, `enabled`
/// flag and effectiveness (`edge_state`); with the counts equal (checked
/// before), the candidate has no other entry. Every effective edge is present
/// in the plain server (`edge_state`: registered). Queries run after the
/// windows, untimed, in batches of [`BATCH`].
async fn registered_content_check(
    candidate: &Arm,
    reference: &mut Arm,
    entries: &FxHashMap<u64, (bool, FxHashMap<u64, bool>)>,
    plain_nodes: &std::collections::HashSet<u64>,
) -> Result<(), String> {
    let active = |v: u64| entries.get(&v).is_some_and(|n| n.0);
    let mut queries: Vec<(Value, Value)> = Vec::new();
    let mut effective: Vec<(u64, u64)> = Vec::new();
    for (&v, (is_active, incident)) in entries {
        queries.push((
            json!({"op":"node_state","node":v.to_string()}),
            json!({"result":"node_state","registered":true,"active":is_active}),
        ));
        for (&w, &enabled) in incident {
            if v < w {
                let eff = enabled && *is_active && active(w);
                queries.push((
                    json!({"op":"edge_state","source":v.to_string(),"target":w.to_string()}),
                    json!({"result":"edge_state","registered":true,"enabled":enabled,"effective":eff}),
                ));
                if eff {
                    effective.push((v, w));
                }
            }
        }
    }
    for chunk in queries.chunks(BATCH) {
        let ops: Vec<&Value> = chunk.iter().map(|(q, _)| q).collect();
        let (status, reply) = post(
            &candidate.check,
            "/v1/batch",
            None,
            json!({"operations": ops}).to_string(),
        )
        .await;
        let results = reply["results"]
            .as_array()
            .ok_or_else(|| format!("candidate state query {status}: {reply}"))?;
        for ((query, want), got) in chunk.iter().zip(results) {
            if got != want {
                return Err(format!(
                    "registered content: {query} expected {want}, candidate {got}"
                ));
            }
        }
    }
    // Plain server, after the candidate checks. The plain API has no read-only
    // node or edge state query (`node_state`/`edge_state` need lifecycle
    // support), so:
    // - every node of catalog ∪ removed is checked one by one with the
    //   read-only `connected(v, v)` (true only for an existing vertex); with the
    //   node count equal to |catalog ∪ removed| it holds no other node. (Unlike
    //   the lifecycle server, the plain server has no node removal: a removed
    //   node stays as an isolated vertex.)
    // - every effective edge is cut, one by one, and must report `changed`;
    //   the edge count must then be 0, so the plain edge set was exactly the
    //   effective set. This mutates only this pair's plain server, after both
    //   windows and the connectivity check, with no request in flight; the
    //   server is discarded afterwards.
    let nodes: Vec<u64> = plain_nodes.iter().copied().collect();
    for chunk in nodes.chunks(BATCH) {
        let ops: Vec<Value> = chunk.iter().map(|v| wire(&Op::Connected(*v, *v))).collect();
        let (status, reply) = post(
            &reference.check,
            "/v1/batch",
            None,
            json!({"operations": ops}).to_string(),
        )
        .await;
        let results = reply["results"]
            .as_array()
            .ok_or_else(|| format!("plain node query {status}: {reply}"))?;
        for (v, got) in chunk.iter().zip(results) {
            if got["result"] != "connected" || got["connected"] != true {
                return Err(format!(
                    "plain server: expected node {v} (catalog or removed) missing ({got})"
                ));
            }
        }
    }
    for chunk in effective.chunks(BATCH) {
        let cuts: Vec<Op> = chunk.iter().map(|&(a, b)| Op::Cut(a, b)).collect();
        if let Some(feeder) = reference.feeder.as_mut() {
            // Source-managed: cut events. The feeder reports no per-event result;
            // the edge count before (equal to the effective edges) and after (0)
            // still proves the exact edge set.
            let body = String::from_utf8(feeder.events(&cuts).to_vec()).unwrap();
            let instance = feeder.instance.clone();
            let (status, reply) =
                post(&reference.check, "/v1/feeder/events", Some(&instance), body).await;
            if status != StatusCode::OK {
                return Err(format!("plain edge check events {status}: {reply}"));
            }
            continue;
        }
        let ops: Vec<Value> = cuts.iter().map(wire).collect();
        let (status, reply) = post(
            &reference.check,
            "/v1/batch",
            None,
            json!({"operations": ops}).to_string(),
        )
        .await;
        let results = reply["results"]
            .as_array()
            .ok_or_else(|| format!("plain edge check {status}: {reply}"))?;
        for ((a, b), got) in chunk.iter().zip(results) {
            if got["result"] != "changed" || got["changed"] != true {
                return Err(format!(
                    "plain server: effective edge {a}-{b} missing ({got})"
                ));
            }
        }
    }
    let after = get(&reference.check, "/v1/stats").await;
    if after["edge_count"] != 0 {
        return Err(format!(
            "plain server holds {} edges beyond the effective set",
            after["edge_count"]
        ));
    }
    Ok(())
}

struct Plan {
    engine: knotrel_core::EngineConfig,
    n: u64,
    edges: Vec<(u64, u64)>,
    requests: usize,
    seed: u64,
    inactive_percent: u64,
    disabled_percent: u64,
}

fn calls(
    app: &Router,
    path: &'static str,
    instance: Option<&str>,
    bodies: Vec<Bytes>,
) -> Vec<Call> {
    bodies
        .into_iter()
        .map(|body| Call {
            app: app.clone(),
            path,
            instance: instance.map(str::to_owned),
            body,
        })
        .collect()
}

async fn prepare(scenario: &str, plan: &Plan, candidate: bool) -> Result<Arm, String> {
    let Plan {
        engine,
        n,
        ref edges,
        requests,
        seed,
        inactive_percent,
        disabled_percent,
    } = *plan;
    // Qualification 3: `<base>-equivalent` changes only the reference window.
    let (scenario, equivalent) = match scenario.strip_suffix("-equivalent") {
        Some(base @ ("ops" | "ops-query" | "events" | "import")) => (base, true),
        Some(_) => return Err("unknown --scenario".into()),
        None => (scenario, false),
    };
    let equivalent_scenario = equivalent;
    let equivalent = equivalent && !candidate;
    match scenario {
        "optin-mutation" | "optin-query" | "metrics-legacy" => {
            let (lifecycle, metrics) = match scenario {
                "metrics-legacy" => (false, candidate),
                _ => (candidate, false),
            };
            let app = standalone(engine, lifecycle, metrics, n, edges).await;
            let mut rng = Rng(seed ^ 0x51);
            let bodies = (0..requests)
                .map(|_| {
                    let ops: Vec<Op> = (0..BATCH)
                        .map(|i| {
                            if scenario == "optin-query" {
                                Op::Connected(rng.below(n), rng.below(n))
                            } else {
                                let (a, b) = edges[(i / 2) % edges.len()];
                                if i % 2 == 0 {
                                    Op::Cut(a, b)
                                } else {
                                    Op::Link(a, b)
                                }
                            }
                        })
                        .collect();
                    batch_body(&ops)
                })
                .collect();
            Ok(Arm {
                calls: calls(&app, "/v1/batch", None, bodies),
                check: app,
                planner: None,
                flag_store: None,
                built_store: None,
                plan_steps: None,
                equivalent_source: None,
                built_equivalent: None,
                expected: None,
                planned: None,
                removed: None,
                feeder: None,
                responses: None,
            })
        }
        "ops" | "ops-query" | "events" | "metrics-ops" => {
            let mix = if scenario == "ops-query" {
                Mix::QueryHeavy
            } else {
                Mix::MutationHeavy
            };
            let ops: Vec<Op> = trace(n, edges, mix, requests * 256, seed)
                .into_iter()
                .filter(|op| scenario == "ops-query" || !matches!(op, Op::Connected(..)))
                .collect();
            if scenario == "events" {
                let app =
                    router_with_config(config(engine, candidate, ServerMode::SourceManaged, false));
                let mut feeder = Feeder::start(&app, n, edges).await;
                let mut planner = (!candidate).then(|| Planner::new(n, edges));
                let pristine = planner.clone().filter(|_| equivalent);
                let mut steps = Vec::new();
                let mut bodies = Vec::new();
                for chunk in ops.chunks(128) {
                    match planner.as_mut() {
                        None => bodies.push(feeder.events(chunk)),
                        Some(planner) => {
                            let mut legacy = Vec::new();
                            for &op in chunk {
                                planner.plan(op, &mut legacy);
                            }
                            let before = bodies.len();
                            for part in legacy.chunks(BATCH) {
                                bodies.push(feeder.events(part));
                            }
                            steps.push((chunk.to_vec(), bodies.len() - before));
                        }
                    }
                }
                let instance = feeder.instance.clone();
                let kept_feeder = equivalent.then_some(feeder);
                return Ok(Arm {
                    calls: calls(&app, "/v1/feeder/events", Some(&instance), bodies),
                    check: app,
                    planner,
                    flag_store: None,
                    built_store: None,
                    plan_steps: pristine.map(|p| (p, steps)),
                    equivalent_source: None,
                    built_equivalent: None,
                    expected: None,
                    planned: None,
                    removed: None,
                    feeder: kept_feeder,
                    responses: None,
                });
            }
            let (lifecycle, metrics) = if scenario == "metrics-ops" {
                (true, candidate)
            } else {
                (candidate, false)
            };
            let app = standalone(engine, lifecycle, metrics, n, edges).await;
            if lifecycle {
                let bodies = ops.chunks(256).map(batch_body).collect();
                return Ok(Arm {
                    calls: calls(&app, "/v1/batch", None, bodies),
                    check: app,
                    planner: None,
                    flag_store: None,
                    built_store: None,
                    plan_steps: None,
                    equivalent_source: None,
                    built_equivalent: None,
                    expected: None,
                    planned: None,
                    removed: None,
                    feeder: None,
                    responses: (candidate && equivalent_scenario).then(Vec::new),
                });
            }
            let mut planner = Planner::new(n, edges);
            let pristine = equivalent.then(|| planner.clone());
            let mut steps = Vec::new();
            let mut bodies = Vec::new();
            for chunk in ops.chunks(256) {
                let mut legacy = Vec::new();
                for &op in chunk {
                    planner.plan(op, &mut legacy);
                }
                let before = bodies.len();
                for part in legacy.chunks(BATCH) {
                    bodies.push(batch_body(part));
                }
                steps.push((chunk.to_vec(), bodies.len() - before));
            }
            Ok(Arm {
                calls: calls(&app, "/v1/batch", None, bodies),
                check: app,
                planner: Some(planner),
                flag_store: None,
                built_store: None,
                plan_steps: pristine.map(|p| (p, steps)),
                equivalent_source: None,
                built_equivalent: None,
                expected: None,
                planned: None,
                removed: None,
                feeder: None,
                responses: None,
            })
        }
        "import" | "import-optin" => {
            let mut rng = Rng(seed ^ 0x1a);
            let flagged = scenario == "import";
            let inactive: Vec<bool> = (0..n)
                .map(|_| flagged && rng.below(100) < inactive_percent)
                .collect();
            let disabled: Vec<bool> = edges
                .iter()
                .map(|_| flagged && rng.below(100) < disabled_percent)
                .collect();
            let mut all = Vec::new();
            let mut check = None;
            let mut last_instance = String::new();
            let mut sent_effective = Vec::new();
            for _ in 0..requests.max(1) {
                let app =
                    router_with_config(config(engine, candidate, ServerMode::SourceManaged, false));
                let instance = Feeder::session(&app).await;
                last_instance = instance.clone();
                let (nodes, wire_edges) = if candidate || !flagged {
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
                    (json!(nodes), json!(wire_edges))
                } else {
                    let effective: Vec<(u64, u64)> = edges
                        .iter()
                        .zip(&disabled)
                        .filter(|&(&(a, b), &off)| {
                            !off && !inactive[a as usize] && !inactive[b as usize]
                        })
                        .map(|(&e, _)| e)
                        .collect();
                    let payload = (legacy_nodes(n), legacy_edges(&effective));
                    sent_effective = effective;
                    payload
                };
                let body = Bytes::from(import_body(&instance, nodes, wire_edges));
                all.extend(calls(
                    &app,
                    "/v1/feeder/import",
                    Some(&instance),
                    vec![body],
                ));
                check = Some(app);
            }
            let imported_effective = sent_effective;
            if equivalent {
                if !flagged {
                    return Err("import-equivalent needs the flagged import".into());
                }
                return Ok(Arm {
                    calls: all,
                    check: check.unwrap(),
                    planner: None,
                    flag_store: None,
                    built_store: None,
                    plan_steps: None,
                    equivalent_source: Some(EquivalentSource {
                        n,
                        edges: edges.clone(),
                        inactive,
                        disabled,
                        sent_effective: imported_effective,
                    }),
                    built_equivalent: None,
                    expected: None,
                    planned: None,
                    removed: None,
                    feeder: Some(Feeder {
                        instance: last_instance,
                        sequence: 0,
                    }),
                    responses: None,
                });
            }
            let flag_store = (!candidate && flagged).then(|| FlagStore {
                edges: edges.clone(),
                inactive,
                disabled,
                effective: Vec::new(),
                imported_effective,
            });
            Ok(Arm {
                calls: all,
                check: check.unwrap(),
                planner: None,
                flag_store,
                built_store: None,
                plan_steps: None,
                equivalent_source: None,
                built_equivalent: None,
                expected: None,
                planned: None,
                removed: None,
                feeder: None,
                responses: None,
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

    fn num_or<T: std::str::FromStr>(&self, key: &str, default: T) -> Result<T, String> {
        if self.0.contains_key(key) {
            self.num(key)
        } else {
            Ok(default)
        }
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
    let topology = Topology::parse(args.0.get("topology").map_or("sparse", String::as_str))
        .ok_or("unknown --topology")?;
    let n: u64 = args.num("nodes")?;
    let seed: u64 = args.num("seed")?;
    let plan = Plan {
        engine,
        n,
        edges: generate(topology, n, seed),
        requests: args.num("requests")?,
        seed,
        inactive_percent: args.num_or("inactive-percent", 20)?,
        disabled_percent: args.num_or("disabled-percent", 10)?,
    };
    let pairs: usize = args.num("pairs")?;
    let warmup: usize = args.num("warmup")?;
    let mut rng = Rng(seed ^ 0xc4ec);
    let checks: Vec<(u64, u64)> = (0..200).map(|_| (rng.below(n), rng.below(n))).collect();
    for index in 0..warmup + pairs {
        let mut candidate = prepare(&scenario, &plan, true).await?;
        let mut reference = prepare(&scenario, &plan, false).await?;
        let candidate_first = index % 2 == 0;
        let (c, r) = if candidate_first {
            let c = run_window(&mut candidate).await;
            (c, run_window(&mut reference).await)
        } else {
            let r = run_window(&mut reference).await;
            (run_window(&mut candidate).await, r)
        };
        let agree = answers(&candidate, &checks).await == answers(&reference, &checks).await;
        if !agree {
            return Err(format!(
                "connectivity answers differ between arms in pair {index}"
            ));
        }
        if scenario.ends_with("-equivalent") {
            equivalence_check(&candidate, &mut reference)
                .await
                .map_err(|e| format!("equivalence check failed in pair {index}: {e}"))?;
        }
        let pair = index as i64 - warmup as i64;
        println!(
            "{}",
            json!({"kind": if pair < 0 {"warmup"} else {"pair"}, "pair": pair, "scenario": scenario,
                   "candidate_first": candidate_first, "candidate_ns": c as u64, "reference_ns": r as u64,
                   "candidate_requests": candidate.calls.len(), "reference_requests": reference.calls.len(),
                   "answers_agree": agree})
        );
    }
    Ok(())
}

fn main() -> ExitCode {
    println!("{}", build_record("http-lifecycle"));
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
