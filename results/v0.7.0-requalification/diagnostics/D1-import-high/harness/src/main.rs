//! D1 diagnostic (DIAGNOSTICS-PLAN.md): B4 `import-high` cost breakdown and a
//! capability-equivalent comparison. Not part of the qualification.
//!
//! The topology, flags and request bodies are those of the frozen
//! `http-lifecycle --scenario import` (sparse, `--seed`, flags from
//! `Rng(seed ^ 0x1a)`), through the real router in process, one fresh
//! source-managed server per import, untimed setup.
//!
//! Arms (every pair runs all three, in a rotating order):
//! - `L`: lifecycle server, full registered topology with flags (the B4 candidate);
//! - `F`: plain server, full registered topology with every node and edge active
//!   (the same parse and storage volume, no flags);
//! - `E`: plain server, effective graph only, plus the application-side flag store
//!   copied and the effective list derived inside the timed window (the B4 reference).
//!
//! Then, untimed against the pairs: body bytes per arm; parse-only time of each
//! body with `sonic_rs::Value` (a proxy: the server decodes into typed structs);
//! and the server's own `knotrel_import_duration_seconds{phase}` sums for one
//! metrics-enabled import of L and of F.
//!
//! ```text
//! d1-import --nodes 10000 --seed 5000001 --inactive-percent 60 --disabled-percent 30 --pairs 12 --warmup 2
//! ```

use axum::{
    Router,
    body::{Body, Bytes, to_bytes},
    http::{Request, StatusCode},
};
use knotrel_server::{ServerConfig, ServerMode, router_with_config};
use lifecycle_probes::{Rng, Topology, generate};
use serde_json::{Value, json};
use std::{collections::HashMap, time::Instant};
use tower::ServiceExt;

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

fn config(lifecycle: bool, metrics: bool) -> ServerConfig {
    ServerConfig::new("127.0.0.1:0".parse().unwrap(), knotrel_core::EngineConfig::CompactBfs, 32)
        .unwrap()
        .with_mode(ServerMode::SourceManaged)
        .with_topology_lifecycle(lifecycle)
        .expect("compact-bfs supports lifecycle")
        .with_metrics_enabled(metrics)
        .with_graph_limits(knotrel_core::GraphLimits::default())
}

async fn send(app: &Router, method: &str, path: &str, instance: Option<&str>, body: Bytes) -> (StatusCode, Bytes) {
    let mut request = Request::builder().method(method).uri(path).header("content-type", "application/json");
    if let Some(instance) = instance {
        request = request.header("x-knotrel-instance-id", instance);
    }
    let response = app.clone().oneshot(request.body(Body::from(body)).unwrap()).await.unwrap();
    let status = response.status();
    (status, to_bytes(response.into_body(), 64 << 20).await.unwrap())
}

async fn session(app: &Router) -> String {
    let (_, info) = send(app, "GET", "/v1/info", None, Bytes::new()).await;
    let instance = serde_json::from_slice::<Value>(&info).unwrap()["instance_id"].as_str().unwrap().to_owned();
    let body = json!({"instance_id":instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000});
    let (status, _) = send(app, "POST", "/v1/feeder/session", Some(&instance), Bytes::from(body.to_string())).await;
    assert_eq!(status, StatusCode::OK);
    instance
}

/// The frozen probe's import body; `{instance}` is substituted per server.
fn body(instance: &str, nodes: &Value, edges: &Value) -> Bytes {
    Bytes::from(
        json!({"mode":"create_only","instance_id":instance,"graph_id":"default","source_id":"src",
               "source_epoch":"e1","source_position":"p0","feeder_session_id":"s","feeder_epoch":1,
               "nodes":nodes,"edges":edges})
        .to_string(),
    )
}

struct Inputs {
    n: u64,
    edges: Vec<(u64, u64)>,
    inactive: Vec<bool>,
    disabled: Vec<bool>,
    l_nodes: Value,
    l_edges: Value,
    f_nodes: Value,
    f_edges: Value,
    e_edges: Value,
}

fn inputs(n: u64, seed: u64, inactive_percent: u64, disabled_percent: u64) -> Inputs {
    let edges = generate(Topology::Sparse, n, seed);
    let mut rng = Rng(seed ^ 0x1a);
    let inactive: Vec<bool> = (0..n).map(|_| rng.below(100) < inactive_percent).collect();
    let disabled: Vec<bool> = edges.iter().map(|_| rng.below(100) < disabled_percent).collect();
    let l_nodes = json!((0..n)
        .map(|v| if inactive[v as usize] { json!({"node":v.to_string(),"active":false}) } else { json!(v.to_string()) })
        .collect::<Vec<_>>());
    let l_edges = json!(edges
        .iter()
        .zip(&disabled)
        .map(|(&(a, b), &off)| if off {
            json!({"source":a.to_string(),"target":b.to_string(),"enabled":false})
        } else {
            json!({"source":a.to_string(),"target":b.to_string()})
        })
        .collect::<Vec<_>>());
    let f_nodes = json!((0..n).map(|v| v.to_string()).collect::<Vec<_>>());
    let f_edges = json!(edges.iter().map(|(a, b)| json!({"source":a.to_string(),"target":b.to_string()})).collect::<Vec<_>>());
    let effective: Vec<(u64, u64)> = edges
        .iter()
        .zip(&disabled)
        .filter(|&(&(a, b), &off)| !off && !inactive[a as usize] && !inactive[b as usize])
        .map(|(&e, _)| e)
        .collect();
    let e_edges = json!(effective.iter().map(|(a, b)| json!({"source":a.to_string(),"target":b.to_string()})).collect::<Vec<_>>());
    Inputs { n, edges, inactive, disabled, l_nodes, l_edges, f_nodes, f_edges, e_edges }
}

