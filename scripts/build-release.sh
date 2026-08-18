#!/bin/bash
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(tr -d '\r\n' <"$ROOT/ports/GAFE/VERSION")
DIST="$ROOT/dist"
ARCHIVE="$DIST/GAFE-v$VERSION.zip"

"$ROOT/scripts/verify.sh"
mkdir -p "$DIST"
rm -f "$ARCHIVE" "$DIST/SHA256SUMS"
(
    cd "$ROOT/ports"
    zip -q -r -X "$ARCHIVE" GAFE-ON.sh GAFE-OFF.sh GAFE \
        -x '*/__pycache__/*' '*.pyc' '.DS_Store'
)
(
    cd "$DIST"
    shasum -a 256 "$(basename "$ARCHIVE")" >SHA256SUMS
)
echo "Created $ARCHIVE"
