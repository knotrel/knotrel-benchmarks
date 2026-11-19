# Equivalence smoke runs (checks only, not measurements)

Before the freeze, each of the 13 capability-equivalent B/C cells was run at
its real size and arguments (window multipliers applied), with 2 pairs and no
warmup. The purpose was the equivalence checks of `http-lifecycle`:
- per-operation outcomes;
- final counts;
- the registered content of the candidate;
- the content of the plain server.

Every cell passed (`smoke-*.txt`; the last line of each run). The timings in
those lines come from a laptop that was not gated, with two pairs, during
other work. They are not measurements and are not used for any decision.

**Negative controls.** These ran on a scratch copy of the probe with
injected mutations, at 2k nodes. Each mutation was detected:
- A, a wrong per-operation outcome: caught on `ops-equivalent`;
- B, a wrong store flag: caught on `import-equivalent`, by the count assertion;
- C, a plain cut left out: caught on `ops-equivalent` and `events-equivalent`
  through the plain edge count;
- D, a wrong expected node flag with equal counts: caught by the
  registered-content check on `ops-equivalent`, `events-equivalent` and
  `import-equivalent`.

As intended, A is not detected on `events-equivalent`: the API reports no
per-event results there, so the final-state checks apply instead.
