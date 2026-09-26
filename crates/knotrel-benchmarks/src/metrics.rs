//! Per-operation latency summaries; sorting runs after the measured workload.

use serde::Serialize;

#[derive(Debug, Serialize)]
pub(crate) struct Latency {
    count: usize,
    total_ns: u128,
    min_ns: u128,
    p50_ns: u128,
    p95_ns: u128,
    p99_ns: u128,
    max_ns: u128,
}

impl Latency {
    /// Sorts nonempty samples in O(n log n) time and computes nearest-rank
    /// percentiles: rank = ceil(p*n/100), using one-based ranks. The workload
    /// guarantees at least one sample in each operation class. u128 rank
    /// arithmetic avoids overflowing usize for large sample counts.
    pub(crate) fn from_samples(mut samples: Vec<u128>) -> Self {
        assert!(
            !samples.is_empty(),
            "each operation has at least one sample"
        );
        samples.sort_unstable();
        let percentile =
            |percent: u128| samples[((samples.len() as u128 * percent).div_ceil(100) - 1) as usize];
        Self {
            count: samples.len(),
            total_ns: samples.iter().sum(),
            min_ns: samples[0],
            p50_ns: percentile(50),
            p95_ns: percentile(95),
            p99_ns: percentile(99),
            max_ns: samples[samples.len() - 1],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn percentiles_use_nearest_rank_with_short_and_unsorted_samples() {
        let summary = Latency::from_samples(vec![40, 10, 30, 20]);
        assert_eq!(summary.count, 4);
        assert_eq!(summary.total_ns, 100);
        assert_eq!(
            (
                summary.min_ns,
                summary.p50_ns,
                summary.p95_ns,
                summary.p99_ns,
                summary.max_ns
            ),
            (10, 20, 40, 40, 40)
        );
        let singleton = Latency::from_samples(vec![8]);
        assert_eq!(
            (
                singleton.min_ns,
                singleton.p50_ns,
                singleton.p99_ns,
                singleton.max_ns
            ),
            (8, 8, 8, 8)
        );
    }
}
