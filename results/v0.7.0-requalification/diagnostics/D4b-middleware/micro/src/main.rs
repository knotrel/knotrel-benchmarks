//! D4b diagnostic (DIAGNOSTICS-PLAN-2.md): median of 15 repetitions of 1,000,000 calls of
//! the per-request work `track_http` does outside `next.run` (`d4b-variants.diff`).
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
fn main() {
    let iterations = 1_000_000u64;
    knotrel_server::d4b_middleware_micro(100_000);
    let mut per_call: Vec<f64> = (0..15).map(|_| knotrel_server::d4b_middleware_micro(iterations) as f64 / iterations as f64).collect();
    println!("{{\"kind\":\"micro\",\"iterations\":{iterations},\"ns_per_call\":{per_call:?}}}");
    per_call.sort_by(|a, b| a.partial_cmp(b).unwrap());
    println!("{{\"kind\":\"micro_summary\",\"median_ns_per_call\":{},\"min\":{},\"max\":{},\"per_37_request_window_us\":{}}}", per_call[7], per_call[0], per_call[14], per_call[7] * 37.0 / 1000.0);
}
