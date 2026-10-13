//! Phase-scoped initialization baseline; never times dynamic operations.

use knotrel_benchmarks::{
    Config, Operation, Workload, WorkloadKind,
    engines::{ConstructionTimings, Engine, EngineKind},
    generate_with_query_percent,
};
use knotrel_core::{ConnectivityGraph, EngineConfig, GraphError, GraphLimits};
use serde::Serialize;
use std::{collections::HashMap, error::Error, hint::black_box, process::ExitCode, time::Instant};

#[derive(Clone, Copy)]
enum Surface {
    Adapter,
    Facade,
    FacadeLimited,
}

/// How the facade is populated; `Incremental` is the historical default.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Initialization {
    /// Ordered `add_node` calls followed by ordered `link` calls in the harness.
    Incremental,
    /// One `ConnectivityGraph::try_from_edges` call over the same ordered input.
    ///
    /// Requires distinct initial edges without self-loops (see `construct_bulk`).
    Bulk,
}

struct Options {
    config: Config,
    workload: WorkloadKind,
    engine: EngineKind,
    surface: Surface,
    initialization: Initialization,
    phases: bool,
    warmup: usize,
    repetitions: usize,
    validate: bool,
}

#[derive(Serialize)]
struct Report {
    schema_version: u32,
    measurement: &'static str,
    compiler: &'static str,
    debug_assertions: bool,
    engine: &'static str,
    surface: &'static str,
    timing: &'static str,
    // Present only for non-default modes so incremental reports keep their schema.
    #[serde(skip_serializing_if = "Option::is_none")]
    initialization: Option<&'static str>,
    workload: &'static str,
    config: Config,
    warmup: usize,
    validated_dynamic_continuation: bool,
    repetitions: Vec<Run>,
}

#[derive(Serialize)]
struct Run {
    trace_fingerprint_fnv1a64: String,
    initial_edges: usize,
    total_initialization_ns: u128,
    setup_ns: u128,
    #[serde(skip_serializing_if = "Option::is_none")]
    phases: Option<Phases>,
}

#[derive(Default, Serialize)]
struct Phases {
    input_generation_ns: u128,
    trace_encoding_fingerprint_ns: u128,
    node_vector_ns: u128,
    adapter_validation_ns: Option<u128>,
    vertex_registration_ns: u128,
    constructor_other_ns: u128,
    initial_edges_ns: u128,
    setup_other_ns: u128,
}

impl Phases {
    fn setup_sum(&self) -> u128 {
        self.node_vector_ns
            + self.adapter_validation_ns.unwrap_or(0)
            + self.vertex_registration_ns
            + self.constructor_other_ns
            + self.initial_edges_ns
            + self.setup_other_ns
    }
}

enum Graph {
    Adapter(Engine),
    Facade(ConnectivityGraph),
}

impl Graph {
    fn link(&mut self, a: u64, b: u64) -> Result<bool, Box<dyn Error>> {
        Ok(match self {
            Self::Adapter(graph) => graph.link(a, b)?,
            Self::Facade(graph) => graph.link(a, b)?,
        })
    }

    fn validate(&mut self, workload: &Workload) -> Result<(), Box<dyn Error>> {
        for &op in &workload.operations {
            let valid = match op {
                Operation::Link { source, target } => self.link(source, target)?,
                Operation::Cut { source, target } => match self {
                    Self::Adapter(graph) => graph.cut(source, target)?,
                    Self::Facade(graph) => graph.cut(source, target)?,
                },
                Operation::Connected {
                    source,
                    target,
                    expected,
                } => {
                    let actual = match self {
                        Self::Adapter(graph) => graph.connected(source, target)?,
                        Self::Facade(graph) => graph.connected(source, target)?,
                    };
                    actual == expected
                }
            };
            if !valid {
                return Err("dynamic continuation failed the workload oracle".into());
            }
        }
        Ok(())
    }
}

