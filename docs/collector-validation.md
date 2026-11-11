# Collector Qualification And Resource Boundaries

These scripts are experimental measurement tools, not acceptance of an algorithm
or a release. Repairs to reusable tooling do not retrospectively qualify or
invalidate historical campaigns. Examine the frozen collector and raw artifacts
actually used in a campaign before drawing any conclusion about its results.
Candidate A remains unaccepted; production FIFO remains parked as inconclusive.
P0, M3.1 and v0.3.0 remain open.

## Validation Versus Analysis

The P0 core reader retains schema versions 2, 3 and 4 and its legacy comparison
envelope handling. It validates every repetition of the selected report against
the requested workload/configuration, operation counts, query partitions and
numeric latency fields. The legacy envelope still selects the first comparison
report; it does not qualify every other engine in an unsolicited comparison.
P0 analysis still selects the first repetition's metrics, not their average or
median. Complete validation does not change that historical selection rule.

Requested query controls are checked against both cell metadata and any matching
argv flags. Conflicting requests, boolean/float values and mismatched reports
fail qualification. Legacy reports may omit query_repeats only for its zero
default, and sustained query_percent only for its 50-percent default. Native
chain reports need not include query_percent; their mix remains native and a
nondefault percentage is not accepted. These compatibility defaults do not permit
an omitted field to satisfy an explicitly requested nondefault value.

HTTP lifecycle and batch readers require exactly the configured number of runs,
validate every run and preserve the original first-run exports. Both zero-based
legacy fixture indices and one-based driver indices are supported; indices must
then be consecutive. Configuration, server provenance, seed, required phase
timings, counters, oracle/verification results, latency and sampled memory are
checked. Historical batch reports without warmup-chunk metadata retain the
one-request/50-query interpretation.

JSON readers reject duplicate fields and non-JSON NaN/Infinity constants. Negative,
boolean or malformed numeric samples are not accepted as measurements. Valid
zero-duration latency samples remain valid; no positive per-operation latency or
new numerical regression threshold is assumed. The Candidate A reader retains its
existing median-over-three-repetitions analysis and positive primary wall-time
requirement for ratio calculations. No historical report is rewritten.

## Observation And Capture Limits

The shared process observer drains stdout/stderr with a selector under one combined
raw-byte limit (default 1 MiB, configurable through output_limit_bytes). It never
buffers arbitrary streams before checking their size. Overflow and timeout stop
the dedicated process group and reap the direct child. Abnormal parent exit also
stops surviving descendants. Captured prefixes, timestamps, argv/cwd/environment,
exit/status, failure reason, capture counts and reap status remain available.
Undecodable UTF-8 prefixes additionally retain their exact bytes as base64.
If Popen never succeeds, PID and streams are null: no output is fabricated.
Every caller rejects status=failed or a nonempty failure_reason before parsing,
even if the process exits zero and its captured stdout is valid JSON. Existing
timeout/nonzero-exit classification is retained. The failed observation is saved
and no subsequent invocation is launched.

Candidate A writes an observation before exit/timeout/RSS/parser qualification and
updates it explicitly on failure. Failed observations cannot become parsed_valid,
and collection does not retry them. Successful pair/report output remains
compatible; observation files and metadata fields are additive. Fake mode marks
its metadata and emits schema-valid synthetic reports without launching a child.

Candidate A's 100-MiB limit is checked before each collector-owned JSON write,
including schedule, observation, report, pair, analysis and final metadata.
Before launch, the actual argv/full-command, cwd, environment and observation
envelope are serialized to size their metadata, including quotes, backslashes
and non-ASCII escaping. Space covers the two stored raw-stream copies; their
allowance includes worst-case JSON escaping, replacement decoding and optional
base64. Parsed reports and other duplicated structures are checked at their
actual encoded size on every write. Insufficient space can stop collection after
a successful capture without losing the saved observation.

Failure reservation is metadata-aware and at least 64 KiB, covering completion
fields and bounded failure reasons as well as invocation overhead. If even full
preflight metadata cannot fit, a compact failure record states the omission and
serialized size; no child is launched. The initial observation write is inside
the failure handler, so its failure cannot bypass failed campaign status.
Exhaustion stops new launches. This assumes
exclusive ownership of the newly created destination; it is not a filesystem quota
against concurrent writers or an assurance that the disk cannot independently fill.
An observation-write error triggers a best-effort failed-record write and failed
metadata. This does not promise recovery from arbitrary disk exhaustion, permission
errors, concurrent filesystem changes or other unrelated I/O failure; such errors
can prevent persistence itself. A child invocation is never retried to compensate.

P0 and batch-warmup collectors perform pre-launch directory-size checks with failure
space reserved and a reduced capture limit, plus their retrospective boundary/final
directory-size checks. Those directory checks are not a hard aggregate filesystem
quota. Child-written HTTP JSON files are not capped while being written; readers
reject files over 1 MiB before loading/parsing them. Disk traffic from such files
can therefore exceed a boundary check between observations. Do not describe this
as a live disk-write bound or use untrusted children without external isolation.

RSS checks are retrospective observations, not imposed memory limits. No hard CPU,
address-space, process-tree RSS or child-created-file quota is imposed. Host checks
are boundary samples, not continuous environmental monitoring. These distinctions
must remain explicit in any future measurement protocol.

## Paths And Provenance

P0's historical default plan is derived relative to the sibling repository layout;
its --manifest and --schedule options accept explicit inputs. The batch runner's
binary defaults are similarly repository-relative and its --cwd overrides runtime
cwd. Historical expected hashes remain experiment-specific; relocating a binary
does not waive its hash check. Candidate A accepts explicit --baseline-sha256,
--candidate-sha256 and --cwd, preserving hash verification and recording its actual
sanitized runtime environment. Its default hashes remain historical identities,
not claims about whatever source happens to be checked out.

Tests generate plans, schedules, reports, placeholder binaries and lockfiles in
temporary directories from repository-owned synthetic factories. Provenance tests
check real fixture-file hashes and independently simulated Git identities. No
external evidence directory or historical executable is required. The repository
smoke-schema fixture uses synthetic server identity/path metadata.

Run the four collector suites with bytecode/cache output disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  scripts/tests/test_p0_aa.py scripts/tests/test_candidate_a_comparison.py \
  scripts/tests/test_batch_warmup_investigation.py scripts/tests/test_collector_validation.py
```

Only synthetic children are used by these suites. A collector source change and a
passing fake-mode test do not authorize a real performance campaign.