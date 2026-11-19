# Equivalence smoke runs (checks only, not measurements)

Before the freeze, each of the 13 capability-equivalent B/C cells was run at
its real size and arguments (window multipliers applied), with 2 pairs and no
warmup. The purpose was the equivalence checks of `http-lifecycle`:
- per-operation outcomes;
- final counts;
- the registered content of the candidate;
- the content of the plain server.

Every cell passed. `smoke-final.txt` records the tooling commit, the knotrel
candidate and the probe binary hash, and per cell the exit status and the
last record without timings. An earlier smoke file, from a probe version
before the review fixes and with truncated, timed lines, was replaced.

**Negative controls.** These ran on a scratch copy of the final probe source
with injected mutations, at 2k nodes. Each mutation was detected:
- A, a wrong per-operation outcome: caught on `ops-equivalent`;
- B, a wrong store flag: caught on `import-equivalent`, by the count assertion;
- C, a plain cut left out: caught on `ops-equivalent` and `events-equivalent`
  through the plain edge count;
- D, a wrong expected node flag with equal counts: caught by the
  registered-content check on `ops-equivalent`, `events-equivalent` and
  `import-equivalent`;
- E, a planned plain operation differing from the requests sent: caught on
  `ops-equivalent` and `events-equivalent`;
- F, a forwarded `connected` answer compared wrongly: caught on
  `ops-query-equivalent`.

**Request counts.** On `hub`, two lifecycle chunks expand into more than
1,024 plain operations. The frozen planner then splits each into two
requests: 39 requests against 37 for ops, 76 against 74 for events. Those
chunks lack the single-request atomicity the lifecycle batch has. This is a
residual limit of the equivalence (PROTOCOL §4.3).

As intended, A is not detected on `events-equivalent`: the API reports no
per-event results there, so the final-state checks apply instead.
