//! ETag-on-412 evaluation (DIAGNOSTICS-PLAN-3.md), against the diagnostic server build
//! `etag412.diff`. Not part of the qualification.
//!
//! In process, through the real router: a source-managed lifecycle server, a small graph.
//! 1. Consistency: after `k` event batches advance the state, a replacement import with the
//!    stale token gets 412; its `ETag` header must equal the token `GET /v1/stats` returns
//!    right after (nothing else runs), and a retry with it must succeed (201).
//! 2. Staleness: the same, but one more event batch is applied between the 412 and the retry
//!    (a concurrent change after the lock was released): the retry must get 412 again, with a
//!    newer token, exactly as a token read from `/v1/stats` would.
use axum::{Router, body::{Body, to_bytes}, http::{Request, StatusCode}};
use serde_json::{Value, json};
use tower::ServiceExt;

struct Feeder { app: Router, instance: String, generation: u64, sequence: u64, position: String, imports: u64 }

impl Feeder {
    async fn send(&self, method: &str, path: &str, if_match: Option<&str>, body: String) -> (StatusCode, Option<String>, Value) {
        let mut r = Request::builder().method(method).uri(path).header("content-type", "application/json")
            .header("x-knotrel-instance-id", self.instance.as_str());
        if let Some(t) = if_match { r = r.header("if-match", t); }
        let resp = self.app.clone().oneshot(r.body(Body::from(body)).unwrap()).await.unwrap();
        let status = resp.status();
        let etag = resp.headers().get("etag").map(|v| v.to_str().unwrap().to_owned());
        let bytes = to_bytes(resp.into_body(), 1 << 24).await.unwrap();
        (status, etag, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
    }
    fn import_body(&self, mode: &str, position: &str) -> String {
        let nodes: Vec<String> = (0..200).map(|v| v.to_string()).collect();
        let edges: Vec<Value> = (0..199).map(|v| json!({"source": v.to_string(), "target": (v + 1).to_string()})).collect();
        json!({"mode":mode,"instance_id":self.instance,"graph_id":"default","source_id":"src","source_epoch":"e1",
               "source_position":position,"feeder_session_id":"s","feeder_epoch":1,"nodes":nodes,"edges":edges}).to_string()
    }
    async fn import(&mut self, mode: &str, if_match: Option<&str>) -> (StatusCode, Option<String>, Value) {
        self.imports += 1;
        let position = format!("i{}", self.imports);
        let out = self.send("POST", "/v1/feeder/import", if_match, self.import_body(mode, &position)).await;
        if out.0 == StatusCode::CREATED {
            self.generation = out.2["generation"].as_u64().unwrap();
            self.sequence = 0;
            self.position = position;
        }
        out
    }
    async fn events(&mut self, toggles: u64) {
        let mut events = Vec::new();
        for k in 0..toggles {
            let sequence = self.sequence + 1;
            let position = format!("e{}-{sequence}", self.generation);
            let op = if (self.sequence / 1) % 2 == 0 { "link" } else { "cut" };
            events.push(json!({"event_id":format!("ev-{}-{sequence}", self.generation),"delivery_sequence":sequence,
                "prev_delivery_sequence":self.sequence,"source_position":position,"prev_source_position":self.position,
                "op":op,"source":"1000","target":(1001 + k % 1).to_string()}));
            self.sequence = sequence;
            self.position = position;
        }
        let body = json!({"instance_id":self.instance,"graph_id":"default","generation":self.generation,"feeder_session_id":"s",
            "feeder_epoch":1,"source_id":"src","source_epoch":"e1","events":events}).to_string();
        let (status, _, reply) = self.send("POST", "/v1/feeder/events", None, body).await;
        assert_eq!(status, StatusCode::OK, "{reply}");
    }
    async fn stats_etag(&self) -> String {
        let (status, etag, _) = self.send("GET", "/v1/stats", None, String::new()).await;
        assert_eq!(status, StatusCode::OK);
        etag.unwrap()
    }
}

async fn run() -> Value {
    let config = knotrel_server::ServerConfig::new("127.0.0.1:0".parse().unwrap(), knotrel_core::EngineConfig::CompactBfs, 32).unwrap()
        .with_mode(knotrel_server::ServerMode::SourceManaged).with_topology_lifecycle(true).unwrap();
    let app = knotrel_server::router_with_config(config);
    let info: Value = {
        let resp = app.clone().oneshot(Request::get("/v1/info").body(Body::empty()).unwrap()).await.unwrap();
        serde_json::from_slice(&to_bytes(resp.into_body(), 1 << 20).await.unwrap()).unwrap()
    };
    let mut f = Feeder { app, instance: info["instance_id"].as_str().unwrap().to_owned(), generation: 0, sequence: 0, position: String::new(), imports: 0 };
    let session = json!({"instance_id":f.instance,"feeder_session_id":"s","feeder_epoch":1,"lease_duration_ms":60000}).to_string();
    assert_eq!(f.send("POST", "/v1/feeder/session", None, session).await.0, StatusCode::OK);
    let (status, mut token, _) = f.import("create_only", None).await;
    assert_eq!(status, StatusCode::CREATED);
    let mut consistency = Vec::new();
    for k in 1..=50u64 {
        let stale = token.clone().unwrap();
        f.events(k).await;
        let (s412, tag412, _) = f.import("replace", Some(&stale)).await;
        let stats = f.stats_etag().await;
        let (retry, next, _) = f.import("replace", tag412.as_deref()).await;
        consistency.push(json!({"k":k,"status":s412.as_u16(),"etag_412":tag412,"stats_etag":stats,"equal":tag412.as_deref()==Some(stats.as_str()),"retry":retry.as_u16()}));
        token = next;
    }
    let mut staleness = Vec::new();
    for k in 1..=50u64 {
        let stale = token.clone().unwrap();
        f.events(k).await;
        let (s412, tag412, _) = f.import("replace", Some(&stale)).await;
        f.events(1).await; // a change after the lock was released
        let (retry, tag_again, _) = f.import("replace", tag412.as_deref()).await;
        let (fresh, next, _) = f.import("replace", tag_again.as_deref()).await;
        staleness.push(json!({"k":k,"first":s412.as_u16(),"retry_with_412_etag":retry.as_u16(),"second_etag_newer":tag_again!=tag412,"retry_with_second":fresh.as_u16()}));
        token = next;
    }
    let ok_c = consistency.iter().filter(|r| r["status"]==412 && r["equal"]==true && r["retry"]==201).count();
    let ok_s = staleness.iter().filter(|r| r["first"]==412 && r["retry_with_412_etag"]==412 && r["second_etag_newer"]==true && r["retry_with_second"]==201).count();
    json!({"kind":"summary","consistency_trials":consistency.len(),"consistency_ok":ok_c,"staleness_trials":staleness.len(),"staleness_ok":ok_s,
           "consistency":consistency,"staleness":staleness})
}

fn main() {
    let rt = tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap();
    println!("{}", rt.block_on(run()));
}
