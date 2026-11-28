#!/bin/sh
# p2run.sh VARIANT LOAD REP
B=$(dirname "$0"); V=$1; L=$2; I=$3; SRV=$B/server-$V
PROBE=/Users/rt/workspace/knotrel/evidence/v1.2.0-qualification-attempt2-977e54d-99f820c/targets/contention/release/contention-probe
case $L in
  R) MODE=standalone; LC=false; CFG='{"id":"R","mix":"read95","batch":8,"clients":16,"warmup_ms":3000,"measure_ms":20000,"open_rate":null,"background":"none"}' ;;
  F) MODE=source-managed; LC=true; CFG='{"id":"F","mix":"read100","batch":8,"clients":16,"warmup_ms":3000,"measure_ms":20000,"open_rate":null,"background":"events"}' ;;
  W) MODE=standalone; LC=false; CFG='{"id":"W","mix":"mixed50","batch":64,"clients":16,"warmup_ms":3000,"measure_ms":20000,"open_rate":null,"background":"none"}' ;;
esac
echo "$CFG" > $B/cfg-$L.json
OUT=$B/p2-$L-$V-$I
$PROBE --server-bin $SRV --mode $MODE --lifecycle $LC --nodes 100000 --seed 182 --configs $B/cfg-$L.json --port 19$(( $$ % 900 + 100 )) > $OUT.json 2> $OUT.err &
PR=$!
: > $OUT.rss
while kill -0 $PR 2>/dev/null; do P=$(pgrep -nf "^$SRV") && ps -o rss= -p $P >> $OUT.rss; sleep 0.1; done
wait $PR
