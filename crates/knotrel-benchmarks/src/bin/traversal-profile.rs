//! Structural BFS/DFS counts; never use this instrumented binary for timing.
use knotrel_benchmarks::{
    Config, Operation, Workload, WorkloadKind, generate_with_query_percent,
    traversal::{
        BitSearchSpace, DequeSearchSpace, Graph, QueueStats, ScratchStats, SearchSpace, SearchStats,
    },
};
use knotrel_core::{Graph as ProductionGraph, ReferenceGraph};
use serde::Serialize;
use serde_json::json;
use std::error::Error;

const DEFAULT_ROUNDS: usize = 10;
const DIAGNOSTIC_SEED: u64 = 42;
const LEDGER_SCHEMA_VERSION: u32 = 2;
const LEDGER_FLAG: &str = "--scratch-ledger";
const FIFO_FLAG: &str = "--fifo-ledger";
const FIFO_SCHEMA_VERSION: u32 = 3;
const USAGE: &str =
    "usage: traversal-profile N WORKLOAD QUERY_PERCENT [ROUNDS [--scratch-ledger|--fifo-ledger]]";

#[derive(Clone, Copy, Serialize)]
#[serde(rename_all = "kebab-case")]
enum ScratchVariant {
    FreshEpoch,
    ReusedEpoch,
    FreshPacked,
    ReusedPacked,
}

#[derive(Default, Serialize)]
struct OperationCounts {
    cut: usize,
    link: usize,
    connected: usize,
    query_true: usize,
    query_false: usize,
}

#[derive(Serialize)]
struct QueryLedger {
    operation_index: usize,
    source: u64,
    target: u64,
    expected: bool,
    graph: SearchStats,
    scratch: [ScratchStats; 4],
}

