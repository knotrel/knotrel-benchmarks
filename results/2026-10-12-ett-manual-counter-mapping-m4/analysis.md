# Manual-counter mapping validation

## Method

The original template was hashed before use and was never written. The probe
used the supported `xctrace record --recording-options` mechanism to derive:

1. eight configurations with exactly one event each; and
2. one configuration with all eight events in reverse order.

Each derived configuration was accepted by `xctrace --show-recording-options`
before recording. All nine recordings and their `counters-profile` exports
succeeded. The full original configuration from the preceding fixed probe was
also inspected for the duplicate-group check.

## Observed mapping

Every nonzero `pmc-events` sample from a one-event configuration had width two
and both values were identical. The event identity is unambiguous because the
derived recording options contain exactly that one archived event payload.

| Exported positions in the first group | Validated event |
| --- | --- |
| 0 | `FIXED_CYCLES` |
| 1 | `CORE_ACTIVE_CYCLE` |
| 2 | `BRANCH_MISPRED_NONSPEC` |
| 3 | `L1I_CACHE_MISS_DEMAND` |
| 4 | `INST_ALL` |
| 5 | `ARM_L1D_CACHE_RD` |
| 6 | `ARM_L1D_CACHE_LMISS_RD` |
| 7 | `ARM_STALL_BACKEND` |

The full-reversed configuration exported width-16 samples. Positions 0–7
contained the reverse sequence, with readily distinct retired-instruction,
L1D-read, backend-stall, branch-misprediction, and cycle magnitudes appearing
at their corresponding reversed positions. Positions 8–15 were an exact copy
of positions 0–7 in every nonzero sample. The earlier full-original
configuration has the same exact duplication property: 5,850 nonzero
width-16 samples each had `values[0:8] == values[8:16]`.

This establishes that the XML array consists of the eight configured events in
recording-option order followed by an identical duplicate group. Analyses must
use positions 0–7 only, reject any row not having two identical groups, and
never sum both groups.

## Remaining uncertainty and interpretation boundary

Counter magnitudes differ between recordings because the sampled process,
sampling windows, core placement, and counter multiplexing differ. The probe
establishes event-to-position mapping, not cross-recording numerical equality.
Replay-scoped aggregation must still select only target-process samples that
overlap `measurement-replay`.

`ARM_L1D_CACHE_LMISS_RD` is a Level-1 data-cache long-latency read-miss
counter. It is not a page-fault or TLB-miss counter. The template has no TLB
event, so no TLB conclusion is permitted.