/// Engine and limits shared by both facade initialization modes.
fn facade_settings(
    options: &Options,
    nodes: usize,
    edges: usize,
) -> Result<(EngineConfig, GraphLimits), Box<dyn Error>> {
    let engine = match options.engine {
        EngineKind::Compact => EngineConfig::CompactBfs,
        EngineKind::EttScan => EngineConfig::EulerTour,
        EngineKind::Hdt => EngineConfig::Hdt,
        _ => return Err("initialization requires compact-bfs, ett-scan or hdt".into()),
    };
    let limits = if matches!(options.surface, Surface::FacadeLimited) {
        GraphLimits {
            max_nodes: Some(nodes),
            // Leave room for the disconnected workload's later bridge insertion.
            max_edges: Some(edges.checked_add(1).ok_or("edge limit overflow")?),
        }
    } else {
        GraphLimits::default()
    };
    Ok((engine, limits))
}

/// Equivalence precondition of bulk and incremental loading: initial edges are
/// pairwise distinct as undirected pairs and contain no self-loop.
///
/// Returns the first violation in input order, independent of any core error.
/// Every generated workload family satisfies it. It is evaluated only after a
/// failed bulk construction, never on the timed success path: a successful run
/// already proves it (self-loops are core errors and the edge-count comparison
/// detects duplicates).
fn first_precondition_violation(edges: &[(u64, u64)]) -> Option<String> {
    let mut seen = HashMap::with_capacity(edges.len());
    for (index, &(a, b)) in edges.iter().enumerate() {
        if a == b {
            return Some(format!("initial edge {index} ({a}, {b}) is a self-loop"));
        }
        if let Some(first) = seen.insert((a.min(b), a.max(b)), index) {
            return Some(format!(
                "initial edge {index} ({a}, {b}) duplicates edge {first}"
            ));
        }
    }
    None
}

/// Loads nodes and edges through the core's ordered bulk constructor.
///
/// The constructor returns no per-edge change flags and, unlike the incremental
/// loop, steps over duplicate edges. Observable equivalence with incremental
/// loading is therefore guaranteed for inputs satisfying
/// [`first_precondition_violation`]: both modes then succeed with the same graph
/// or fail with the same core error. Any other failing input is rejected with an
/// explicit precondition error instead of whichever core error the ordered loop
/// meets first, which could differ from the incremental path's report. The
/// precondition scan runs only on this failure path; the timed path performs the
/// constructor call and one edge-count comparison.
fn construct_bulk(
    options: &Options,
    nodes: &[u64],
    edges: &[(u64, u64)],
) -> Result<Graph, Box<dyn Error>> {
    let (engine, limits) = facade_settings(options, nodes.len(), edges.len())?;
    let core_error = match ConnectivityGraph::try_from_edges(engine, limits, nodes, edges) {
        Ok(graph) if graph.edge_count() == edges.len() => return Ok(Graph::Facade(graph)),
        Ok(_) => None,
        Err(error) => Some(error),
    };
    Err(bulk_failure(edges, core_error))
}

/// Explains a failed bulk load (`core_error` is `None` if edges were lost).
fn bulk_failure(edges: &[(u64, u64)], core_error: Option<GraphError>) -> Box<dyn Error> {
    if let Some(violation) = first_precondition_violation(edges) {
        return format!(
            "bulk initialization requires distinct initial edges without self-loops: {violation}"
        )
        .into();
    }
    match core_error {
        Some(error) => error.into(),
        None => "bulk initialization produced fewer edges than the input".into(),
    }
}

fn construct(
    options: &Options,
    nodes: &[u64],
    edges: usize,
    phases: &mut Phases,
) -> Result<Graph, Box<dyn Error>> {
    if matches!(options.surface, Surface::Adapter) {
        return if options.phases {
            let (
                graph,
                ConstructionTimings {
                    validation_ns,
                    vertex_registration_ns,
                    other_ns,
                    ..
                },
            ) = Engine::new_with_timings(options.engine, nodes)?;
            phases.adapter_validation_ns = Some(validation_ns);
            phases.vertex_registration_ns = vertex_registration_ns;
            phases.constructor_other_ns = other_ns;
            Ok(Graph::Adapter(graph))
        } else {
            Ok(Graph::Adapter(Engine::new(options.engine, nodes)?))
        };
    }
    let (engine, limits) = facade_settings(options, nodes.len(), edges)?;
    let start = options.phases.then(Instant::now);
    let mut graph = ConnectivityGraph::with_limits(engine, limits);
    for &node in nodes {
        graph.add_node(node)?;
    }
    if let Some(start) = start {
        phases.vertex_registration_ns = start.elapsed().as_nanos();
    }
    Ok(Graph::Facade(graph))
}