#[derive(Serialize)]
struct LedgerReport {
    schema_version: u32,
    scope: &'static str,
    representation: &'static str,
    retention: &'static str,
    config: Config,
    workload: &'static str,
    query_percent: Option<u8>,
    trace_fingerprint_fnv1a64: String,
    epoch_element_bytes: usize,
    packed_element_bytes: usize,
    queue_element_bytes: usize,
    variants: [ScratchVariant; 4],
    counts: OperationCounts,
    queries: Vec<QueryLedger>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
struct FifoWork {
    enqueues: usize,
    expanded_vertices: usize,
    examined_arcs: usize,
    peak_pending_frontier: usize,
}

fn fifo_work(stats: SearchStats, queue: QueueStats) -> FifoWork {
    FifoWork {
        enqueues: queue.enqueues,
        expanded_vertices: stats.expanded_vertices,
        examined_arcs: stats.examined_arcs,
        peak_pending_frontier: stats.peak_frontier,
    }
}

#[derive(Serialize)]
struct FifoStorage {
    peak_logical_len: usize,
    growth_events: usize,
    peak_capacity_bytes: usize,
    final_capacity_bytes: usize,
    mark_initialized_elements: usize,
    mark_cleared_elements: usize,
    mark_capacity_bytes: usize,
}

fn fifo_storage(stats: SearchStats, scratch: ScratchStats, queue: QueueStats) -> FifoStorage {
    FifoStorage {
        peak_logical_len: stats.peak_buffer_len,
        growth_events: scratch.queue_growth_events,
        peak_capacity_bytes: queue.peak_capacity_bytes,
        final_capacity_bytes: queue.final_capacity_bytes,
        mark_initialized_elements: scratch.mark_initialized_elements,
        mark_cleared_elements: scratch.mark_cleared_elements,
        mark_capacity_bytes: scratch.mark_capacity_bytes,
    }
}

#[derive(Serialize)]
struct FifoQuery {
    operation_index: usize,
    source: u64,
    target: u64,
    expected: bool,
    work: FifoWork,
    queues: [FifoStorage; 4],
}

#[derive(Serialize)]
struct FifoReport {
    schema_version: u32,
    scope: &'static str,
    counter_semantics: &'static str,
    config: Config,
    workload: &'static str,
    query_percent: Option<u8>,
    trace_fingerprint_fnv1a64: String,
    mark_element_bytes: usize,
    queue_element_bytes: usize,
    variants: [FifoVariant; 4],
    exact_order_checked_per_query: bool,
    counts: OperationCounts,
    queries: Vec<FifoQuery>,
}

#[derive(Serialize)]
#[serde(rename_all = "kebab-case")]
enum FifoVariant {
    FreshVec,
    ReusedVec,
    FreshDeque,
    ReusedDeque,
}

fn fifo_ledger(
    config: Config,
    kind: WorkloadKind,
    percent: u8,
    trace: &Workload,
    fingerprint: u64,
) -> Result<(), Box<dyn Error>> {
    let mut graph = Graph::new();
    let mut production = ProductionGraph::new();
    let mut reference = ReferenceGraph::new();
    for node in 0..config.nodes {
        assert!(graph.add_node(node));
        assert!(production.add_node(node));
        assert!(reference.add_node(node));
    }
    for &(source, target) in &trace.initial_edges {
        assert!(graph.link(source, target)?);
        assert!(production.link(source, target)?);
        assert!(reference.link(source, target)?);
    }
    let mut reused_vec = BitSearchSpace::with_order_recording();
    let mut reused_deque = DequeSearchSpace::with_order_recording();
    let (mut uncounted_vec, mut uncounted_deque) =
        (BitSearchSpace::default(), DequeSearchSpace::default());
    let mut counts = OperationCounts::default();
    let mut queries = Vec::new();
    for (operation_index, operation) in trace.operations.iter().enumerate() {
        match *operation {
            Operation::Link { source, target } => {
                assert!(graph.link(source, target)?);
                assert!(production.link(source, target)?);
                assert!(reference.link(source, target)?);
                counts.link += 1;
            }
            Operation::Cut { source, target } => {
                assert!(graph.cut(source, target)?);
                assert!(production.cut(source, target)?);
                assert!(reference.cut(source, target)?);
                counts.cut += 1;
            }
            Operation::Connected {
                source,
                target,
                expected,
            } => {
                let mut fresh_vec = BitSearchSpace::with_order_recording();
                let mut fresh_deque = DequeSearchSpace::with_order_recording();
                assert_eq!(
                    graph.search_bits::<true>(source, target, &mut fresh_vec)?,
                    expected
                );
                assert_eq!(
                    graph.search_bits::<true>(source, target, &mut reused_vec)?,
                    expected
                );
                assert_eq!(
                    graph.search_deque::<true>(source, target, &mut fresh_deque)?,
                    expected
                );
                assert_eq!(
                    graph.search_deque::<true>(source, target, &mut reused_deque)?,
                    expected
                );
                assert_eq!(
                    graph.search_bits::<false>(source, target, &mut uncounted_vec)?,
                    expected
                );
                assert_eq!(
                    graph.search_deque::<false>(source, target, &mut uncounted_deque)?,
                    expected
                );
                assert_eq!(production.connected(source, target)?, expected);
                assert_eq!(reference.connected(source, target)?, expected);
                assert_eq!(fresh_vec.recorded_order(), reused_vec.recorded_order());
                assert_eq!(fresh_vec.recorded_order(), fresh_deque.recorded_order());
                assert_eq!(fresh_vec.recorded_order(), reused_deque.recorded_order());
                let work = fifo_work(fresh_vec.stats(), fresh_vec.queue_stats());
                assert_eq!(
                    work,
                    fifo_work(reused_vec.stats(), reused_vec.queue_stats())
                );
                assert_eq!(
                    work,
                    fifo_work(fresh_deque.stats(), fresh_deque.queue_stats())
                );
                assert_eq!(
                    work,
                    fifo_work(reused_deque.stats(), reused_deque.queue_stats())
                );
                let queues = [
                    fifo_storage(
                        fresh_vec.stats(),
                        fresh_vec.scratch_stats(),
                        fresh_vec.queue_stats(),
                    ),
                    fifo_storage(
                        reused_vec.stats(),
                        reused_vec.scratch_stats(),
                        reused_vec.queue_stats(),
                    ),
                    fifo_storage(
                        fresh_deque.stats(),
                        fresh_deque.scratch_stats(),
                        fresh_deque.queue_stats(),
                    ),
                    fifo_storage(
                        reused_deque.stats(),
                        reused_deque.scratch_stats(),
                        reused_deque.queue_stats(),
                    ),
                ];
                for (baseline, candidate) in [(0, 2), (1, 3)] {
                    assert_eq!(
                        queues[baseline].mark_initialized_elements,
                        queues[candidate].mark_initialized_elements
                    );
                    assert_eq!(
                        queues[baseline].mark_cleared_elements,
                        queues[candidate].mark_cleared_elements
                    );
                    assert_eq!(
                        queues[baseline].mark_capacity_bytes,
                        queues[candidate].mark_capacity_bytes
                    );
                }
                counts.connected += 1;
                counts.query_true += usize::from(expected);
                counts.query_false += usize::from(!expected);
                queries.push(FifoQuery {
                    operation_index,
                    source,
                    target,
                    expected,
                    work,
                    queues,
                });
            }
        }
        assert_eq!(graph.node_count(), production.node_count());
        assert_eq!(graph.node_count(), reference.node_count());
        assert_eq!(graph.edge_count(), production.edge_count());
        assert_eq!(graph.edge_count(), reference.edge_count());
    }
    let report = FifoReport {
        schema_version: FIFO_SCHEMA_VERSION,
        scope: "Packed-bit queue-only structural comparison; no timings",
        counter_semantics: "Pending frontier excludes the expanded vertex. Vec logical storage retains history; VecDeque stores pending entries. pop_front and clear do not shrink capacity. Final capacity is before scratch drop; fresh retains zero between queries. Capacity excludes metadata/order-recording/oracles and is not RSS, allocator traffic or bytes copied. Work counters are asserted equal across all four variants.",
        config,
        workload: kind.name(),
        query_percent: kind.is_sustained().then_some(percent),
        trace_fingerprint_fnv1a64: format!("{fingerprint:016x}"),
        mark_element_bytes: size_of::<u64>(),
        queue_element_bytes: size_of::<usize>(),
        variants: [
            FifoVariant::FreshVec,
            FifoVariant::ReusedVec,
            FifoVariant::FreshDeque,
            FifoVariant::ReusedDeque,
        ],
        exact_order_checked_per_query: true,
        counts,
        queries,
    };
    serde_json::to_writer(std::io::stdout().lock(), &report)?;
    Ok(())
}

fn scratch_ledger(
    config: Config,
    kind: WorkloadKind,
    percent: u8,
    trace: &Workload,
    fingerprint: u64,
) -> Result<(), Box<dyn Error>> {
    let mut graph = Graph::new();
    let mut production = ProductionGraph::new();
    let mut reference = ReferenceGraph::new();
    for node in 0..config.nodes {
        assert!(graph.add_node(node));
        assert!(production.add_node(node));
        assert!(reference.add_node(node));
    }
    for &(source, target) in &trace.initial_edges {
        assert!(graph.link(source, target)?);
        assert!(production.link(source, target)?);
        assert!(reference.link(source, target)?);
    }
    let (mut reused_epoch, mut reused_bits) = (SearchSpace::default(), BitSearchSpace::default());
    let (mut uncounted_epoch, mut uncounted_bits) =
        (SearchSpace::default(), BitSearchSpace::default());
    let mut counts = OperationCounts::default();
    let mut queries = Vec::new();
    for (operation_index, operation) in trace.operations.iter().enumerate() {
        match *operation {
            Operation::Link { source, target } => {
                assert!(graph.link(source, target)?);
                assert!(production.link(source, target)?);
                assert!(reference.link(source, target)?);
                counts.link += 1;
            }
            Operation::Cut { source, target } => {
                assert!(graph.cut(source, target)?);
                assert!(production.cut(source, target)?);
                assert!(reference.cut(source, target)?);
                counts.cut += 1;
            }
            Operation::Connected {
                source,
                target,
                expected,
            } => {
                let (mut fresh_epoch, mut fresh_bits) =
                    (SearchSpace::default(), BitSearchSpace::default());
                assert_eq!(
                    graph.search::<false, true>(source, target, &mut fresh_epoch)?,
                    expected
                );
                assert_eq!(
                    graph.search::<false, true>(source, target, &mut reused_epoch)?,
                    expected
                );
                assert_eq!(
                    graph.search_bits::<true>(source, target, &mut fresh_bits)?,
                    expected
                );
                assert_eq!(
                    graph.search_bits::<true>(source, target, &mut reused_bits)?,
                    expected
                );
                assert_eq!(
                    graph.search::<false, false>(source, target, &mut uncounted_epoch)?,
                    expected
                );
                assert_eq!(
                    graph.search_bits::<false>(source, target, &mut uncounted_bits)?,
                    expected
                );
                assert_eq!(production.connected(source, target)?, expected);
                assert_eq!(reference.connected(source, target)?, expected);
                let stats = fresh_epoch.stats();
                assert_eq!(stats, reused_epoch.stats());
                assert_eq!(stats, fresh_bits.stats());
                assert_eq!(stats, reused_bits.stats());
                counts.connected += 1;
                counts.query_true += usize::from(expected);
                counts.query_false += usize::from(!expected);
                queries.push(QueryLedger {
                    operation_index,
                    source,
                    target,
                    expected,
                    graph: stats,
                    scratch: [
                        fresh_epoch.scratch_stats(),
                        reused_epoch.scratch_stats(),
                        fresh_bits.scratch_stats(),
                        reused_bits.scratch_stats(),
                    ],
                });
            }
        }
        assert_eq!(graph.node_count(), production.node_count());
        assert_eq!(graph.node_count(), reference.node_count());
        assert_eq!(graph.edge_count(), production.edge_count());
        assert_eq!(graph.edge_count(), reference.edge_count());
    }
    let report = LedgerReport {
        schema_version: LEDGER_SCHEMA_VERSION,
        scope: "Structural work only; counters do not identify elapsed-time dominance",
        representation: "Controlled sorted compact adjacency with BTreeMap IDs; not production FixedBitSet instrumentation",
        retention: "Fresh scratch is dropped after each query; reused scratch retains capacity across this trace; capacities exclude Vec/allocator metadata and are not RSS",
        config,
        workload: kind.name(),
        query_percent: kind.is_sustained().then_some(percent),
        trace_fingerprint_fnv1a64: format!("{fingerprint:016x}"),
        epoch_element_bytes: size_of::<u32>(),
        packed_element_bytes: size_of::<u64>(),
        queue_element_bytes: size_of::<usize>(),
        variants: [
            ScratchVariant::FreshEpoch,
            ScratchVariant::ReusedEpoch,
            ScratchVariant::FreshPacked,
            ScratchVariant::ReusedPacked,
        ],
        counts,
        queries,
    };
    serde_json::to_writer(std::io::stdout().lock(), &report)?;
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().collect();
    if !(4..=6).contains(&args.len())
        || (args.len() == 6 && args[5] != LEDGER_FLAG && args[5] != FIFO_FLAG)
    {
        return Err(USAGE.into());
    }
    let config = Config {
        nodes: args[1].parse()?,
        rounds: args
            .get(4)
            .map_or(Ok(DEFAULT_ROUNDS), |value| value.parse())?,
        seed: DIAGNOSTIC_SEED,
    };
    let kind = WorkloadKind::parse(&args[2])?;
    let percent = args[3].parse()?;
    let trace = generate_with_query_percent(kind, config, percent)?;
    #[derive(serde::Serialize)]
    struct Export<'a> {
        schema_version: u32,
        workload: &'static str,
        config: Config,
        #[serde(skip_serializing_if = "Option::is_none")]
        query_percent: Option<u8>,
        trace: &'a knotrel_benchmarks::Workload,
    }
    let bytes = serde_json::to_vec(&Export {
        schema_version: 1,
        workload: kind.name(),
        config,
        query_percent: kind.is_sustained().then_some(percent),
        trace: &trace,
    })?;
    let fingerprint = bytes.iter().fold(0xcbf29ce484222325_u64, |h, b| {
        (h ^ u64::from(*b)).wrapping_mul(0x100000001b3)
    });
    if args.len() == 6 && args[5] == FIFO_FLAG {
        return fifo_ledger(config, kind, percent, &trace, fingerprint);
    }
    if args.len() == 6 {
        return scratch_ledger(config, kind, percent, &trace, fingerprint);
    }
    let mut graph = Graph::new();
    for node in 0..config.nodes {
        graph.add_node(node);
    }
    for &(a, b) in &trace.initial_edges {
        assert!(graph.link(a, b)?);
    }
    let (mut bfs, mut dfs) = (SearchSpace::default(), SearchSpace::default());
    let mut bits = BitSearchSpace::default();
    let mut queries = Vec::new();
    for (index, operation) in trace.operations.iter().enumerate() {
        match *operation {
            Operation::Link { source, target } => assert!(graph.link(source, target)?),
            Operation::Cut { source, target } => assert!(graph.cut(source, target)?),
            Operation::Connected {
                source,
                target,
                expected,
            } => {
                assert_eq!(
                    graph.search::<false, true>(source, target, &mut bfs)?,
                    expected
                );
                assert_eq!(
                    graph.search::<true, true>(source, target, &mut dfs)?,
                    expected
                );
                assert_eq!(
                    graph.search_bits::<true>(source, target, &mut bits)?,
                    expected
                );
                assert_eq!(bfs.stats(), bits.stats());
                queries.push(json!({"operation_index":index,"source":source,"target":target,"expected":expected,"bfs":bfs.stats(),"dfs":dfs.stats(),"bitset":bits.stats()}));
            }
        }
    }
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"scope":"structural counters only, no timings", "config":config,"workload":kind.name(),"query_percent":percent,"trace_fingerprint_fnv1a64":format!("{fingerprint:016x}"),"queries":queries})
        )?
    );
    Ok(())
}
