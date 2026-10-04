//! Caller-owned reusable BFS storage; no graph answers or IDs are retained.
use crate::{Graph, GraphError, NodeId};

/// Reusable temporary storage for [`Graph::connected_with_workspace`].
///
/// Each caller or worker owns its workspace. Separate workspaces permit shared
/// graph queries without internal locks. A workspace can be reused across graph
/// growth, mutations and different graphs. It never caches connectivity answers.
/// Storage retains O(N + R) capacity for the largest registered node count N and
/// largest visited set R so far; drop the workspace to release that memory.
#[derive(Debug, Default)]
pub struct BfsWorkspace {
    visited: Vec<bool>,
    queue: Vec<usize>,
}

impl Graph {
    /// Tests connectivity using reusable caller-owned traversal storage.
    ///
    /// Unlike [`Graph::connected`], repeated calls reuse allocations. Only visited
    /// entries are reset, including on early target discovery. The visited array
    /// grows when necessary and never shrinks; all marks are clear at return.
    /// Traversal and reset take O(V_reached + E_examined), plus O(log V) endpoint
    /// lookup and amortized storage growth (initial growth is O(V)). The worst
    /// case remains O(V + E). No answers are cached; queries observe current edges.
    ///
    /// ```
    /// use knotrel_core::{BfsWorkspace, Graph};
    /// let mut graph = Graph::new();
    /// graph.link(10, 20)?;
    /// let mut workspace = BfsWorkspace::default();
    /// assert!(graph.connected_with_workspace(10, 20, &mut workspace)?);
    /// graph.cut(10, 20)?;
    /// assert!(!graph.connected_with_workspace(10, 20, &mut workspace)?);
    /// # Ok::<(), knotrel_core::GraphError>(())
    /// ```
    ///
    /// # Errors
    /// Returns [`GraphError::UnknownNode`] for absent endpoints, source first.
    pub fn connected_with_workspace(
        &self,
        source: NodeId,
        target: NodeId,
        workspace: &mut BfsWorkspace,
    ) -> Result<bool, GraphError> {
        let a = *self
            .ids
            .get(&source)
            .ok_or(GraphError::UnknownNode { node: source })?;
        let b = *self
            .ids
            .get(&target)
            .ok_or(GraphError::UnknownNode { node: target })?;
        if a == b {
            return Ok(true);
        }
        if workspace.visited.len() < self.adjacency.len() {
            workspace.visited.resize(self.adjacency.len(), false);
        }
        workspace.visited[a] = true;
        workspace.queue.push(a);
        let mut cursor = 0;
        let mut found = false;
        // Mark on enqueue. Queue records every marked index exactly once, so
        // resetting it also handles the unprocessed frontier after early exit.
        'search: while cursor < workspace.queue.len() {
            for &neighbor in &self.adjacency[workspace.queue[cursor]] {
                if neighbor == b {
                    found = true;
                    break 'search;
                }
                if !workspace.visited[neighbor] {
                    workspace.visited[neighbor] = true;
                    workspace.queue.push(neighbor);
                }
            }
            cursor += 1;
        }
        for &vertex in &workspace.queue {
            workspace.visited[vertex] = false;
        }
        workspace.queue.clear();
        Ok(found)
    }
}
