# v1.1.0 qualification: release decision record

Three separate statements, which should not be confused:

1. **Campaign: CF5 attempt 1, FINAL** ([`REPORT.md`](REPORT.md)). Session
   execution complete; conformance accepted with one explicit exception (D1);
   all 226 comparisons have an outcome.
2. **Qualification of the CF5 results for candidate `02cba68`: ACCEPTED
   WITH EXCEPTIONS** (maintainer, 2026-11-25), with the dispositions D1–D5.
   - This is **not** "all gates PASS", and **not** a complete qualification.
   - No regression check of the existing engines against v1.0.0 (V1, V2) is
     REGRESSION or FAIL.
   - Five regression checks are left open on performance (D3): two
     UNRESOLVED and one INCONCLUSIVE_DISCLOSED (V1, HTTP cells with
     `compact-bfs`), two TIMER_LIMITED (V2, `ett`). Each keeps its class; none
     is a regression or a pass.
   - Host swap activity is not verifiable; the results are accepted by the
     maintainer with this limitation (D1). It applies to every class, PASS
     included.
   - `cluster-forest` is released **opt-in and experimental**;
     `compact-bfs` stays the default (D4). Its two lifecycle C3 FAILs on the
     sparse 1 000-node graph are a documented limitation (D5); memory
     stability for those two workloads stays open.
   - Every original class, interval and threshold stands as computed.
     Nothing was converted into PASS and nothing was measured again.
3. **Transfer of these results to the final v1.1.0 build: OPEN.** The
   maintainer has not decided it yet; see "Transfer to the release build"
   below. Until it is decided, the results describe `02cba68`, not the
   v1.1.0 binaries.

The decisions D1–D5 and their reasons are in `REPORT.md` section 7, taken by
the maintainer on 2026-11-25 after the session. This file states only the
release-level outcome they add up to; it changes no class.

## What was measured and what is released

| | |
|---|---|
| Measured candidate | knotrel `02cba6825f9ad9ef769f4006428ccad5509076e9` (crate version 1.0.0 on `main`, never released) |
| Reference (V1, V2) | published knotrel v1.0.0, tag `v1.0.0` = `d38df5f9fb935e95de6f7195d8bb1d5d9a458be9`, built from source alongside the candidate |
| Released | knotrel v1.1.0, built from `main` after `02cba68` |
| Delta between the two | documentation and doc comments (including doctests), CI configuration, release checks, version metadata, the console's development tooling (`typescript` 5.9.3 → 6.0.3), and one runtime dependency patch update of the server: `sonic-rs` 0.5.11 → 0.5.12 (JSON) |

## Transfer to the release build (open)

**Decision: pending.** Binary identity with the measured build and a new
measurement of v1.1.0 are not claimed.

Analysis of the only runtime change, `sonic-rs` 0.5.11 → 0.5.12 (knotrel#167),
for the maintainer's decision:

- The published crates differ in one source file, `src/value/node.rs`, plus
  version metadata, the crate's own `Cargo.lock` (not used by knotrel's
  build) and an added upstream test suite. In knotrel's `Cargo.lock` only the
  `sonic-rs` entry changes; no other dependency moves.
- The change is confined to the DOM type `sonic_rs::Value`: `Value::clone`
  of a node of a parsed document takes the DOM reference differently for a
  root and for a borrowed child (upstream test: a cloned child outlives its
  owners), a node's kind is read with `get_kind` instead of `get_type`, and
  `get_type` is marked `#[inline]`.
- `knotrel-server` calls `sonic-rs` in one place, `parse_import_body`
  (`api.rs`): `sonic_rs::from_slice::<ImportRequest>`, typed serde
  deserialization of the import body into structs of strings, integers and
  vectors. It never builds or clones a `sonic_rs::Value`, so the changed code
  is not instantiated on any measured path (import, readiness, M_reg import
  cells, S3).
- Assessment: no plausible performance or behavior impact on the measured
  paths. The smallest verification that would settle it: build
  `knotrel-server` at `02cba68` twice, once with each `sonic-rs` version
  (only `Cargo.lock` differs), and compare the `__TEXT,__text` section of
  the two binaries. Identical sections show that the update changes no
  executed code.

## Where the results are published

- Release entry (V1, V2 against v1.0.0): benchmark site, release 1.1.0
  (`docs/data/releases.json`, exported by `scripts/export_cf5_release_site.py`).
- `cluster-forest` against `compact-bfs`, ETT and HDT: benchmark site, engine
  comparison `cluster-forest-cf5-02cba68` (`docs/data/engine-comparisons.json`).
- Every cell, metric and interval: `analysis/attempt1/`.
