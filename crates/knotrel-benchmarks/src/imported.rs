//! Strict offline import validation, independent of every measured backend.
use knotrel_benchmarks::{Operation, Workload};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, VecDeque};
use std::error::Error;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ImportedTrace {
    schema_version: u32,
    kind: String,
    pub(crate) workload: String,
    node_ids: Vec<String>,
    provenance: Provenance,
    transform: serde_json::Map<String, serde_json::Value>,
    batches: Vec<Batch>,
    pub(crate) trace: Workload,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Provenance {
    source_url: String,
    source_revision: String,
    source_sha256: String,
    license: String,
    citation: String,
    retrieved_date: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Batch {
    time: u64,
    start: usize,
    end: usize,
}
impl ImportedTrace {
    pub(crate) fn nodes(&self) -> u64 {
        self.node_ids.len() as u64
    }

    /// Validate the normalized trace, not the truth of external provenance claims.
    /// BFS validation is O(q*(n+m)); it is performed once outside all timers.
    pub(crate) fn validate(&self) -> Result<serde_json::Value, Box<dyn Error>> {
        if self.schema_version != 1 || self.kind != "connectivity-import" {
            return Err("unsupported imported trace schema or kind".into());
        }
        if self.workload.trim().is_empty() || self.transform.is_empty() {
            return Err("workload and transform metadata are required".into());
        }
        if self.node_ids.len() < 2
            || self.node_ids.iter().any(|id| id.is_empty())
            || self.node_ids.windows(2).any(|ids| ids[0] >= ids[1])
        {
            return Err("node_ids must contain at least two sorted unique nonempty IDs".into());
        }
        let p = &self.provenance;
        if [
            &p.source_url,
            &p.source_revision,
            &p.license,
            &p.citation,
            &p.retrieved_date,
        ]
        .iter()
        .any(|s| s.trim().is_empty())
            || p.source_sha256.len() != 64
            || !p.source_sha256.bytes().all(|b| b.is_ascii_hexdigit())
        {
            return Err("source provenance and a 64-digit SHA-256 are required".into());
        }
        let mut end = 0;
        let mut time = None;
        for batch in &self.batches {
            if batch.start != end
                || batch.end <= batch.start
                || batch.end > self.trace.operations.len()
                || time.is_some_and(|previous| previous >= batch.time)
            {
                return Err(
                    "batches must partition operations with increasing logical times".into(),
                );
            }
            let mut querying = false;
            let mut linking = false;
            let mut cut_pairs = BTreeSet::new();
            let mut last_cut = None;
            let mut last_link = None;
            for op in &self.trace.operations[batch.start..batch.end] {
                match *op {
                    Operation::Connected { .. } => querying = true,
                    Operation::Cut { source, target } => {
                        let pair = (source, target);
                        if querying || linking || last_cut.is_some_and(|last| last >= pair) {
                            return Err("batch cuts must be sorted before links and queries".into());
                        }
                        cut_pairs.insert(pair);
                        last_cut = Some(pair);
                    }
                    Operation::Link { source, target } => {
                        let pair = (source, target);
                        if querying
                            || cut_pairs.contains(&pair)
                            || last_link.is_some_and(|last| last >= pair)
                        {
                            return Err("batch links must be sorted before queries".into());
                        }
                        linking = true;
                        last_link = Some(pair);
                    }
                }
            }
            if !querying {
                return Err("each imported batch requires queries".into());
            }
            end = batch.end;
            time = Some(batch.time);
        }
        if end != self.trace.operations.len() || self.batches.is_empty() {
            return Err("nonempty batches must cover the complete trace".into());
        }
        let mut adjacency = vec![BTreeSet::new(); self.node_ids.len()];
        let check_pair =
            |a: u64, b: u64, mutation: bool| -> Result<(usize, usize), Box<dyn Error>> {
                if a >= self.nodes() || b >= self.nodes() || (mutation && a >= b) {
                    return Err(
                        "endpoints must exist; mutation pairs must be canonical and distinct"
                            .into(),
                    );
                }
                Ok((a as usize, b as usize))
            };
        for &(a, b) in &self.trace.initial_edges {
            let (a, b) = check_pair(a, b, true)?;
            if !adjacency[a].insert(b) {
                return Err("duplicate initial edge".into());
            }
            adjacency[b].insert(a);
        }
        let mut validated_queries = 0;
        for op in &self.trace.operations {
            match *op {
                Operation::Link { source, target } => {
                    let (a, b) = check_pair(source, target, true)?;
                    if !adjacency[a].insert(b) {
                        return Err("imported link does not change graph".into());
                    }
                    adjacency[b].insert(a);
                }
                Operation::Cut { source, target } => {
                    let (a, b) = check_pair(source, target, true)?;
                    if !adjacency[a].remove(&b) {
                        return Err("imported cut does not change graph".into());
                    }
                    adjacency[b].remove(&a);
                }
                Operation::Connected {
                    source,
                    target,
                    expected,
                } => {
                    let (a, b) = check_pair(source, target, false)?;
                    let mut seen = vec![false; adjacency.len()];
                    let mut queue = VecDeque::from([a]);
                    seen[a] = true;
                    while let Some(vertex) = queue.pop_front() {
                        if vertex == b {
                            break;
                        }
                        for &neighbor in &adjacency[vertex] {
                            if !seen[neighbor] {
                                seen[neighbor] = true;
                                queue.push_back(neighbor);
                            }
                        }
                    }
                    if seen[b] != expected {
                        return Err("imported query disagrees with independent BFS oracle".into());
                    }
                    validated_queries += 1;
                }
            }
        }
        Ok(serde_json::json!({
            "schema_version": self.schema_version, "node_count": self.nodes(),
            "source_batches": self.batches.len(), "provenance": p,
            "transform": self.transform, "validated_queries": validated_queries,
            "validation": "independent-bfs-before-warmup", "input_file_cache": "uncontrolled"
        }))
    }
}
