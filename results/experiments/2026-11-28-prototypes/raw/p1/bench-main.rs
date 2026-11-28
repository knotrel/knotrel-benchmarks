use knotrel_core::Graph;
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;
use std::sync::{Barrier, Mutex};
use std::time::Instant;

// Per-thread counters: no shared atomics on the allocation path.
thread_local! {
    static ALLOCS: Cell<u64> = const { Cell::new(0) };
    static BYTES: Cell<u64> = const { Cell::new(0) };
    static NET: Cell<i64> = const { Cell::new(0) };
}
struct Counting;
unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        let _ = ALLOCS.try_with(|c| c.set(c.get() + 1));
        let _ = BYTES.try_with(|c| c.set(c.get() + l.size() as u64));
        let _ = NET.try_with(|c| c.set(c.get() + l.size() as i64));
        unsafe { System.alloc(l) }
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        let _ = NET.try_with(|c| c.set(c.get() - l.size() as i64));
        unsafe { System.dealloc(p, l) }
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        let _ = ALLOCS.try_with(|c| c.set(c.get() + 1));
        let _ = BYTES.try_with(|c| c.set(c.get() + n as u64));
        let _ = NET.try_with(|c| c.set(c.get() + n as i64 - l.size() as i64));
        unsafe { System.realloc(p, l, n) }
    }
}
#[global_allocator]
static A: Counting = Counting;
fn net() -> i64 { NET.with(|c| c.get()) }
fn counts() -> (u64, u64) { (ALLOCS.with(|c| c.get()), BYTES.with(|c| c.get())) }

struct Rng(u64);
impl Rng { fn next(&mut self) -> u64 { self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17; self.0 } fn below(&mut self, n: u64) -> u64 { self.next() % n } }
fn build(n: u64, edges: impl Iterator<Item = (u64, u64)>) -> Graph { let mut g = Graph::new(); for v in 0..n { g.add_node(v); } for (a, b) in edges { if a != b { let _ = g.link(a, b); } } g }

fn pct(v: &mut Vec<u64>, p: f64) -> f64 { v.sort_unstable(); v[((v.len() - 1) as f64 * p) as usize] as f64 }

fn main() {
    let mode = std::env::args().nth(1).unwrap_or_default();
    let mut r = Rng(0x9e3779b97f4a7c15);
    let n = 100_000u64;
    if mode != "retain" {
        let random = build(n, (0..2 * n).map(|_| (r.below(n), r.below(n))).collect::<Vec<_>>().into_iter());
        // S2: random graph plus a separate 64-vertex path component (ids n..n+64)
        let mut s2 = build(n, (0..2 * n).map(|_| (r.below(n), r.below(n))).collect::<Vec<_>>().into_iter());
        for i in 0..63 { s2.link(n + i, n + i + 1).unwrap(); }
        let chain = build(n, (1..n).map(|i| (i - 1, i)));
        let cycle = build(n, (1..n).map(|i| (i - 1, i)).chain([(n - 1, 0)]));
        let split = build(n, (1..n).filter(|&i| i != n / 2).map(|i| (i - 1, i)));
        let s1q: Vec<_> = (0..4000).map(|_| (r.below(n), r.below(n))).collect();
        let s2q: Vec<_> = (0..4000).map(|i| (n + (i % 64), r.below(n))).collect();
        let loads: Vec<(&str, &Graph, Vec<(u64, u64)>)> = vec![
            ("S1 random short", &random, s1q),
            ("S2 small->giant disc", &s2, s2q),
            ("L1 chain ends", &chain, vec![(0, n - 1); 30]),
            ("L2 cycle opposite", &cycle, (0..30).map(|i| (i, i + n / 2)).collect()),
            ("L3 split chain disc", &split, vec![(0, n - 1); 30]),
        ];
        for (name, g, qs) in &loads {
            for &threads in &[1usize, 4, 8, 16] {
                let out = Mutex::new((Vec::new(), 0u64, 0u64, 0u64));
                let bar = Barrier::new(threads);
                std::thread::scope(|sc| {
                    for t in 0..threads {
                        let (g, qs, out, bar) = (*g, qs, &out, &bar);
                        sc.spawn(move || {
                            // warm-up: one pass
                            for &(a, b) in qs.iter() { std::hint::black_box(g.connected(a, b).unwrap()); }
                            bar.wait();
                            let (a0, b0) = counts();
                            let mut lat = Vec::with_capacity(qs.len() * 3);
                            for rep in 0..3 { for i in 0..qs.len() { let (a, b) = qs[(i + t * 7 + rep) % qs.len()]; let s = Instant::now(); std::hint::black_box(g.connected(a, b).unwrap()); lat.push(s.elapsed().as_nanos() as u64); } }
                            let (a1, b1) = counts();
                            let n = lat.len() as u64;
                            let mut o = out.lock().unwrap(); o.0.extend(lat); o.1 += a1 - a0 - 0; o.2 += b1 - b0; o.3 += n;
                        });
                    }
                });
                let mut o = out.into_inner().unwrap();
                // the latency Vec itself is preallocated before a0, so counts are query-only
                println!("{name}\t{threads}\tp50_ns {:.0}\tp99_ns {:.0}\tallocs/q {:.3}\tbytes/q {:.0}", pct(&mut o.0, 0.5), pct(&mut o.0, 0.99), o.1 as f64 / o.3 as f64, o.2 as f64 / o.3 as f64);
            }
        }
    }
    if mode != "latency" {
        // P: one large query per thread (chain of 1,000,000 ends), then 10,000 short ones.
        let big_n = 1_000_000u64;
        let big = build(big_n, (1..big_n).map(|i| (i - 1, i)));
        let small = build(n, (0..2 * n).map(|_| (r.below(n), r.below(n))).collect::<Vec<_>>().into_iter());
        let sq: Vec<_> = (0..10_000).map(|_| (r.below(n), r.below(n))).collect();
        for &threads in &[1usize, 16] {
            let nets = Mutex::new(vec![(0i64, 0i64, 0i64); threads]);
            let bar = Barrier::new(threads + 1);
            std::thread::scope(|sc| {
                for t in 0..threads {
                    let (big, small, sq, nets, bar) = (&big, &small, &sq, &nets, &bar);
                    sc.spawn(move || {
                        let base = net();
                        std::hint::black_box(big.connected(0, big_n - 1).unwrap());
                        let after_big = net() - base;
                        for &(a, b) in sq { std::hint::black_box(small.connected(a, b).unwrap()); }
                        let after_small = net() - base;
                        nets.lock().unwrap()[t] = (0, after_big, after_small);
                        bar.wait(); // keep the thread (and its scratch) alive until measured
                        bar.wait();
                    });
                }
                bar.wait();
                let v = nets.lock().unwrap().clone();
                let max_big = v.iter().map(|x| x.1).max().unwrap();
                let sum_small: i64 = v.iter().map(|x| x.2).sum();
                let max_small = v.iter().map(|x| x.2).max().unwrap();
                println!("P retain\t{threads}\tafter_large_max_KiB {:.1}\tafter_10k_small_max_KiB {:.1}\tafter_10k_small_total_KiB {:.1}", max_big as f64 / 1024.0, max_small as f64 / 1024.0, sum_small as f64 / 1024.0);
                bar.wait();
            });
        }
    }
}
