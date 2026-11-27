#!/bin/sh
# Builds the impact-estimate arms (protocol: knotrel docs/design/bidirectional-bfs-layer-fix-impact-estimate.md).
# --locked where the lockfile serves the arm; otherwise the lockfile is derived offline and the diff recorded.
set -u
E=$(cd "$(dirname "$0")" && pwd)
CB="cargo +1.100.0 build --release --offline"
build() { # arm name dir target-name args...
  arm=$1; dir=$2; tname=$3; shift 3
  log=$E/logs/build-$arm-$tname.log
  if ( cd "$dir" && CARGO_TARGET_DIR=$E/targets/$arm-$tname $CB --locked "$@" ) > "$log" 2>&1; then
    echo "$arm $tname locked"
  else
    cp "$dir/Cargo.lock" "$E/logs/$arm-$tname.Cargo.lock.orig"
    if ( cd "$dir" && CARGO_TARGET_DIR=$E/targets/$arm-$tname $CB "$@" ) >> "$log" 2>&1; then
      diff "$E/logs/$arm-$tname.Cargo.lock.orig" "$dir/Cargo.lock" > "$E/logs/$arm-$tname.lock-derivation.diff"
      echo "$arm $tname derived-lock ($(grep -c '^[<>]' "$E/logs/$arm-$tname.lock-derivation.diff") lines)"
    else
      echo "$arm $tname FAILED"; return 1
    fi
  fi
}
for arm in prev fix v110; do
  build $arm "$E/src/$arm/knotrel-benchmarks" harness -p knotrel-benchmarks --bin knotrel-benchmarks
done
for arm in prev fix; do
  build $arm "$E/src/$arm/knotrel-benchmarks/tools/lifecycle-probes" probes --bin core-lifecycle
  build $arm "$E/src/$arm/knotrel/integrations/postgres-feeder" feeder --bin knotrel-pg-feeder --example load
done