fn measure(options: &Options) -> Result<Run, Box<dyn Error>> {
    let total_start = Instant::now();
    let workload = generate_with_query_percent(options.workload, options.config, 50)?;
    let generated = options.phases.then(Instant::now);
    // Field order matches the existing runner's generated trace schema exactly.
    #[derive(Serialize)]
    struct Trace<'a> {
        schema_version: u32,
        workload: &'static str,
        config: Config,
        #[serde(skip_serializing_if = "Option::is_none")]
        query_percent: Option<u8>,
        trace: &'a Workload,
    }
    let bytes = serde_json::to_vec(&Trace {
        schema_version: 1,
        workload: options.workload.name(),
        config: options.config,
        query_percent: options.workload.is_sustained().then_some(50),
        trace: &workload,
    })?;
    let fingerprint = bytes.iter().fold(0xcbf29ce484222325_u64, |h, b| {
        (h ^ u64::from(*b)).wrapping_mul(0x100000001b3)
    });
    drop(bytes);
    let setup_start = Instant::now();
    let mut phases = Phases::default();
    if let Some(generated) = generated {
        phases.input_generation_ns = (generated - total_start).as_nanos();
        phases.trace_encoding_fingerprint_ns = (setup_start - generated).as_nanos();
    }
    let nodes: Vec<_> = (0..options.config.nodes).collect();
    let prepared = options.phases.then(Instant::now);
    if let Some(prepared) = prepared {
        phases.node_vector_ns = (prepared - setup_start).as_nanos();
    }
    let (mut graph, registered) = if options.initialization == Initialization::Bulk {
        // Bulk mode is rejected with phase timing: registration and edge
        // insertion are one core call and cannot be separated.
        (
            construct_bulk(options, &nodes, &workload.initial_edges)?,
            None,
        )
    } else {
        let mut graph = construct(options, &nodes, workload.initial_edges.len(), &mut phases)?;
        let registered = options.phases.then(Instant::now);
        for &(a, b) in &workload.initial_edges {
            if !graph.link(a, b)? {
                return Err("initial edge failed the workload oracle".into());
            }
        }
        (graph, registered)
    };
    black_box(&graph);
    let end = Instant::now();
    let setup_ns = (end - setup_start).as_nanos();
    let total_initialization_ns = (end - total_start).as_nanos();
    if let Some(registered) = registered {
        phases.initial_edges_ns = (end - registered).as_nanos();
        // Only untimed gaps in the enclosing interval: dispatch, clock/bookkeeping.
        phases.setup_other_ns = setup_ns
            .checked_sub(phases.setup_sum())
            .ok_or("initialization phases exceed setup wall time")?;
        if phases.setup_sum() != setup_ns
            || phases.input_generation_ns + phases.trace_encoding_fingerprint_ns + setup_ns
                != total_initialization_ns
        {
            return Err("inconsistent initialization timing accounting".into());
        }
    }
    if options.validate {
        graph.validate(&workload)?;
    }
    // Graph, node list, and workload remain live through the end timestamp.
    black_box(&graph);
    Ok(Run {
        trace_fingerprint_fnv1a64: format!("{fingerprint:016x}"),
        initial_edges: workload.initial_edges.len(),
        total_initialization_ns,
        setup_ns,
        phases: options.phases.then_some(phases),
    })
}

