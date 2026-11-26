#!/bin/sh
# Builds the knotrel#151 comparison tools once per arm (knotrel
# docs/design/compact-node-index.md, section 6.1) and writes the tool map for
# scripts/run_151.py. It never measures.
#
# Usage: build_151_probes.sh BASE_CHECKOUT CAND_CHECKOUT OUT [--overlay] [--relock]
#
#   BASE_CHECKOUT, CAND_CHECKOUT  knotrel checkouts of the two arms (CUR and B)
#   OUT                           a new directory (refused if it exists)
#   --overlay                     copy this knotrel-benchmarks working tree (uncommitted
#                                 changes included) over the clone; for development and
#                                 smoke runs only, never for a campaign
#   --relock                      build the probes without --locked (the probe lockfile
#                                 names another knotrel-core version); the lockfile
#                                 difference is saved under OUT/logs and the clone's
#                                 lockfile is restored with git checkout afterwards
#
# The method of release-cells (tools/lifecycle-probes/src/bin/release-cells.rs): the
# same probe source is built against each checkout. Per arm, OUT/arms/ARM holds a
# symbolic link knotrel -> the checkout and a clone of this repository at HEAD
# (knotrel-benchmarks), so the probe crate's ../../../knotrel path names the arm's
# checkout. One target directory per arm: knotrel-server (from the checkout,
# --locked), compact-cells, release-cells, http-lifecycle, core-lifecycle (default
# features) and memory-peak (peak-alloc). Toolchain 1.100.0, --release --offline.
# When both arms name the same checkout (an A/A smoke), it is built once and both
# arms point to it (recorded as "shared_build" in the tool map).
set -eu
BASE=$1
CAND=$2
OUT=$3
shift 3
OVERLAY=0
LOCKED=--locked
for X in "$@"; do
  case "$X" in
    --overlay) OVERLAY=1 ;;
    --relock) LOCKED= ;;
    *) echo "unknown option $X" >&2; exit 3 ;;
  esac
done
BREPO=$(cd "$(dirname "$0")/.." && pwd)
SHA=$(git -C "$BREPO" rev-parse HEAD)
if [ -e "$OUT" ]; then echo "refusing to reuse $OUT" >&2; exit 3; fi
mkdir -p "$OUT/logs" "$OUT/arms"
OUT=$(cd "$OUT" && pwd)
BASE=$(cd "$BASE" && pwd -P)
CAND=$(cd "$CAND" && pwd -P)
CB="cargo +1.100.0 build --release --offline"

build_arm() {
  ARM=$1
  CHECKOUT=$2
  D=$OUT/arms/$ARM
  mkdir -p "$D"
  ln -s "$CHECKOUT" "$D/knotrel"
  git clone --quiet --shared "$BREPO" "$D/knotrel-benchmarks"
  git -C "$D/knotrel-benchmarks" checkout --quiet --detach "$SHA"
  if [ "$OVERLAY" = 1 ]; then
    rsync -a --exclude target --exclude results --exclude .git "$BREPO/" "$D/knotrel-benchmarks/"
  fi
  T=$D/target
  ( cd "$CHECKOUT" && CARGO_TARGET_DIR=$T $CB --locked -p knotrel-server --bin knotrel-server ) \
    > "$OUT/logs/build-$ARM-server.log" 2>&1
  P=$D/knotrel-benchmarks/tools/lifecycle-probes
  # shellcheck disable=SC2086 # LOCKED is empty or one flag
  ( cd "$P" && CARGO_TARGET_DIR=$T $CB $LOCKED --bin compact-cells --bin release-cells \
      --bin http-lifecycle --bin core-lifecycle ) > "$OUT/logs/build-$ARM-probes.log" 2>&1
  # shellcheck disable=SC2086
  ( cd "$P" && CARGO_TARGET_DIR=$T $CB $LOCKED --features peak-alloc --bin memory-peak ) \
    > "$OUT/logs/build-$ARM-probes-peak.log" 2>&1
  if [ -z "$LOCKED" ]; then
    git -C "$D/knotrel-benchmarks" diff -- tools/lifecycle-probes/Cargo.lock \
      > "$OUT/logs/lock-$ARM.diff" || true
    git -C "$D/knotrel-benchmarks" checkout --quiet -- tools/lifecycle-probes/Cargo.lock
  fi
}

build_arm base "$BASE"
if [ "$CAND" = "$BASE" ]; then
  ln -s base "$OUT/arms/cand"
  SHARED=1
else
  build_arm cand "$CAND"
  SHARED=0
fi

python3 - "$OUT" "$BASE" "$CAND" "$SHARED" "$OVERLAY" "${LOCKED:-relocked}" <<'PY'
import json, os, sys
out, base, cand, shared, overlay, locked = sys.argv[1:]
tools = {}
for arm in ("base", "cand"):
    d = f"{out}/arms/{arm}"
    r = f"{d}/target/release"
    bench = f"{d}/knotrel-benchmarks"
    tools[f"compact_cells_{arm}"] = [f"{r}/compact-cells"]
    tools[f"memory_peak_{arm}"] = [f"{r}/memory-peak"]
    tools[f"release_cells_{arm}"] = [f"{r}/release-cells"]
    tools[f"http_lifecycle_{arm}"] = [f"{r}/http-lifecycle"]
    tools[f"core_lifecycle_{arm}"] = [f"{r}/core-lifecycle"]
    tools[f"http_pages_{arm}"] = ["python3", f"{bench}/scripts/http_pages_151.py",
                                  "--server-bin", f"{r}/knotrel-server",
                                  "--emit-bin", f"{r}/compact-cells"]
    tools[f"_server_{arm}"] = f"{r}/knotrel-server"
bench = f"{out}/arms/cand/knotrel-benchmarks"
tools["_delegated"] = {"Q": {
    "argv": ["python3", f"{bench}/scripts/inspection_q_151.py",
             "--base-server", tools["_server_base"], "--cand-server", tools["_server_cand"],
             "--base-checkout", base, "--cand-checkout", cand, "--out", "{run}"],
    "cwd": bench,
    # The check runs from the candidate clone, whose own roots do not cover the base
    # arm, the two checkouts or the run directory: allow them explicitly (cli_paths).
    # Run directories must therefore lie in the directory that contains OUT.
    "env": {"LIFECYCLE_QUALIFICATION_ROOTS": os.pathsep.join(
        [os.path.dirname(out), base, cand])}}}
tools["_checkouts"] = {"base": base, "candidate": cand, "benchmarks": bench}
tools["_lockfiles"] = [f"{base}/Cargo.lock", f"{cand}/Cargo.lock",
                       f"{bench}/tools/lifecycle-probes/Cargo.lock"]
tools["_build"] = {"shared_build": shared == "1", "overlay": overlay == "1",
                   "probes_locked": locked != "relocked"}
json.dump(tools, open(f"{out}/tools.json", "w"), indent=1)
PY
( cd "$OUT" && find arms/*/target/release -maxdepth 1 -type f -perm -u+x -print0 2>/dev/null \
    | xargs -0 shasum -a 256 > binaries-sha256.txt ) || true
echo "BUILT $OUT (tools: $OUT/tools.json)"
