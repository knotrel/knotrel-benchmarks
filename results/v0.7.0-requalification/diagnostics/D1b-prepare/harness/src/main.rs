//! D1b diagnostic (DIAGNOSTICS-PLAN-2.md): import `prepare` sub-phase profile.
//! Not part of the qualification.
//!
//! Same inputs and arms as D1 (sparse, `--seed`, flags from `Rng(seed ^ 0x1a)`;
//! L lifecycle full topology with flags, F plain full topology all active, E plain
//! effective graph). Each import goes to a fresh source-managed server in process; the
//! instrumented candidate build (`d1b-instrument.diff`) accumulates sub-phase times in
//! `knotrel_core::diag_d1`, reset before and read after each import.
//!
//! ```text
//! d1b-prepare --nodes 10000 --seed 5000001 --inactive-percent 60 --disabled-percent 30 --imports 30 --warmup 3
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

fn config(lifecycle: bool) -> ServerConfig {
    ServerConfig::new("127.0.0.1:0".parse().unwrap(), knotrel_core::EngineConfig::CompactBfs, 32)
        .unwrap()
        .with_mode(ServerMode::SourceManaged)
        .with_topology_lifecycle(lifecycle)
        .expect("compact-bfs supports lifecycle")
        .with_metrics_enabled(false)
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

fn body(instance: &str, nodes: &Value, edges: &Value) -> Bytes {
    Bytes::from(
        json!({"mode":"create_only","instance_id":instance,"graph_id":"default","source_id":"src",
               "source_epoch":"e1","source_position":"p0","feeder_session_id":"s","feeder_epoch":1,
               "nodes":nodes,"edges":edges})
        .to_string(),
    )
}

fn main() {
    let mut args = HashMap::new();
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        args.insert(k.trim_start_matches("--").to_owned(), it.next().unwrap_or_default());
    }
    let num = |k: &str| args.get(k).unwrap_or_else(|| panic!("--{k}")).parse::<u64>().unwrap();
    let (n, seed) = (num("nodes"), num("seed"));
    let (inactive_percent, disabled_percent) = (num("inactive-percent"), num("disabled-percent"));
    let (imports, warmup) = (num("imports"), num("warmup"));
    let edges = generate(Topology::Sparse, n, seed);
    let mut rng = Rng(seed ^ 0x1a);
    let inactive: Vec<bool> = (0..n).map(|_| rng.below(100) < inactive_percent).collect();
    let disabled: Vec<bool> = edges.iter().map(|_| rng.below(100) < disabled_percent).collect();
    let l_nodes = json!((0..n)
        .map(|v| if inactive[v as usize] { json!({"node":v.to_string(),"active":false}) } else { json!(v.to_string()) })
        .collect::<Vec<_>>());
    let l_edges = json!(edges.iter().zip(&disabled).map(|(&(a, b), &off)| if off {
        json!({"source":a.to_string(),"target":b.to_string(),"enabled":false})
    } else {
        json!({"source":a.to_string(),"target":b.to_string()})
    }).collect::<Vec<_>>());
    let f_nodes = json!((0..n).map(|v| v.to_string()).collect::<Vec<_>>());
    let f_edges = json!(edges.iter().map(|(a, b)| json!({"source":a.to_string(),"target":b.to_string()})).collect::<Vec<_>>());
    let e_edges = json!(edges.iter().zip(&disabled)
        .filter(|&(&(a, b), &off)| !off && !inactive[a as usize] && !inactive[b as usize])
        .map(|(&(a, b), _)| json!({"source":a.to_string(),"target":b.to_string()})).collect::<Vec<_>>());
    let rt = tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap();
    println!("{}", json!({"kind":"setup","nodes":n,"registered_edges":edges.len(),
        "effective_edges":e_edges.as_array().unwrap().len(),"phases":knotrel_core::diag_d1::NAMES}));
    let orders = [['L', 'F', 'E'], ['F', 'E', 'L'], ['E', 'L', 'F']];
    for i in 0..(warmup + imports) {
        let order = orders[(i % 3) as usize];
        let mut row = serde_json::Map::new();
        for arm in order {
            let app = router_with_config(config(arm == 'L'));
            let instance = rt.block_on(session(&app));
            let request = match arm {
                'L' => body(&instance, &l_nodes, &l_edges),
                'F' => body(&instance, &f_nodes, &f_edges),
                _ => body(&instance, &f_nodes, &e_edges),
            };
            knotrel_core::diag_d1::reset();
            let start = Instant::now();
            let (status, _) = rt.block_on(send(&app, "POST", "/v1/feeder/import", Some(&instance), request));
            let total = start.elapsed().as_nanos() as u64;
            let phases = knotrel_core::diag_d1::snapshot();
            assert_eq!(status, StatusCode::CREATED, "arm {arm}");
            row.insert(arm.to_string(), json!({"total_ns":total,"phases_ns":phases.to_vec()}));
        }
        println!("{}", json!({"kind":"round","index":i,"warmup":i < warmup,"order":order.iter().collect::<String>(),"arms":row}));
    }
}