fn parse() -> Result<Option<Options>, Box<dyn Error>> {
    let mut options = Options {
        config: Config {
            nodes: 10_000,
            rounds: 1,
            seed: 42,
        },
        workload: WorkloadKind::Chain,
        engine: EngineKind::Compact,
        surface: Surface::Adapter,
        initialization: Initialization::Incremental,
        phases: true,
        warmup: 0,
        repetitions: 1,
        validate: false,
    };
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--help" | "-h" => {
                println!(
                    "Usage: initialization-profile [--engine compact-bfs|ett-scan|hdt] [--workload NAME] [--nodes N] [--rounds N] [--seed N] [--surface adapter|facade|facade-limited] [--init-mode incremental|bulk] [--timing whole|phases] [--warmup N] [--repetitions N] [--validate]\nDefaults: compact-bfs, chain-split-rejoin-v1, nodes=10000, rounds=1, seed=42, adapter, incremental, phases, warmup=0, repetitions=1. Generated inputs only; sustained query percent is 50. Warmup rebuilds input and graph; --validate runs an untimed dynamic oracle afterward and contaminates build-only peak RSS.\n--init-mode bulk uses ConnectivityGraph::try_from_edges and requires --surface facade or facade-limited and --timing whole: it never emulates bulk loading for the adapter surface and cannot separate registration from edge insertion. Initial edges must be distinct without self-loops; other inputs are rejected explicitly (generated workloads always qualify). No performance claim is made for either mode."
                );
                return Ok(None);
            }
            "--validate" => options.validate = true,
            _ => {
                let value = args.next().ok_or("flag requires a value")?;
                match flag.as_str() {
                    "--nodes" => options.config.nodes = value.parse()?,
                    "--rounds" => options.config.rounds = value.parse()?,
                    "--seed" => options.config.seed = value.parse()?,
                    "--workload" => options.workload = WorkloadKind::parse(&value)?,
                    "--engine" => options.engine = EngineKind::parse(&value)?,
                    "--warmup" => options.warmup = value.parse()?,
                    "--repetitions" => options.repetitions = value.parse()?,
                    "--surface" => {
                        options.surface = match value.as_str() {
                            "adapter" => Surface::Adapter,
                            "facade" => Surface::Facade,
                            "facade-limited" => Surface::FacadeLimited,
                            _ => return Err("unknown construction surface".into()),
                        }
                    }
                    "--timing" => {
                        options.phases = match value.as_str() {
                            "whole" => false,
                            "phases" => true,
                            _ => return Err("timing must be whole or phases".into()),
                        }
                    }
                    "--init-mode" => {
                        options.initialization = match value.as_str() {
                            "incremental" => Initialization::Incremental,
                            "bulk" => Initialization::Bulk,
                            _ => return Err("init-mode must be incremental or bulk".into()),
                        }
                    }
                    _ => return Err(format!("unknown argument: {flag}").into()),
                }
            }
        }
    }
    if !matches!(
        options.engine,
        EngineKind::Compact | EngineKind::EttScan | EngineKind::Hdt
    ) {
        return Err("initialization requires compact-bfs, ett-scan or hdt".into());
    }
    if options.repetitions == 0 {
        return Err("repetitions must be positive".into());
    }
    if options.initialization == Initialization::Bulk {
        if matches!(options.surface, Surface::Adapter) {
            return Err("bulk initialization requires --surface facade or facade-limited".into());
        }
        if options.phases {
            return Err(
                "bulk initialization cannot separate registration from edge insertion; use --timing whole"
                    .into(),
            );
        }
    }
    Ok(Some(options))
}

