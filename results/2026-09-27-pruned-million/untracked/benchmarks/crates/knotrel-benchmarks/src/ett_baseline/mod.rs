//! Frozen ETT scan v1 for controlled comparisons; never used by the server.
//! Copied from the first prototype before candidate-subtree pruning.
mod dynamic;
mod forest;
pub(crate) use dynamic::ForestGraph;
