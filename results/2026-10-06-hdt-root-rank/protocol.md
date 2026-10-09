# Single-pass reroot root/rank lookup

Replace the two parent walks used by reroot with one read-only walk returning
both root and in-order rank. Keep standalone root/rank callers, split/concat,
promotion order and rank-zero behavior unchanged. Do not combine the previous
rank-zero shortcut. Build both variants in the same isolated workspace with
identical Rust/Cargo inputs except the candidate forest; copy toolchain pins.

Validate the fused lookup against explicit in-order enumeration across live
vertex and edge tokens, singleton/disconnected tours and repeated cut/relink.
Run the complete existing core tests and doctests before timing.

Replay the frozen current-ranking sparse 100k/1M path/blocks, 10/50/90% queries,
fresh/warmed (24 cells), dense 512 one/two bridges at all three mixes and both
regimes (12 cells), and Cogentco (2 cells). Four sequential pairs per cell,
two before-first and two after-first; shuffled seed42. 304 processes total.
No CPU-heavy concurrent jobs. Timeout120s, preserve every failure.

Compare per-cell median wall runtime, paired directions, setup, operation tails
and whole-process RSS separately. Require identical fingerprints, answer counts,
mutation counts and HDT counters. Do not infer runtime improvements from counting
parent steps. Existing baselines and the earlier candidate patch remain intact.
Broad mixed results keep a candidate experimental; any integration requires
correctness validation and explicit documentation of observed tradeoffs.
