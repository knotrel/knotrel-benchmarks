# ETT manual-counter export probe on Apple M4 — 2026-10-12

This fixed two-process probe validates export shape before a second large
marker-scoped campaign. It uses the user-saved manual CPU Counters template at
`$HOME/Downloads/MyTemplate.tracetemplate`, SHA-256
`99b0cb00c8c35bdd66fb6456021ea11c21c0c3e36c89b0b4e5975ea5622ecd74`.

The template configures the M4 events `FIXED_CYCLES`, `CORE_ACTIVE_CYCLES`,
`BRANCH_MISPRED_NON_SPEC`, `IFU_CACHE_MISS_DEMAND`, `INST_ALL`, `L1D_CACHE_RD`,
`L1D_CACHE_LMISS_RD`, and `IFU_STALL_BACKEND`. It uses the already verified
safe-marker before/after binaries. The two records are warmed one-million-node
path replays, before then after, and validate export names and scope only.