fn run() -> Result<(), Box<dyn Error>> {
    let Some(options) = parse()? else {
        return Ok(());
    };
    for _ in 0..options.warmup {
        black_box(measure(&options)?);
    }
    let mut repetitions = Vec::new();
    repetitions.try_reserve_exact(options.repetitions)?;
    for _ in 0..options.repetitions {
        repetitions.push(measure(&options)?);
    }
    let report = Report {
        schema_version: 1,
        measurement: "initialization-only",
        compiler: env!("KNOTREL_BUILD_COMPILER"),
        debug_assertions: cfg!(debug_assertions),
        engine: options.engine.name(),
        surface: match options.surface {
            Surface::Adapter => "adapter",
            Surface::Facade => "facade",
            Surface::FacadeLimited => "facade-limited",
        },
        timing: if options.phases { "phases" } else { "whole" },
        initialization: (options.initialization == Initialization::Bulk).then_some("bulk"),
        workload: options.workload.name(),
        config: options.config,
        warmup: options.warmup,
        validated_dynamic_continuation: options.validate,
        repetitions,
    };
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("initialization-profile: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ALL_KINDS: [WorkloadKind; 8] = [
        WorkloadKind::Chain,
        WorkloadKind::Cycle,
        WorkloadKind::Components,
        WorkloadKind::Hub,
        WorkloadKind::SustainedPath,
        WorkloadKind::SustainedBlocks,
        WorkloadKind::DenseBridge,
        WorkloadKind::RedundantBridge,
    ];
    const ORACLE: &str = "initial edge failed the workload oracle";
    const PREFIX: &str = "bulk initialization requires distinct initial edges without self-loops: ";

    fn options(engine: EngineKind, surface: Surface) -> Options {
        Options {
            config: Config {
                nodes: 4,
                rounds: 1,
                seed: 1,
            },
            workload: WorkloadKind::Chain,
            engine,
            surface,
            initialization: Initialization::Bulk,
            phases: false,
            warmup: 0,
            repetitions: 1,
            validate: false,
        }
    }

    fn incremental(
        options: &Options,
        nodes: &[u64],
        edges: &[(u64, u64)],
    ) -> Result<Graph, Box<dyn Error>> {
        let mut graph = construct(options, nodes, edges.len(), &mut Phases::default())?;
        for &(a, b) in edges {
            if !graph.link(a, b)? {
                return Err("initial edge failed the workload oracle".into());
            }
        }
        Ok(graph)
    }

    fn message<T>(result: Result<T, Box<dyn Error>>) -> Option<String> {
        result.err().map(|error| error.to_string())
    }

    const ENGINES: [EngineKind; 3] = [EngineKind::Compact, EngineKind::EttScan, EngineKind::Hdt];
    const SURFACES: [Surface; 2] = [Surface::Facade, Surface::FacadeLimited];

    #[test]
    fn conforming_inputs_match_incremental_exactly() {
        let nodes = [0, 1, 2];
        for engine in ENGINES {
            for surface in SURFACES {
                let options = options(engine, surface);
                for edges in [
                    &[][..],
                    &[(0, 1), (1, 2)][..],
                    &[(0, 1), (1, 2), (2, 0)][..],
                    // Implicit endpoints: a node-limit error only on the limited surface,
                    // identical in both modes because no duplicate can precede it.
                    &[(0, 9)][..],
                    &[(0, 1), (0, 9), (1, 2)][..],
                    &[(0, 1), (9, 8)][..],
                ] {
                    assert_eq!(first_precondition_violation(edges), None);
                    let bulk = construct_bulk(&options, &nodes, edges);
                    let sequential = incremental(&options, &nodes, edges);
                    if let (Ok(Graph::Facade(a)), Ok(Graph::Facade(b))) = (&bulk, &sequential) {
                        assert_eq!(
                            (a.node_count(), a.edge_count()),
                            (b.node_count(), b.edge_count())
                        );
                    }
                    assert_eq!(message(bulk), message(sequential), "{edges:?}");
                }
            }
        }
    }

    #[test]
    fn violating_inputs_are_rejected_explicitly_in_either_order() {
        // (edges, bulk violation, incremental error on the unlimited / limited surface).
        // Incremental keeps reporting whichever failure it meets first; bulk reports
        // the input's first precondition violation, independent of the order of any
        // later self-loop or limit error. Both always fail: no graph is ever returned.
        type Case = (
            &'static [(u64, u64)],
            &'static str,
            &'static str,
            &'static str,
        );
        let cases: [Case; 8] = [
            // Plain and reversed duplicates.
            (
                &[(0, 1), (1, 2), (0, 1)],
                "initial edge 2 (0, 1) duplicates edge 0",
                ORACLE,
                ORACLE,
            ),
            (
                &[(0, 1), (1, 2), (2, 1)],
                "initial edge 2 (2, 1) duplicates edge 1",
                ORACLE,
                ORACLE,
            ),
            // Duplicate, then self-loop; and self-loop, then duplicate.
            (
                &[(0, 1), (1, 0), (2, 2)],
                "initial edge 1 (1, 0) duplicates edge 0",
                ORACLE,
                ORACLE,
            ),
            (
                &[(2, 2), (0, 1), (1, 0)],
                "initial edge 0 (2, 2) is a self-loop",
                "self-loops are not supported: 2",
                "self-loops are not supported: 2",
            ),
            // Duplicate, then node-limit error; and node-limit error, then duplicate.
            (
                &[(0, 1), (1, 0), (0, 9)],
                "initial edge 1 (1, 0) duplicates edge 0",
                ORACLE,
                ORACLE,
            ),
            (
                &[(0, 9), (0, 1), (1, 0)],
                "initial edge 2 (1, 0) duplicates edge 1",
                ORACLE,
                "node limit exceeded: 3",
            ),
            // Self-loop and duplicate separated by valid edges.
            (
                &[(0, 1), (1, 2), (2, 2), (0, 1)],
                "initial edge 2 (2, 2) is a self-loop",
                "self-loops are not supported: 2",
                "self-loops are not supported: 2",
            ),
            (
                &[(0, 1), (1, 2), (0, 1), (2, 2)],
                "initial edge 2 (0, 1) duplicates edge 0",
                ORACLE,
                ORACLE,
            ),
        ];
        for engine in ENGINES {
            for (surface, limited) in [(Surface::Facade, false), (Surface::FacadeLimited, true)] {
                let options = options(engine, surface);
                for &(edges, violation, unlimited, limited_error) in &cases {
                    assert_eq!(
                        message(construct_bulk(&options, &[0, 1, 2], edges)),
                        Some(format!("{PREFIX}{violation}")),
                        "{edges:?}"
                    );
                    assert_eq!(
                        message(incremental(&options, &[0, 1, 2], edges)).as_deref(),
                        Some(if limited { limited_error } else { unlimited }),
                        "{edges:?}"
                    );
                }
            }
        }
    }

    #[test]
    fn precondition_scan_is_order_based_and_canonical() {
        assert_eq!(first_precondition_violation(&[]), None);
        assert_eq!(first_precondition_violation(&[(5, 6), (7, 6)]), None);
        assert_eq!(
            first_precondition_violation(&[(u64::MAX, 0), (0, u64::MAX)]).as_deref(),
            Some("initial edge 1 (0, 18446744073709551615) duplicates edge 0")
        );
        // Whichever violation comes first in the input is reported.
        assert!(
            first_precondition_violation(&[(1, 2), (2, 1), (3, 3)])
                .unwrap()
                .contains("duplicates edge 0")
        );
        assert!(
            first_precondition_violation(&[(3, 3), (1, 2), (2, 1)])
                .unwrap()
                .contains("self-loop")
        );
    }

    #[test]
    fn every_generated_workload_satisfies_the_precondition_and_loads_in_bulk() {
        for kind in ALL_KINDS {
            for (nodes, rounds, seed) in [(24, 2, 1), (24, 3, 9), (64, 1, 42)] {
                let config = Config {
                    nodes,
                    rounds,
                    seed,
                };
                let workload = generate_with_query_percent(kind, config, 50).unwrap();
                assert_eq!(
                    first_precondition_violation(&workload.initial_edges),
                    None,
                    "{}",
                    kind.name()
                );
                let ids: Vec<_> = (0..nodes).collect();
                for engine in ENGINES {
                    for surface in SURFACES {
                        let options = options(engine, surface);
                        let Ok(Graph::Facade(graph)) =
                            construct_bulk(&options, &ids, &workload.initial_edges)
                        else {
                            panic!("{} failed bulk loading", kind.name());
                        };
                        assert_eq!(graph.edge_count(), workload.initial_edges.len());
                        assert_eq!(graph.node_count(), ids.len());
                    }
                }
            }
        }
    }
}
