//! Mechanism microbenchmarks for the hot-path audit.
//!
//! Each benchmark replicates one synchronization or allocation pattern from
//! `knotrel-server` in isolation; none calls Knotrel code. It measures the
//! cost of the pattern, not a request-level effect:
//!
//! - `job_track_release_watch`: the baseline outstanding-job counter, a
//!   `tokio::sync::watch` sender updated with `send_modify` on job start and
//!   on guard release (the guard holds a sender clone).
//! - `job_track_release_atomic`: the candidate counter, `AtomicUsize`
//!   increment/decrement with `Notify::notify_waiters` when it reaches zero.
//! - `http_counter_get_or_create` / `http_counter_cached_oncelock`: the
//!   reverted metric-handle cache (family map lookup versus cached handle).
//! - `clock_now_millis`: one millisecond clock read, as in feeder stamping.
//! - `body_1mib_to_vec` / `body_1mib_vec_from_unique`: copying a 1 MiB body
//!   versus converting a uniquely owned `Bytes` into `Vec<u8>`.
//!
//! Output: one JSON object per benchmark and thread count, with every
//! sample (nanoseconds per operation per thread) in run order.
//!
//! ```text
//! job-tracking [--samples N] [--operations N]
//! ```

use prometheus_client::metrics::{counter::Counter, family::Family};
use std::{
    hint::black_box,
    sync::{
        OnceLock,
        atomic::{AtomicUsize, Ordering},
    },
    time::Instant,
};
use tokio::sync::{Notify, watch};

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

type Labels = [(&'static str, &'static str); 3];

fn parse() -> (usize, usize) {
    let mut samples = 9;
    let mut operations = 1_000_000;
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        let value = args.next().and_then(|value| value.parse().ok());
        match (flag.as_str(), value) {
            ("--samples", Some(value)) if value > 0 => samples = value,
            ("--operations", Some(value)) if value > 0 => operations = value,
            _ => {
                eprintln!("usage: job-tracking [--samples N] [--operations N]");
                std::process::exit(2);
            }
        }
    }
    (samples, operations)
}

/// Runs `operation` `operations` times on each of `threads` threads and
/// returns nanoseconds per operation per thread (wall time / operations).
fn sample(threads: usize, operations: usize, operation: &(impl Fn() + Sync)) -> f64 {
    let clock = Instant::now();
    std::thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| {
                for _ in 0..operations {
                    operation();
                }
            });
        }
    });
    clock.elapsed().as_nanos() as f64 / operations as f64
}

fn report(name: &str, threads: usize, samples: usize, operations: usize, op: impl Fn() + Sync) {
    // One discarded warmup sample.
    sample(threads, operations / 10, &op);
    let values: Vec<f64> = (0..samples)
        .map(|_| sample(threads, operations, &op))
        .collect();
    println!(
        "{}",
        serde_json::json!({
            "schema": 1,
            "benchmark": name,
            "threads": threads,
            "operations_per_sample": operations,
            "ns_per_op": values,
        })
    );
}

fn main() {
    let (samples, operations) = parse();
    for threads in [1, 4] {
        let (sender, _receiver) = watch::channel(0_usize);
        report(
            "job_track_release_watch",
            threads,
            samples,
            operations,
            || {
                sender.send_modify(|count| *count += 1);
                let guard = sender.clone();
                guard.send_modify(|count| *count -= 1);
            },
        );
        let jobs = AtomicUsize::new(0);
        let idle = Notify::new();
        report(
            "job_track_release_atomic",
            threads,
            samples,
            operations,
            || {
                jobs.fetch_add(1, Ordering::AcqRel);
                if jobs.fetch_sub(1, Ordering::AcqRel) == 1 {
                    idle.notify_waiters();
                }
            },
        );
        let family = Family::<Labels, Counter>::default();
        let labels: Labels = [
            ("route", "/v1/operations"),
            ("method", "POST"),
            ("status_class", "2xx"),
        ];
        report(
            "http_counter_get_or_create",
            threads,
            samples,
            operations,
            || {
                family.get_or_create(black_box(&labels)).inc();
            },
        );
        let cached: OnceLock<Counter> = OnceLock::new();
        report(
            "http_counter_cached_oncelock",
            threads,
            samples,
            operations,
            || {
                cached
                    .get_or_init(|| family.get_or_create(&labels).clone())
                    .inc();
            },
        );
        let start = Instant::now();
        report("clock_now_millis", threads, samples, operations, || {
            black_box(start.elapsed().as_millis() as u64);
        });
    }
    let body = vec![b'x'; 1 << 20];
    let mut copies = Vec::new();
    let mut conversions = Vec::new();
    for _ in 0..samples {
        let buffers: Vec<_> = (0..64).map(|_| bytes::Bytes::from(body.clone())).collect();
        let clock = Instant::now();
        for buffer in &buffers {
            black_box(buffer.to_vec());
        }
        copies.push(clock.elapsed().as_nanos() as f64 / 64.0);
        let clock = Instant::now();
        for buffer in buffers {
            black_box(Vec::from(buffer));
        }
        conversions.push(clock.elapsed().as_nanos() as f64 / 64.0);
    }
    for (name, values) in [
        ("body_1mib_to_vec", copies),
        ("body_1mib_vec_from_unique", conversions),
    ] {
        println!(
            "{}",
            serde_json::json!({
                "schema": 1,
                "benchmark": name,
                "threads": 1,
                "operations_per_sample": 64,
                "ns_per_op": values,
            })
        );
    }
}
