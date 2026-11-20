# Equivalence smoke runs (checks only, not measurements)

Before the freeze, each of the 13 capability-equivalent B/C cells was run at
its real size and arguments (window multipliers applied), with 2 pairs and no
warmup. The purpose was the equivalence checks of `http-lifecycle`:
- per-operation outcomes;
- final counts;
- the registered content of the candidate;
- the content of the plain server.

Every cell completed the checks. (Revision 2 found that two of them, hub ops
and hub events, are not equivalent: see below.) `smoke-final.txt` records the tooling commit, the knotrel
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

## Revision 2 (2026-11-20)

`smoke-r2-draft.txt` repeats the 13 cells with the revision-2 probe, which
records atomicity per pair (PROTOCOL §4.3). All 13 exit 0 and complete every
functional check of §4.4 (outcomes, counts, registered content, plain
content). **Only 11 are equivalent**; completing the functional checks does
not make the other two equivalent:
- **Hub ops and events: not equivalent.** They need 39 and 76 plain requests
  against 37 and 74. Their largest single command expands to 1,565 plain
  operations, so `atomicity_equivalent: false`.
- **Every other planner cell:** one plain request per chunk, at most 15
  plain operations per command.
- **Import cells:** the field does not apply. Each import is one atomic
  publication on both sides.

That file comes from a build made before the tooling commit. The pre-freeze
smoke of revision 2 is repeated from the reviewed tooling.

**Pre-freeze smokes of revision 2 (tooling d9b98997, clean builds).** These
are functional and completeness checks, not qualification data. No threshold
or criterion was set or changed from them.
- `smoke-r2-final.txt`: the 13 equivalent cells, the same results as the
  draft. All 13 complete the functional checks; 11 are equivalent; hub ops
  and hub events are not (max 1,565 plain operations per command).
- `t5-smoke.txt`: the whole T5 plan (84 runs) through the frozen collector,
  with the gate replaced by a direct call. Every run exits 0. Within each
  topology all runs share the same compaction cycles (30, at 20, 40, …,
  600), call count and digests. The analyzer accepts the collection. Its
  statuses and ratios are deliberately not recorded: the data came from an
  ungated, non-quiesced host and decide nothing.
