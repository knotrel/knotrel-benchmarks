#!/bin/sh
# Prepares the B2 impact estimate (knotrel docs/design/b2-bounded-query-concurrency.md, approved
# 2026-11-27: option B, K = 4, 2 h). Builds once, then lays out two campaign directories in the
# layout of results/v1.2.0-qualification/run_q.sh, which runs the frozen block-Q procedure:
#   E/off: cand-server = the B2 build, KNOTREL_MAX_CONCURRENT_QUERIES unset
#   E/on : cand-server = a wrapper that execs the same B2 build with KNOTREL_MAX_CONCURRENT_QUERIES=4
#          (the load tool starts servers with a cleared environment, so the setting must travel
#          with the executable)
# Both: ref-server = v1.1.0 (the in-session Q5 reference), feeder and load tool from the B2
# checkout (integrations unchanged since v1.1.0). No measurement.
#
# Usage: prepare_b2.sh B2_SHA TOOLING_SHA
set -eu
B2=$1; TOOLING=$2
V110=57c35e8d4b17bfce2d9941419ef251a2a2a1d69c
KREPO=${KNOTREL_REPO:-/Users/rt/workspace/knotrel/knotrel}
BREPO=${BENCH_REPO:-/Users/rt/workspace/knotrel/knotrel-benchmarks}
EVIDENCE=${EVIDENCE_ROOT:-/Users/rt/workspace/knotrel/evidence}
E=$EVIDENCE/v1.2.0-b2-$(echo "$B2" | cut -c1-7)
[ -e "$E" ] && { echo "refusing to reuse $E" >&2; exit 3; }
mkdir -p "$E/build" "$E/logs"
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }
clone "$KREPO" "$E/build/b2" "$B2"
clone "$KREPO" "$E/build/v110" "$V110"
CB="cargo +1.100.0 build --release --locked --offline"
( cd "$E/build/b2" && CARGO_TARGET_DIR=$E/build/t-b2 $CB -p knotrel-server --bin knotrel-server ) > "$E/logs/build-b2-server.log" 2>&1
( cd "$E/build/v110" && CARGO_TARGET_DIR=$E/build/t-v110 $CB -p knotrel-server --bin knotrel-server ) > "$E/logs/build-v110-server.log" 2>&1
( cd "$E/build/b2/integrations/postgres-feeder" && CARGO_TARGET_DIR=$E/build/t-feeder $CB --bin knotrel-pg-feeder --example load ) > "$E/logs/build-feeder.log" 2>&1
REAL=$E/build/t-b2/release/knotrel-server
for MODE in off on; do
  C=$E/$MODE
  mkdir -p "$C/src/cand" "$C/logs" "$C/targets/cand-server/release" "$C/targets/ref-server/release" "$C/targets/feeder/release/examples"
  ln -s "$E/build/b2" "$C/src/cand/knotrel"
  clone "$BREPO" "$C/src/cand/knotrel-benchmarks" "$TOOLING"
  cp "$E/build/t-v110/release/knotrel-server" "$C/targets/ref-server/release/knotrel-server"
  cp "$E/build/t-feeder/release/knotrel-pg-feeder" "$C/targets/feeder/release/knotrel-pg-feeder"
  cp "$E/build/t-feeder/release/examples/load" "$C/targets/feeder/release/examples/load"
  if [ "$MODE" = off ]; then
    cp "$REAL" "$C/targets/cand-server/release/knotrel-server"
  else
    printf '#!/bin/sh\n# B2 estimate, mode on: the B2 build with K = 4 (design section 5).\nKNOTREL_MAX_CONCURRENT_QUERIES=4 exec %s "$@"\n' "$REAL" > "$C/targets/cand-server/release/knotrel-server"
    chmod +x "$C/targets/cand-server/release/knotrel-server"
  fi
  ( cd "$C" && for X in cand-server/release/knotrel-server ref-server/release/knotrel-server feeder/release/knotrel-pg-feeder feeder/release/examples/load; do shasum -a 256 "targets/$X"; done ) > "$C/binaries-sha256.txt"
done
shasum -a 256 "$REAL" | sed "s#$E/##" > "$E/b2-server.sha256"
# Smoke check, not a measurement: both cand-servers start and answer /v1/info; the on wrapper
# must carry the setting (a bad value would refuse to start).
for MODE in off on; do
  PORT=$((18600 + $(printf '%s' "$MODE" | wc -c)))
  env -i KNOTREL_ADDR=127.0.0.1:$PORT "$E/$MODE/targets/cand-server/release/knotrel-server" > "$E/logs/smoke-$MODE.log" 2>&1 &
  PID=$!
  ok=0; for _ in $(seq 1 50); do curl -fsS "http://127.0.0.1:$PORT/v1/info" > "$E/logs/smoke-$MODE-info.json" 2>/dev/null && { ok=1; break; }; sleep 0.1; done
  kill $PID 2>/dev/null || true; wait $PID 2>/dev/null || true
  [ "$ok" = 1 ] || { echo "smoke $MODE failed" >&2; exit 4; }
done
env -i KNOTREL_ADDR=127.0.0.1:18699 KNOTREL_MAX_CONCURRENT_QUERIES=0 "$REAL" > "$E/logs/smoke-reject.log" 2>&1 && { echo "K=0 was not refused" >&2; exit 4; } || true
grep -q KNOTREL_MAX_CONCURRENT_QUERIES "$E/logs/smoke-reject.log" || { echo "K=0 refusal not reported" >&2; exit 4; }
echo "PREPARED $E"