/// One timed import of an arm on a fresh server; returns nanoseconds.
async fn timed(arm: char, inp: &Inputs, metrics: bool) -> (u128, Router) {
    let app = router_with_config(config(arm == 'L', metrics));
    let instance = session(&app).await;
    let request = match arm {
        'L' => body(&instance, &inp.l_nodes, &inp.l_edges),
        'F' => body(&instance, &inp.f_nodes, &inp.f_edges),
        _ => body(&instance, &inp.f_nodes, &inp.e_edges),
    };
    let start = Instant::now();
    let (status, _) = send(&app, "POST", "/v1/feeder/import", Some(&instance), request).await;
    if arm == 'E' {
        // The B4 reference's flag store, built inside the window.
        let store: (Vec<(u64, u64)>, Vec<bool>, Vec<bool>, Vec<(u64, u64)>) = (
            inp.edges.clone(),
            inp.inactive.clone(),
            inp.disabled.clone(),
            inp.edges
                .iter()
                .zip(&inp.disabled)
                .filter(|&(&(a, b), &off)| !off && !inp.inactive[a as usize] && !inp.inactive[b as usize])
                .map(|(&e, _)| e)
                .collect(),
        );
        std::hint::black_box(&store);
    }
    let ns = start.elapsed().as_nanos();
    assert_eq!(status, StatusCode::CREATED, "arm {arm} import failed");
    (ns, app)
}

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let m = v.len() / 2;
    if v.len() % 2 == 0 { (v[m - 1] + v[m]) / 2.0 } else { v[m] }
}

fn phase_sums(text: &str) -> Value {
    let mut out = serde_json::Map::new();
    for line in text.lines() {
        if line.starts_with("knotrel_import_duration_seconds_sum") {
            let (key, value) = line.rsplit_once(' ').unwrap();
            out.insert(key.to_owned(), json!(value.parse::<f64>().unwrap_or(f64::NAN)));
        }
    }
    Value::Object(out)
}

async fn run(args: HashMap<String, String>) {
    let num = |k: &str| args.get(k).unwrap_or_else(|| panic!("--{k}")).parse::<u64>().unwrap();
    let inp = inputs(num("nodes"), num("seed"), num("inactive-percent"), num("disabled-percent"));
    let (pairs, warmup) = (num("pairs"), num("warmup"));
    let orders = [['L', 'F', 'E'], ['F', 'E', 'L'], ['E', 'L', 'F']];
    let mut samples: HashMap<char, Vec<f64>> = HashMap::new();
    for i in 0..(warmup + pairs) {
        let order = orders[(i % 3) as usize];
        let mut row = serde_json::Map::new();
        for arm in order {
            let (ns, _) = timed(arm, &inp, false).await;
            row.insert(arm.to_string(), json!(ns));
            if i >= warmup {
                samples.entry(arm).or_default().push(ns as f64);
            }
        }
        println!("{}", json!({"kind":"pair","index":i,"warmup":i < warmup,"order":order.iter().collect::<String>(),"ns":row}));
    }
    let ratio = |a: char, b: char| -> Value {
        let r: Vec<f64> = samples[&a].iter().zip(&samples[&b]).map(|(x, y)| x / y).collect();
        json!({"median_ratio": median(r.clone()), "min": r.iter().cloned().fold(f64::MAX, f64::min), "max": r.iter().cloned().fold(0.0, f64::max)})
    };
    let medians: HashMap<String, f64> = samples.iter().map(|(k, v)| (k.to_string(), median(v.clone()))).collect();
    // Untimed: body bytes and parse-only proxies.
    let bodies = [('L', body("x", &inp.l_nodes, &inp.l_edges)), ('F', body("x", &inp.f_nodes, &inp.f_edges)), ('E', body("x", &inp.f_nodes, &inp.e_edges))];
    let mut parse = serde_json::Map::new();
    for (arm, b) in &bodies {
        let mut t = Vec::new();
        for _ in 0..25 {
            let s = Instant::now();
            let v: sonic_rs::Value = sonic_rs::from_slice(b).unwrap();
            std::hint::black_box(&v);
            t.push(s.elapsed().as_nanos() as f64);
        }
        parse.insert(arm.to_string(), json!({"bytes": b.len(), "sonic_value_parse_ns_median": median(t)}));
    }
    // Server phases: one metrics-enabled import each of L and F.
    let mut phases = serde_json::Map::new();
    for arm in ['L', 'F', 'E'] {
        let (_, app) = timed(arm, &inp, true).await;
        let (_, text) = send(&app, "GET", "/metrics", None, Bytes::new()).await;
        phases.insert(arm.to_string(), phase_sums(&String::from_utf8_lossy(&text)));
    }
    println!("{}", json!({"kind":"summary","nodes":inp.n,"registered_edges":inp.edges.len(),
        "effective_edges": inp.e_edges.as_array().unwrap().len(),
        "medians_ns":medians, "L_over_E":ratio('L','E'), "F_over_E":ratio('F','E'), "L_over_F":ratio('L','F'),
        "bodies":parse, "server_phase_sums_s":phases}));
}

fn main() {
    let mut args = HashMap::new();
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        args.insert(k.trim_start_matches("--").to_owned(), it.next().unwrap_or_default());
    }
    tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap().block_on(run(args));
}
