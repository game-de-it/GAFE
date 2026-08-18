#!/bin/bash
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(tr -d '\r\n' <"$ROOT/ports/GAFE/VERSION")
ARCHIVE="$ROOT/dist/GAFE-v$VERSION.zip"
NOTES="$ROOT/docs/releases/v$VERSION.md"

"$ROOT/scripts/verify.sh"
git -C "$ROOT" diff --check

[ -f "$NOTES" ] || { echo "Missing release notes: $NOTES" >&2; exit 1; }
[ -z "$(git -C "$ROOT" status --porcelain)" ] || {
    echo "Git worktree is not clean" >&2
    exit 1
}

"$ROOT/scripts/build-release.sh"
unzip -t "$ARCHIVE" >/dev/null

(
    cd "$ROOT/dist"
    shasum -a 256 -c SHA256SUMS
)

checksum=$(cut -d ' ' -f 1 "$ROOT/dist/SHA256SUMS")
grep -q "$checksum" "$NOTES" || {
    echo "Release notes do not contain the current archive checksum" >&2
    exit 1
}

echo "GAFE v$VERSION is ready for GitHub Release"
