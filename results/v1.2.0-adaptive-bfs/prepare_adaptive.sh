#!/bin/sh
# Prepares the adaptive-BFS impact estimate (knotrel docs/design/adaptive-bfs-impact-estimate.md,
# sections 2, 3 and 5, block 0): checkouts per arm, builds, V1 identities and the two core-only
# V1 plans, and their dry runs. No measurement.
#
# Usage: prepare_adaptive.sh CAND_SHA TOOLING_SHA
set -eu
CAND=$1; TOOLING=$2
V110=57c35e8d4b17bfce2d9941419ef251a2a2a1d69c
BFS196=9faf168b4a12a91faddddbdfac16eac5a4b2236d
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675
KREPO=${KNOTREL_REPO:-/Users/rt/workspace/knotrel/knotrel}
BREPO=${BENCH_REPO:-/Users/rt/workspace/knotrel/knotrel-benchmarks}
EVIDENCE=${EVIDENCE_ROOT:-/Users/rt/workspace/knotrel/evidence}
SOURCE_MANIFEST=$EVIDENCE/p0-coverage-increment-1-plan-20261030/manifest.json
SOURCE_MANIFEST_SHA256=95dfdabd165863c832473cd756441c0b825a846a64be45367b52901e2f6c8d42
[ "$(shasum -a 256 "$SOURCE_MANIFEST" | cut -d' ' -f1)" = "$SOURCE_MANIFEST_SHA256" ] || { echo "source manifest mismatch" >&2; exit 3; }
E=$EVIDENCE/v1.2.0-adaptive-bfs-$(echo "$CAND" | cut -c1-7)
[ -e "$E" ] && { echo "refusing to reuse $E" >&2; exit 3; }
mkdir -p "$E/logs" "$E/targets" "$E/src" "$E/A/sources" "$E/A/build-inputs"
L=$E/logs; T=$E/targets
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }
for arm in v110:$V110 bfs196:$BFS196 cand:$CAND; do
  n=${arm%%:*}; r=${arm#*:}
  clone "$KREPO" "$E/src/$n/knotrel" "$r"
  clone "$BREPO" "$E/src/$n/knotrel-benchmarks" "$TOOLING"
done
clone "$KREPO" "$E/A/sources/B/knotrel" "$V110"
clone "$KREPO" "$E/A/sources/C/knotrel" "$CAND"
clone "$BREPO" "$E/A/sources/knotrel-benchmarks" "$HARNESS"
for X in B C; do   # the #182 A build-input derivation: only the knotrel-core version line changes
  V=$(grep -m1 '^version' "$E/A/sources/$X/knotrel/Cargo.toml" | cut -d'"' -f2)
  I=$E/A/build-inputs/$X/knotrel-benchmarks
  mkdir -p "$I"
  cp -R "$E/A/sources/knotrel-benchmarks/Cargo.toml" "$E/A/sources/knotrel-benchmarks/crates" "$E/A/sources/knotrel-benchmarks/rust-toolchain.toml" "$I/"
  python3 - "$E/A/sources/knotrel-benchmarks/Cargo.lock" "$I/Cargo.lock" "$V" <<'PY'
import re, sys
src, dst, version = sys.argv[1:]
new, count = re.subn(r'(name = "knotrel-core"\nversion = ")[^"]+(")', r'\g<1>' + version + r'\2', open(src).read())
assert count == 1, count
open(dst, "w").write(new)
PY
  ln -s "../../sources/$X/knotrel" "$E/A/build-inputs/$X/knotrel"
done
CB="cargo +1.100.0 build --release --offline"
build() { # name dir target args...  (--locked; else derived lockfile, diff recorded)
  name=$1; dir=$2; tgt=$3; shift 3
  if ( cd "$dir" && CARGO_TARGET_DIR=$T/$tgt $CB --locked "$@" ) > "$L/build-$name.log" 2>&1; then
    echo "$name locked" >> "$L/build-summary.txt"
  else
    cp "$dir/Cargo.lock" "$L/$name.Cargo.lock.orig"
    ( cd "$dir" && CARGO_TARGET_DIR=$T/$tgt $CB "$@" ) >> "$L/build-$name.log" 2>&1
    diff "$L/$name.Cargo.lock.orig" "$dir/Cargo.lock" > "$L/$name.lock-derivation.diff" || true
    echo "$name derived-lock" >> "$L/build-summary.txt"
  fi
}
for n in v110 bfs196 cand; do
  build $n-harness "$E/src/$n/knotrel-benchmarks" $n-harness -p knotrel-benchmarks --bin knotrel-benchmarks
  build $n-probes "$E/src/$n/knotrel-benchmarks/tools/lifecycle-probes" $n-probes --bin core-lifecycle
  build $n-server "$E/src/$n/knotrel" $n-server -p knotrel-server --bin knotrel-server --example measure_e2e
done
build feeder "$E/src/bfs196/knotrel/integrations/postgres-feeder" feeder --bin knotrel-pg-feeder --example load
for X in B C; do
  build A-$X-harness "$E/A/build-inputs/$X/knotrel-benchmarks" A-$X-harness -p knotrel-benchmarks --bin knotrel-benchmarks
done
( cd "$T" && find . -type f -path '*/release/*' -perm -u+x \( -name knotrel-benchmarks -o -name core-lifecycle -o -name knotrel-server -o -name measure_e2e -o -name knotrel-pg-feeder -o -name load \) -not -path '*/deps/*' -exec shasum -a 256 {} \; ) | sort -k2 > "$E/binaries.sha256"
# V1 identities (B = v1.1.0, C = candidate) and two core-only plans of 12 pairs per cell.
python3 - "$E" "$V110" "$CAND" "$HARNESS" <<'PY'
import hashlib, json, sys
e, ref, cand, harness = sys.argv[1:]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
ids = {"comparison_identities": {}, "shared_binaries": {}}
for label, commit, arm in (("B", ref, "v110"), ("C", cand, "cand")):
    k = f"{e}/A/sources/{label}/knotrel"
    hb = f"{e}/targets/A-{label}-harness/release/knotrel-benchmarks"
    sb = f"{e}/targets/{arm}-server/release/knotrel-server"
    lock = f"{e}/A/build-inputs/{label}/knotrel-benchmarks/Cargo.lock"
    ids["comparison_identities"][label] = {
        "binaries": {"knotrel_benchmarks": {"path": hb, "sha256": h(hb), "source_commit": harness},
                     "knotrel_server": {"path": sb, "sha256": h(sb), "source_commit": commit}},
        "checkouts": {"benchmarks_source": {"commit": harness, "path": f"{e}/A/sources/knotrel-benchmarks"},
                      "knotrel_source": {"commit": commit, "path": k}},
        "lockfiles": {"benchmarks_lock_derived": {"path": lock, "sha256": h(lock)},
                      "knotrel_lock": {"path": f"{k}/Cargo.lock", "sha256": h(f"{k}/Cargo.lock")}}}
m = f"{e}/targets/cand-server/release/examples/measure_e2e"
ids["shared_binaries"]["measure_e2e"] = {"path": m, "sha256": h(m), "source_checkout": f"{e}/A/sources/C/knotrel"}
json.dump(ids, open(f"{e}/A/identities.json", "w"), indent=1)
PY
B=$E/src/cand/knotrel-benchmarks
CELLS="core_sparse_traversal_10k_compact-bfs_warmed core_sparse_traversal_10k_compact-workspace_warmed core_sustained_churn_10k_compact-bfs_warmed core_sustained_churn_10k_compact-workspace_warmed"
LIFECYCLE_QUALIFICATION_ROOTS="$E:$(dirname "$SOURCE_MANIFEST")"; export LIFECYCLE_QUALIFICATION_ROOTS
# shellcheck disable=SC2086
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$E/A/plan1" --identities "$E/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --phase extension --cells $CELLS --checkpoint adaptive-bfs-V-Block1 --session-seeds 204110 204111 204112 ) > "$L/A-plan1.log" 2>&1
# shellcheck disable=SC2086
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$E/A/plan2" --identities "$E/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --phase extension --cells $CELLS --checkpoint adaptive-bfs-V-Block2 --session-seeds 204120 204121 204122 ) > "$L/A-plan2.log" 2>&1
for P in plan1 plan2; do
  ( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$E/A/$P/manifest.json" --schedule "$E/A/$P/schedule.json" --dry-run ) > "$L/A-$P-dry-run.log" 2>&1
done
cat "$L/build-summary.txt"
echo "PREPARED $E"
