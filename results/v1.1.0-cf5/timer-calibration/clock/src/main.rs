use std::collections::BTreeMap;
use std::hint::black_box;
use std::time::Instant;

fn spin(n: u64) -> u64 { let mut x = 0u64; for i in 0..n { x = black_box(x.wrapping_add(i)); } x }

fn main() {
    // a) tick: back-to-back deltas
    let mut hist: BTreeMap<u128, u64> = BTreeMap::new();
    let mut prev = Instant::now();
    for _ in 0..10_000_000 { let now = Instant::now(); *hist.entry((now - prev).as_nanos()).or_default() += 1; prev = now; }
    let nonzero_min = hist.keys().find(|&&k| k > 0).copied().unwrap();
    let zero = *hist.get(&0).unwrap_or(&0);
    let top: Vec<_> = { let mut v: Vec<_> = hist.iter().collect(); v.sort_by(|a, b| b.1.cmp(a.1)); v.into_iter().take(6).map(|(k, c)| format!("{k}:{c}")).collect() };
    // b) now() cost
    let n = 50_000_000u64;
    let s = Instant::now(); for _ in 0..n { black_box(Instant::now()); } let now_cost = s.elapsed().as_nanos() as f64 / n as f64;
    // c) empty interval (in-interval clock overhead), harness pattern
    let m = 10_000_000usize; let mut v: Vec<u128> = Vec::with_capacity(m);
    for _ in 0..m { let st = Instant::now(); black_box(()); v.push(st.elapsed().as_nanos()); }
    let mean_empty = v.iter().sum::<u128>() as f64 / m as f64;
    v.sort_unstable(); let p50 = v[m / 2]; let p99 = v[m * 99 / 100]; let max_empty = v[m - 1];
    // d) per-op summed vs aggregate for a fixed-cost op; and harness-pattern per-op cost
    let k = 1_000_000usize;
    for &iters in &[1u64, 20, 100] {
        let s = Instant::now(); for _ in 0..k { black_box(spin(black_box(iters))); } let agg = s.elapsed().as_nanos() as f64;
        let mut sum = 0u128; let mut pushes: Vec<u128> = Vec::with_capacity(k);
        let s = Instant::now();
        for _ in 0..k { let st = Instant::now(); black_box(spin(black_box(iters))); let e = st.elapsed().as_nanos(); sum += e; pushes.push(e); }
        let wall = s.elapsed().as_nanos() as f64;
        println!("op spin({iters}): agg/op {:.2} ns, summed-per-op/op {:.2} ns, instrumented-wall/op {:.2} ns -> bias(summed-agg)/op {:.2}, in-window instrumentation/op {:.2}",
            agg / k as f64, sum as f64 / k as f64, wall / k as f64, (sum as f64 - agg) / k as f64, (wall - agg) / k as f64);
    }
    println!("tick: min nonzero delta {nonzero_min} ns, zero deltas {zero}/10000000, top {top:?}");
    println!("now() cost {now_cost:.2} ns; empty interval mean {mean_empty:.2} p50 {p50} p99 {p99} max {max_empty}");
}
