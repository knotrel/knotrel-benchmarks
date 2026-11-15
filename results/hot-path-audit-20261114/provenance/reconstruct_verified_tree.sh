#!/bin/bash
# Proves that the current knotrel working tree is the tree verified on
# 2026-11-14 (results-final run), except for documentation edited afterwards.
#
# At verification time the index held the first synchronized versions of the
# twelve changed files, and the recorded identity was
#   git diff | shasum -a 256   (index -> working tree)
#   = b17d7018523f2e0a6a40f3a4ef19d9ce9c2b29feeabf7a5027e946d1b920ea36
# This script rebuilds that exact index/working-tree pair in a throwaway clone:
# index = the recorded first-sync blobs (read from the knotrel object store),
# working tree = the current working tree, with docs/hot-path-audit-v0.3.0.md
# replaced by its verification-time copy archived beside this script.
#
# Usage: reconstruct_verified_tree.sh /path/to/knotrel
set -euo pipefail
REPO=$(cd "$1" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
EXPECTED=b17d7018523f2e0a6a40f3a4ef19d9ce9c2b29feeabf7a5027e946d1b920ea36
BASE=e1e11818a762baf07575719456a2158959b2e2c8
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone -q --no-checkout "$REPO" "$TMP/repo"
git -C "$TMP/repo" checkout -q "$BASE"
# Index blobs recorded at verification time (path blob).
while read -r blob path; do
    git -C "$REPO" cat-file -e "$blob" || { echo "missing blob $blob for $path" >&2; exit 2; }
    git -C "$REPO" cat-file blob "$blob" > "$TMP/repo/$path"
    git -C "$TMP/repo" add "$path"
done < "$HERE/verification-time-index.txt"
# Working tree: current files, plus the archived verification-time document.
while read -r _ path; do
    cp "$REPO/$path" "$TMP/repo/$path"
done < "$HERE/verification-time-index.txt"
cp "$HERE/verification-time-docs/hot-path-audit-v0.3.0.md" "$TMP/repo/docs/hot-path-audit-v0.3.0.md"
ACTUAL=$(git -C "$TMP/repo" diff | shasum -a 256 | cut -d' ' -f1)
echo "reconstructed index->worktree diff sha256: $ACTUAL"
echo "recorded at verification (results-final):   $EXPECTED"
if [ "$ACTUAL" = "$EXPECTED" ]; then echo "MATCH"; else echo "MISMATCH"; exit 1; fi
