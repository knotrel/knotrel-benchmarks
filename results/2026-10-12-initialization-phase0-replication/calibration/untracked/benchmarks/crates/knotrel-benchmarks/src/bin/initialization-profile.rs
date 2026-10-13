//! Phase-scoped initialization baseline; never times dynamic operations.

use knotrel_benchmarks::{
    Config, Operation, Workload, WorkloadKind,
    engines::{ConstructionTimings, Engine, EngineKind},
    generate_with_query_percent,
};
use knotrel_core::{ConnectivityGraph, EngineConfig, GraphLimits};
use serde::Serialize;
use std::{error::Error, hint::black_box, process::ExitCode, time::Instant};

#[derive(Clone, Copy)]
enum Surface {
    Adapter,
    Facade,
    FacadeLimited,
}

struct Options {
    config: Config,
    workload: WorkloadKind,
    engine: EngineKind,
    surface: Surface,
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
    let engine = match options.engine {
        EngineKind::Compact => EngineConfig::CompactBfs,
        EngineKind::EttScan => EngineConfig::EulerTour,
        EngineKind::Hdt => EngineConfig::Hdt,
        _ => return Err("initialization requires compact-bfs, ett-scan or hdt".into()),
    };
    let limits = if matches!(options.surface, Surface::FacadeLimited) {
        GraphLimits {
            max_nodes: Some(nodes.len()),
            // Leave room for the disconnected workload's later bridge insertion.
            max_edges: Some(edges.checked_add(1).ok_or("edge limit overflow")?),
        }
    } else {
        GraphLimits::default()
    };
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
    let mut graph = construct(options, &nodes, workload.initial_edges.len(), &mut phases)?;
    let registered = options.phases.then(Instant::now);
    for &(a, b) in &workload.initial_edges {
        if !graph.link(a, b)? {
            return Err("initial edge failed the workload oracle".into());
        }
    }
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
                    "Usage: initialization-profile [--engine compact-bfs|ett-scan|hdt] [--workload NAME] [--nodes N] [--rounds N] [--seed N] [--surface adapter|facade|facade-limited] [--timing whole|phases] [--warmup N] [--repetitions N] [--validate]\nDefaults: compact-bfs, chain-split-rejoin-v1, nodes=10000, rounds=1, seed=42, adapter, phases, warmup=0, repetitions=1. Generated inputs only; sustained query percent is 50. Warmup rebuilds input and graph; --validate runs an untimed dynamic oracle afterward and contaminates build-only peak RSS."
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
