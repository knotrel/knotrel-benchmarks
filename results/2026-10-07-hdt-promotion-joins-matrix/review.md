# Independent review

Collection, analysis and audit match the declared 38 cells, 304 processes and
four balanced pairs per cell. Review found one reporting edge case: exact ties
must not count as slower pairs. It was corrected before collection finalized,
using an explicit positive-paired-delta count; measured binaries were unchanged.

Final review: no actionable findings. All 304 processes succeeded. All 12 block
cells improve 7.03%–13.11%, with 46/48 faster pairs. Seven regression flags remain:
six path and one dense. Keeping the candidate isolated is justified; no cause is
assigned to the control regressions without further evidence.
