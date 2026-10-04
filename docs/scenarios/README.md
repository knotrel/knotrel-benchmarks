# Domain adapter contracts

Status: imported replay and the [Topology Zoo adapter](topology-zoo.md) are
implemented. Contacts and AML remain planned. See the
[source selection and licensing review](../research/2026-10-03-domain-scenarios.md).
The sections below define shared contracts and the remaining implementation gates.

## Shared normalization and reproducibility

1. Acquire an explicit artifact outside tracked results. Record source URL,
   retrieval date, immutable revision/version, file SHA-256, accompanying license
   and citation. Fail acquisition on checksum mismatch. No automatic bulk download.
2. Validate source schema and timestamp units. Keep original IDs as strings;
   assign dense u64 IDs by sorted UTF-8 source keys, using structured composite
   keys where necessary. Persist the mapping. Register the complete node universe,
   including isolates, before replay; this is an offline experiment.
3. Project to canonical undirected pairs `(min(u,v), max(u,v))`. Report discarded
   self-loops, duplicates, malformed records and every filter. Reject malformed
   records by default. Distinguish duplicate records from separate parallel events.
4. Process all changes at the same logical timestamp as one source batch. Compute
   the final active-pair set, then emit sorted cuts and sorted links for its set
   difference. Query only after the entire batch. Intermediate states are not
   domain observations; this does not add transactional semantics to the server.
5. Store batch boundaries and source time in a sidecar. The existing operation
   vector can express the kernel replay, but its generated-workload envelope must
   not be mislabelled as an imported trace. The implemented [import schema](topology-zoo.md#import-schema-1-and-report-schema-4)
   separates this envelope from generated trace exports.
6. Record query schedule, seed and exact PRNG/version. Include a fixed probe set
   and seeded distinct-node pairs independent of expected answers. Publish actual
   positive/negative counts and mutation/query ratios; do not force a 50/50 mix or
   select queries by an oracle outcome. Reject pair sampling if fewer than 2 nodes.

A repeated source event need not cause a kernel operation. Report source records,
source batches, normalized links/cuts and query counts separately. Every emitted
mutation must change the simple graph. Preserve all seed, window, selection and
horizon parameters in the manifest; never use process-randomized hash iteration
for ordering. Explicitly record whether IDs were selected from the full artifact
or a declared subset before mapping.

## Three scenarios

### Telecom: `topology-zoo-outages-v1` (implemented)

Use selected undirected GraphML topologies. Reject directed/mixed graphs and
unsupported hyperedges rather than silently changing their meaning. Preserve
parallel source edges as separate links with stable source identities; a pair is
active while at least one such link is up. Ignore self-loops with a reported count.

Start from the complete topology. Generate a seeded permutation of source links,
fail the first `k` one at a time, then restore them in reverse order. Persist the
exact permutation, PRNG, seed and `k` (bounded by link count). Query after each
failure/restoration batch, including batches without a projected mutation. This
is a controlled outage experiment, not a historical failure log. Select and pin
at least one topology with alternative paths; report bridges and component sizes
rather than claiming the sample represents all telecom networks.

### Contacts: `sociopatterns-contacts-20s-v1` (proposed)

Select the 2012 high-school release and its node metadata, subject to its license.
Each row `t i j Ci Cj` describes contact in the publisher's interval `[t-20s,t]`.
Treat each timestamp as a **discrete observation bucket**, not an instantaneous
arrival event or a cumulative historical relationship. Validate the 20-second
grid. Deduplicate identical bucket/pair observations and report their count.

For every bucket from first to last observed timestamp, the active set is exactly
its listed pairs. Empty buckets clear the graph, including overnight gaps; they
mean no recorded contacts, not proof nobody met. Consecutive buckets containing
the same pair produce no cut/link. Add one explicitly labelled empty terminal
bucket to expire the last contacts. Register metadata nodes even when unobserved;
reject unknown contact IDs pending explicit source reconciliation. Class is
metadata; gender is unnecessary and need not be imported. Query at bucket end.
This tests static connectivity of each observation, not temporal reachability.

### AML: `aml-data-window-v1` (proposed)

Pin one IBM AML-Data CSV artifact before fixing its concrete column mapping.
Identify accounts by `(bank_id, account_id)`, preserving strings and both endpoint
namespaces. Require an explicit source timestamp format, resolution and timezone
policy; reject ambiguity rather than inventing UTC. Amounts, currencies, direction
and laundering labels are metadata, not connectivity predicates.

A transaction at source time `s` contributes to its undirected pair at time `t`
exactly when `t-W < s <= t`, for configurable positive `W`. A 30-day window is an
experimental choice, not an AML rule. Process both transaction and expiry times,
including expiry-only batches. Stop after the final transaction's expiry, marking
this tail explicitly. Aggregate all expirations and arrivals at a timestamp before
computing transitions: link only on count 0 to positive, cut only on positive to 0.
Distinct identical transactions still count separately unless a verified source
transaction identifier proves duplication. Do not deduplicate by account pair.

For example, A-B transactions at times 0 and 5 with W=10 produce one link at 0,
no cut at 10, and one cut at 15. An arrival exactly when the last earlier event
expires keeps the pair active after that batch. This model measures association
within a window, not directed payment reachability or fraud detection quality.

## Correctness and measurement gates

Build small source fixtures without redistributing third-party data. Verify
parallel telecom links, isolates, contact gaps and duplicates, AML overlapping
transactions, exact expiry boundaries, composite IDs and same-time replacements.
Derive fixture expected adjacency directly from source records and the formal
interval predicates, independently of importer counters; compare all pairs with
an independent traversal or transitive closure. For acquired data, validate every
scheduled query outside timing, recording validation coverage and cost. Do not
use one projection implementation as both producer and sole oracle.

Time parsing, projection, setup and validation separately from kernel operations.
Report both kernel-only replay and, when implemented, end-to-end adapter cost.
Use identical normalized traces across backends, preserving immediate visibility.
Record repetitions separately, actual operation counts, tail latencies, source and
projected graph sizes, peak memory measurement method, build flags, hardware,
compiler, dependency locks, both repository revisions and dirty diffs.

Cache experiments must distinguish fresh graph state from cold hardware caches.
Run reproducible warmups and fresh-graph repetitions, repeated endpoint queries
and a seeded varied-endpoint schedule as separate variants. Rotate backend order
and preserve seeds. Record whether input files were already cached. Do not label
fresh-process or fresh-graph runs “cold cache” without a measured cache-control
protocol. Repeated fixtures alone do not establish production performance.

## Implementation order and acceptance

1. Add a validated imported-trace envelope/replay path, provenance manifest and
   independent fixture oracle. Preserve existing generated-trace compatibility.
2. Implement GraphML normalization and the telecom outage generator. Pin a small
   permitted source artifact by checksum; keep raw inputs outside Git. Validate
   queries, then compare compact, ETT/HDT and petgraph on identical operations.
3. Add bucket-contact normalization with synthetic fixtures first. Acquire real
   data only for usage consistent with its terms; document that boundary.
4. Add AML CSV schema mapping and window expiry with multiplicity. Pin the data
   version independently of the repository software revision.
5. Publish results and limitations only after reproducible runs. Use observed
   bottlenecks to decide further algorithm work; no speedup target is a result.

These steps do not require typed or nested graph support in the core. Any such
extension needs an explicit domain query contract and a separate ADR.
