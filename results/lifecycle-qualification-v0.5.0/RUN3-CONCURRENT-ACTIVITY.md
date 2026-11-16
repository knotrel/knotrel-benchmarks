# Run 3 (`BC-final-a1d9577`): concurrent agent activity record

Recorded 2026-11-16 after the independent evidence audit. Run-3 data and
verdicts are unchanged.

## What ran during the collection

Collection interval (collector `host_before` timestamps): first cell
2026-11-16T07:52:37Z, last cell 08:06:18Z (365 cells, 825.1 s of cell time).

| Activity | Time evidence | Overlap |
|---|---|---|
| Python script rewriting section 2 of `evidence/v0.5.0-remediation/DIAGNOSIS.md` | file mtime 2026-11-16T07:52:51Z | inside cell 10, `B4-http-import-optin-compact-bfs-sparse-100000` (started 07:52:46Z, 8.109 s), a timed paired cell |
| Shell loop `until grep -q "[365/365]" BC-final-a1d9577.log; do sleep 15; done` (first instance, foreground, later moved to background by the tool timeout) | started right after the edit; start and stop times not logged | most of the collection; one `grep` every 15 s |
| A second identical loop (background) | started after the first moved to background; the first was then stopped; times not logged | from about 10 minutes into the run until the end; for a short time both loops ran |
| The agent harness itself (model calls, tool processes) | not logged | throughout, as in earlier runs |

Whether similar polling ran during runs 1 and 2 is not established from the
logs.

## Applicable rule

PROTOCOL.md §1 (host): "AC power, no concurrent builds or campaigns"; §5:
"No other campaign or build runs meanwhile". A file edit and a `grep` polling
loop are neither builds nor campaigns, so the text of the rule was not
violated. The analysis' mechanical validity checks (complete final profile,
exit codes, AC power, multipliers, clean build records) all passed. The
collection was nevertheless not made on a quiet host, which the earlier
reports did not disclose.

## What remains supported, and what would need a protocol decision

- **Unaffected by timing perturbation:** C1/C2 (logical counts and slot
  bounds) and the C-heap and B5 live-heap values are deterministic for a given
  build and schedule; run 3's 30-cycle heap series equal the D1-release series
  in all 45 C-heap cells.
- **Not established:** whether the concurrent activity changed any timing
  (B1-B4) or RSS (C4) value. No claim is made that it touched at most one
  window or could not change a verdict. The cells closest to their thresholds
  are `B4-http-ops-compact-bfs-sparse-10000` (+19.6% [13.6, 38.0], t = 25%),
  `B4-http-ops-compact-bfs-sparse-100000` (+22.7% [17.6, 25.5]),
  `B4-http-import-compact-bfs-sparse-10000` (+99.9% [93.3, 109.3], t = 100%),
  `B4-http-import-compact-bfs-sparse-100000` (+104.0% [101.2, 111.9]) and
  `B4-http-metrics-ops-compact-bfs-sparse-10000` (+4.4% [1.2, 6.6], t = 6%).
- **Decision needed (maintainer):** whether run-3 timing verdicts are accepted
  as collected under §5, given the undisclosed non-quiet host. The protocol
  allows no B rerun or extension; that rule is unchanged and no cell is
  re-sampled.
