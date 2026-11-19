//! D4b diagnostic: checks that V2 (`KNOTREL_D4B_CACHED`) exports the same series as the
//! released path. Two lifecycle standalone servers with metrics on, the same requests
//! (batches of `link`/`cut`, `connected`, an unknown path, a malformed body); then the
//! `/metrics` series (order-insensitive; family maps do not keep order) with every sample
//! value replaced by `V` must be identical, and the
//! request counters must be equal including values.
use axum::{body::{Body, to_bytes}, http::Request};
use tower::ServiceExt;

fn config() -> knotrel_server::ServerConfig {
    knotrel_server::ServerConfig::new("127.0.0.1:0".parse().unwrap(), knotrel_core::EngineConfig::CompactBfs, 32)
        .unwrap()
        .with_topology_lifecycle(true)
        .unwrap()
        .with_metrics_enabled(true)
}

async fn traffic(app: &axum::Router) -> String {
    let bodies = [
        ("POST", "/v1/batch", r#"{"operations":[{"op":"link","source":"1","target":"2"},{"op":"set_node_active","node":"2","active":false}]}"#),
        ("POST", "/v1/batch", r#"{"operations":[{"op":"connected","source":"1","target":"2"}]}"#),
        ("POST", "/v1/batch", r#"{"operations":[{"op":"cut","source":"1","target":"2"}]}"#),
        ("POST", "/v1/batch", "not json"),
        ("GET", "/v1/nope", ""),
        ("GET", "/health", ""),
        ("PUT", "/v1/batch", ""),
    ];
    for _ in 0..3 {
        for (m, p, b) in bodies {
            let req = Request::builder().method(m).uri(p).header("content-type", "application/json").body(Body::from(b)).unwrap();
            let _ = to_bytes(app.clone().oneshot(req).await.unwrap().into_body(), 1 << 20).await.unwrap();
        }
    }
    let req = Request::builder().uri("/metrics").body(Body::empty()).unwrap();
    String::from_utf8(to_bytes(app.clone().oneshot(req).await.unwrap().into_body(), 1 << 24).await.unwrap().to_vec()).unwrap()
}

fn main() {
    let rt = tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap();
    let released = rt.block_on(traffic(&knotrel_server::router_with_config(config())));
    unsafe { std::env::set_var("KNOTREL_D4B_CACHED", "1") };
    let cached = rt.block_on(traffic(&knotrel_server::router_with_config(config())));
    let shape = |t: &str| t.lines().filter(|l| !l.contains("instance") && !l.contains("start_time") && !l.contains("uptime"))
        .map(|l| if l.starts_with('#') { l.to_owned() } else { l.rsplit_once(' ').map(|(k, _)| format!("{k} V")).unwrap_or_default() })
        .collect::<std::collections::BTreeSet<_>>();
    let counters = |t: &str| t.lines().filter(|l| l.starts_with("knotrel_http_requests_total") || l.starts_with("knotrel_http_request_duration_seconds_count")).map(str::to_owned).collect::<std::collections::BTreeSet<_>>();
    let same_shape = shape(&released) == shape(&cached);
    let same_counts = counters(&released) == counters(&cached);
    println!("{{\"kind\":\"export_check\",\"series_lines\":{},\"same_series\":{same_shape},\"same_http_counts\":{same_counts},\"http_count_lines\":{}}}", shape(&released).len(), counters(&released).len());
    for l in counters(&released) { println!("{l}"); }
    if !same_shape { for a in shape(&released).symmetric_difference(&shape(&cached)) { println!("DIFF {a}"); } }
}
