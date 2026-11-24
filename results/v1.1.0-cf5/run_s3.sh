#!/bin/sh
# CF5 block S3 collector (knotrel docs/releases/v1.1.0-cf5-qualification-plan.md, sections 4.3
# and 8): PostgreSQL exists only while S3 runs, as in v1.0.0 block Q (run_part3.sh).
#
# Usage: run_s3.sh CAMP RUN_DIR      (the delegated collector; RUN_DIR is run_cf5.py's {run})
#        run_s3.sh CAMP --prepare    (prepare_cf5.sh: prerequisites and the pinned image)
#
# Collector: checks AC power and the binaries against CAMP/binaries-sha256.txt; starts Docker
# Desktop if it is not running and waits for its daemon; starts the pinned PostgreSQL 18
# container (candidate checkout's start-test-postgres.sh); requires a postgres:// URL,
# pg_isready and SELECT 1; runs run_cf5_s3.py with the URL in its environment only (never
# written), then evaluates. On exit, whatever happened: the container is removed and, if this
# script started Docker Desktop, Docker Desktop is quit and its virtual machine must be gone
# within 120 s. Every step is logged in RUN_DIR/s3-lifecycle.log (no URL, no password).
# Exit status: run_cf5_s3.py's (0 COMPLETE, 1 NONCONFORMING by its cap: the matrix's
# incomplete_exit); 4 for an infrastructure failure (Docker or PostgreSQL not available), which
# run_cf5.py reruns once; 3 for a refused precondition.
#
# --prepare: checks the docker CLI, Docker.app and the scripts, starts Docker Desktop if needed,
# makes sure the pinned image is present (pulls it by digest if not), records its digest in
# CAMP/logs/S3-image.txt, then checks the container cycle (start, pg_isready, SELECT 1,
# removal) and restores Docker Desktop's previous state. No measurement.
set -eu
CAMP=${1%/}
MODE=${2:?usage: run_s3.sh CAMP RUN_DIR|--prepare}
K=$CAMP/src/cand/knotrel
B=$CAMP/src/cand/knotrel-benchmarks
F=$K/integrations/postgres-feeder
T=$CAMP/targets
PGNAME=knotrel-pg-test-18
for D in /usr/local/bin /opt/homebrew/bin /Applications/Docker.app/Contents/Resources/bin "$HOME/.docker/bin"; do
  case ":$PATH:" in *":$D:"*) ;; *) [ -d "$D" ] && PATH="$PATH:$D" ;; esac
done
export PATH
IMAGE=$(grep -o 'postgres:18[^"]*' "$F/scripts/start-test-postgres.sh" | head -1)
[ -n "$IMAGE" ] || { echo "no pinned PostgreSQL 18 image in start-test-postgres.sh" >&2; exit 3; }

if [ "$MODE" = "--prepare" ]; then
  LOG=$CAMP/logs/S3-prepare.log
else
  RUN=${MODE%/}
  mkdir -p "$RUN"
  LOG=$RUN/s3-lifecycle.log
fi
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG"; }
vm_running() { pgrep -f 'com.docker.backend|com.docker.virtualization|com.docker.krun|vfkit|krunkit|Docker Desktop.app/Contents/MacOS/Docker Desktop' > /dev/null 2>&1; }

