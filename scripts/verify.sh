#!/bin/bash
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 -c 'import ast, pathlib, sys; ast.parse(pathlib.Path(sys.argv[1]).read_text())' \
    "$ROOT/ports/GAFE/gafe_frontend.py"
bash -n \
    "$ROOT/ports/GAFE-ON.sh" \
    "$ROOT/ports/GAFE-OFF.sh" \
    "$ROOT/ports/GAFE/launch.sh" \
    "$ROOT/ports/GAFE/gafe-session.sh"
sh -n "$ROOT/ports/GAFE/launcher-wrapper.sh"

for required in \
    GAFE-ON.sh GAFE-OFF.sh \
    GAFE/gafe_frontend.py GAFE/launch.sh GAFE/gafe-session.sh \
    GAFE/launcher-wrapper.sh GAFE/retroarch.cfg GAFE/gba-game.cfg GAFE/VERSION \
    GAFE/assets/xmb-wallpaper.png GAFE/config/global.glslp \
    GAFE/config/mGBA/GBA.opt; do
    [ -f "$ROOT/ports/$required" ] || { echo "Missing: $required" >&2; exit 1; }
done

echo "GAFE source verification passed"
