# v0.7.0 re-qualification: independent reviews

Reviews by separate reviewer agents that did not write the reviewed code or
text. Each read the sources and evidence itself; none edited anything.

## 1. Interference marking (`scripts/report_v070r_interference.py`), before the analysis

- Reviewed `fa9bfa00` against PROTOCOL.md §10.3 and the a3-3 records.
- Blockers (fixed in `4eb765fc`):
  - R and M_reg cells split into warmup and analyzed rows (cell form of the
    frozen analyzer not followed);
  - floating-point artefact: children at exactly 25% marked as above.
- Should-fix (fixed): resolution flag wrong when only sampled %CPU is over;
  missing CPU records silently scored zero.
- Minors fixed (`4eb765fc`, `31a0577b`): stricter B/C mapping, report notes,
  strict cell form, required B/C fields.
- Re-verification: all findings fixed; independent recount 11 of 201 cells.

## 2. Comparison report (`COMPARISON-v0.6.0-v0.7.0.md`)

- Reviewed `86c8ef12`. Every number checked against the archived analyses,
  chain steps, load ranges, identities and gate records: all A, R, Rmem and
  M_reg rows, the B/C non-PASS and near-tolerance rows, C3/C4, M_desc.
  `analyze_bc_qualification.py` re-run from the frozen clone: byte-identical.
  `analysis-sha256.txt` 12/12 OK. All 11 re-qualification directories in the
  §2 table with the right causes.
- Wording against the project rules: no acceptance, waiver, recommended
  disposition or inherited decision; status line correct; statistics and
  conformance kept separate.
- Blockers: none.
- Should-fix (fixed in `d3718c4c`): near-tolerance A cell not flagged; a3-2 A
  outputs not checksummed; re-measurement options could read as a rerun
  replacing the final attempt; maintainer approval of the cross-check basis
  not recorded (now `REPORTING-DECISIONS.md`); cross-check deviation
  imprecise.
- Minors (fixed): tick wording, background share qualification, 503 context,
  speculation removed, M_reg client counts, `release-cells` claim, "source"
  wording, `metrics.rs` wording, restore re-check described as unarchived.
- Re-verification of `86c8ef12..d3718c4c`: all fixed, no new blocker or
  should-fix; one trivial minor (a3-1 "no measurement outputs") fixed in the
  next commit.

## 3. Diagnostics (`diagnostics/`, ordered 2026-11-19)

- Reviewed `73db6711`: numbers re-run from raw (D2 `summarize.py`, D3/D4
  `phases.py`, D1 summary, D5 logs); all reproduce.
- Blockers: none.
- Should-fix (fixed in `12391bcc`):
  - D4 outside-handler share (15–40%, not 30–40%) and verdict-leaning
    wording;
  - D1 arm F builds different structures from L (the lifecycle engine holds
    only effective edges), and the volume share depends on the method
    (82–93%);
  - D3 overclaim and B1 context;
  - unlabelled departures in D2, D3, D4;
  - D5 rests on a synthetic reproduction (and its stale-token source differs
    from a3-3's);
  - summary claims about departures and run counts.
- Re-verification: all fixed, no new findings except trivial minors.
  - The D1 sentence was rephrased.
  - The superseded commit subject of `bead50c2` ("overhead entirely in core
    lifecycle apply") is history; D3's README is authoritative.