STARTED_DOCKER=0
PG_STARTED=0
cleanup() {
  if [ "$PG_STARTED" = 1 ]; then
    bash "$F/scripts/stop-test-postgres.sh" 18 > /dev/null 2>&1 || true
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$PGNAME"; then
      log "container $PGNAME still present after stop"
    else
      log "container $PGNAME removed"
    fi
  fi
  if [ "$STARTED_DOCKER" = 1 ]; then
    # Docker Desktop's CLI quits the app and its virtual machine (osascript quit does not).
    docker desktop stop > /dev/null 2>&1 || osascript -e 'quit app "Docker"' > /dev/null 2>&1 || true
    for _ in $(seq 1 120); do vm_running || break; sleep 1; done
    if vm_running; then log "Docker Desktop virtual machine still running 120 s after quit"
    else log "Docker Desktop quit, virtual machine gone"; fi
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM

command -v docker > /dev/null || { log "docker CLI not found"; echo "docker CLI not found" >&2; exit 3; }
[ -d /Applications/Docker.app ] || { log "Docker.app not found"; echo "Docker.app not found" >&2; exit 3; }
for X in start-test-postgres.sh stop-test-postgres.sh; do
  [ -f "$F/scripts/$X" ] || { log "missing $X"; echo "missing $F/scripts/$X" >&2; exit 3; }
done

if docker info > /dev/null 2>&1; then
  log "Docker daemon already running (left running afterwards)"
else
  log "starting Docker Desktop"
  STARTED_DOCKER=1
  docker desktop start > /dev/null 2>&1 || open -a Docker
  for _ in $(seq 1 180); do docker info > /dev/null 2>&1 && break; sleep 1; done
  if ! docker info > /dev/null 2>&1; then
    log "infrastructure: Docker daemon not available 180 s after start"
    echo "infrastructure failure: Docker daemon not available" >&2
    exit 4
  fi
  log "Docker daemon available"
fi

if [ "$MODE" = "--prepare" ]; then
  if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
    log "pulling $IMAGE"
    docker pull "$IMAGE" > /dev/null 2>&1 || { log "pull failed"; echo "could not pull $IMAGE" >&2; exit 3; }
  fi
  ID=$(docker image inspect --format '{{.Id}}' "$IMAGE")
  echo "$IMAGE $ID" > "$CAMP/logs/S3-image.txt"
  log "image present: $IMAGE $ID"
fi

if [ "$MODE" != "--prepare" ]; then
pmset -g batt | head -1 | grep -q "AC Power" || { log "not on AC power"; echo "not on AC power" >&2; exit 3; }
for X in cand-server/release/knotrel-server feeder/release/knotrel-pg-feeder feeder/release/examples/load; do
  grep -q "$(shasum -a 256 "$T/$X" | cut -d' ' -f1)  targets/$X\$" "$CAMP/binaries-sha256.txt" \
    || { log "binary changed: $X"; echo "binary changed: $X" >&2; exit 3; }
done
docker image inspect "$IMAGE" > /dev/null 2>&1 || log "image not cached: start-test-postgres.sh will pull it"
fi

if [ "$MODE" = "--prepare" ]; then PGERR=$CAMP/logs/S3-prepare-postgres.stderr; else PGERR=$RUN/postgres-start.stderr; fi
PG_STARTED=1
PGRC=0
PGOUT=$(bash "$F/scripts/start-test-postgres.sh" 18 2> "$PGERR") || PGRC=$?
URL=$(printf '%s\n' "$PGOUT" | tail -1)
WHY=""
if [ "$PGRC" -ne 0 ]; then WHY="start-test-postgres.sh exited $PGRC"
else
  case "$URL" in postgres://*) ;; *) WHY="start-test-postgres.sh printed no postgres:// URL" ;; esac
fi
[ -n "$WHY" ] || docker exec "$PGNAME" pg_isready -U postgres -h 127.0.0.1 > /dev/null 2>&1 || WHY="pg_isready failed"
[ -n "$WHY" ] || [ "$(docker exec "$PGNAME" psql -U postgres -h 127.0.0.1 -qAt -c 'SELECT 1' 2>/dev/null)" = 1 ] \
  || WHY="SELECT 1 failed"
if [ -n "$WHY" ]; then
  log "infrastructure: PostgreSQL not available ($WHY)"
  docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}' 2>&1 | head -10 >> "$LOG" || true
  echo "infrastructure failure: PostgreSQL not available ($WHY)" >&2
  exit 4
fi
log "PostgreSQL ready: $IMAGE $(docker image inspect --format '{{.Id}}' "$IMAGE" 2>/dev/null)"
if [ "$MODE" = "--prepare" ]; then
  URL=""
  echo "S3 PREPARE OK"
  exit 0
fi

RC=0
( cd "$B" && LIFECYCLE_QUALIFICATION_ROOTS="$CAMP" KNOTREL_PG_ADMIN_URL="$URL" \
    python3 scripts/run_cf5_s3.py run "$CAMP" "$RUN/S3" ) || RC=$?
URL=""
log "run_cf5_s3.py exit $RC"
( cd "$B" && LIFECYCLE_QUALIFICATION_ROOTS="$CAMP" \
    python3 scripts/run_cf5_s3.py evaluate "$RUN/S3" --out "$RUN/S3-evaluation.json" ) \
  || log "evaluation failed (the run is kept; evaluate again afterwards)"
exit "$RC"
