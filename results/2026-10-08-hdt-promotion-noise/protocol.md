# Adaptive regression diagnosis, 2026-10-08

Select all seven flagged cells from the extended promotion-only matrix. No new
candidate. Reuse exact frozen binaries and traces. For each cell run four pairs
of AA_before (same baseline binary on both sides), AA_after (same candidate binary
on both sides), and AB (baseline vs candidate): 168 sequential processes.
Shuffle all 84 pairs with seed42; balance left-first/right-first 2/2 per cell/mode.
Keep each pair adjacent. Preserve failures, raw timing, setup, RSS, counters.

These cells are adaptively selected. Do not pool with prior studies. A/A
percentage changes are measurement variation, not algorithmic changes; compare
magnitude and direction with contemporaneous A/B. Four pairs cannot establish
equivalence or reliably attribute a causal effect. Keep the original seven flags.
Report every case. Do not remove outliers or subtract A/A changes from A/B.

After timing, disassemble the frozen binaries and compare ordinary forest link,
cut/query paths where symbols permit. Normalize addresses only with documented
rules; retain raw excerpts. A changed code layout is not proof of a performance
cause. No production patch, staging or commit is authorized by this diagnostic.
