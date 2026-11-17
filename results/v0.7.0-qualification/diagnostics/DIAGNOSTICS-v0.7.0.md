# v0.7.0 diagnostics: candidates 0.7.4a and 0.7.4b

**Diagnostic, not qualification.** These runs decide which candidates go to
the frozen v0.7.0 qualification. They grant no verdict against v0.6.0 or
v0.5.0. Each cell has 8 analyzed pairs (1 warmup pair), fresh process per
observation, balanced order. *Change* is `exp(median ln(cand/ref)) − 1`,
with throughput inverted so that **negative is better** everywhere; the range
is r(2)–r(7) of the paired changes. Evidence:
`evidence/v0.7.0-diagnostics/` (README, `SHA256SUMS`). Host and conformance:
Apple M3, AC power and activity gate before every child; the continuous
activity monitor did not run (disclosed in the evidence README).

## Da — shared read lock (0.7.4a), knotrel `008b9b1` vs v0.6.0 `48bc82f`

Contention probe revision 2 against a real server process, 100k nodes unless
noted.

| Cell | Throughput v0.6.0 → candidate | Change [range] | Client p99 | Change [range] | Lock wait / latency |
|---|---|---|---|---|---|
| read95 b1, 1 client | 1,530 → 1,540 req/s | −0.2% [−0.8, +0.3] | 1.84 → 1.85 ms | +0.3% [−0.6, +1.0] | ≈0 → ≈0 |
| read95 b1, 16 clients | 1,562 → 6,119 req/s | **−74.4%** [−74.7, −74.0] | 16.2 → 9.9 ms | **−39.5%** [−43.7, −31.7] | 0.93 → 0.40 |
| read95 b1, 64 clients | 1,259 → 5,050 req/s | **−74.9%** [−75.8, −74.4] | 58.7 → 23.3 ms | **−62.5%** [−64.2, −57.0] | 0.96 → 0.48 |
| read95 b8, 4 clients | 214 → 337 req/s | **−36.8%** [−38.2, −34.1] | 25.5 → 24.1 ms | −4.1% [−6.2, −0.7] | 0.74 → 0.58 |
| read95 b8, 16 clients | 205 → 354 req/s | **−41.7%** [−42.7, −41.4] | 92.9 → 97.6 ms | +2.9% [−3.1, +10.6] | 0.94 → 0.87 |
| read95 b1, 4 clients, 10k | 15,160 → 32,440 req/s | **−53.2%** [−53.4, −53.0] | 0.53 → 0.27 ms | **−49.9%** | 0.61 → 0.06 |
| mixed50 b8, 16 clients | 385 → 385 req/s | +0.2% [+0.0, +0.7] | 56.7 → 57.7 ms | +2.1% [−0.8, +7.0] | 0.93 → 0.93 |
| lifecycle on, lifecycle50 b8, 16 clients | 379 → 380 req/s | −0.7% [−1.2, +0.4] | 56.1 → 57.5 ms | −0.0% [−0.5, +6.2] | 0.93 → 0.93 |
| source-managed off, read100 b8, 16 clients, import every second | 199 → 961 req/s | **−79.3%** | 93.7 → 76.7 ms | **−18.2%** [−19.5, −17.2] | 0.94 → 0.01; imports 4 → 4 |
| source-managed on, read100 b8, 4 clients, feeder catch-up | 203 → 559 req/s | **−63.6%** | 26.8 → 14.0 ms | **−47.6%** | 0.75 → 0.27 |
| source-managed on, read100 b8, 16 clients, feeder catch-up | 206 → 893 req/s | **−76.9%** | 88.9 → 57.9 ms | **−33.8%** [−47.4, −27.7] | 0.93 → 0.50 |

**Feeder catch-up under query load** (events applied in the 4 s run):

| Clients | v0.6.0 → candidate | Change [range] | Feeder batch p50 |
|---|---|---|---|
| 4 | 31,260 → 63,520 | **−45.6%** (2.0× events) [−60.0, −35.3] | 0.12 → 5.6 ms (see below) |
| 16 | 3,648 → 21,060 | **−82.7%** (5.8× events) [−87.4, −77.9] | 77.5 → 13.5 ms |

Readings:
- **Pure query batches scale.** With batch 1 (and read100), throughput at 16
  and 64 clients is about 4× v0.6.0 on 8 cores (4 performance + 4
  efficiency), and lock wait falls from 0.93–0.96 to 0.40–0.50 of client
  latency.
- **Batches containing a mutation still serialize.** `read95` with batch 8
  makes about 34% of batches writers (1 − 0.95⁸), so at 16 clients lock wait
  is still 0.87 of latency and p99 does not improve (+2.9%, within
  tolerance); throughput still rises 73%. `mixed50` and `lifecycle50` are
  unchanged, as designed: a batch with a mutation keeps the whole graph
  exclusively. **M5 rule (i) therefore still holds for read-heavy batches
  that contain mutations** (it is re-evaluated descriptively in the
  qualification).
- **Feeder priority works as designed.** At 16 clients a feeder batch waits
  only for the readers inside the lock (p50 77 → 13 ms) and catch-up is 5.8×
  faster. At 4 clients the feeder batch median rises from 0.12 ms to 5.6 ms:
  under the mutex, with only 4 clients, the feeder often found the lock free;
  with parallel readers the lock is almost always held shared, so each feeder
  batch waits for the readers in flight. Catch-up throughput still doubles.
- **No regression** at 1 client (−0.2%, p99 +0.3%) or on writer-dominated
  cells beyond +2.1% p99 at the median.

**Decision under the declared rule: RETAIN 0.7.4a.**

## Db — sonic-rs import parse (0.7.4b, b2), knotrel `6654082` vs v0.6.0 `48bc82f`

| R cell | v0.6.0 → candidate (median) | Change [range] |
|---|---|---|
| HTTP import, sparse 100k, 60/30 | 28.580 → 23.550 ms | **−18.41%** [−20.08, −16.99] |
| HTTP import, sparse 100k, 20/10 | 28.190 → 23.735 ms | **−15.73%** [−17.44, −13.25] |
| HTTP import, sparse 10k, 20/10 | 2.471 → 1.980 ms | **−20.09%** [−21.28, −19.08] |
| core import, sparse 100k, 60/30 (control, no parse) | 11.434 → 11.451 ms | +0.35% [+0.04, +0.99] |

Rmem (deterministic allocator byte counts): peak and transient-over-final of
HTTP create 20/10, create 60/30 and replace 20/10 are **identical** to
v0.6.0 (32.6 / 31.2 / 50.4 MiB peaks). sonic-rs reads the body in place; the
v0.6.0 memory reduction is kept.

Against the v0.5.0 reference of the R cell (25.133 ms, comparison v0.5.0 →
v0.6.0 §3), the candidate's 23.55 ms median is about 6% faster; only the
qualification can state a verdict against v0.6.0.

**Decision under the declared rule: RETAIN 0.7.4b (b2, sonic-rs).**
**b1 (hand-written visitor): REJECTED** before Db by a micro-benchmark
(release build, 15 repetitions, 100k bodies): no faster than the derived
deserializers for flagged nodes (16.6 vs 16.0 ms at 60/30) and about 3 ms
slower for edges.

Disclosures for b2: measured on ARM64 only; sonic-rs is built without
target-specific CPU flags, and its speed on x86-64 release builds is not
measured.

## Not run

0.7.4c (allocator) and 0.7.4d (CSR) wait for maintainer decisions Q2 and Q4
of the design (`mimalloc` is already the server allocator; CSR retain
threshold).
