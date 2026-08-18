#!/bin/bash
set -u

APP_DIR=/mnt/mmc/Roms/PORTS/GAFE
HOME_DIR=/mnt/mmc/GAFE_HOME
LOG_DIR="$HOME_DIR/logs"

mkdir -p "$LOG_DIR"
export HOME="$HOME_DIR"
export XDG_CONFIG_HOME="$HOME_DIR/config"
export SDL_VIDEODRIVER=mali
export SDL_AUDIODRIVER=alsa
cd "$APP_DIR" || exit 1
exec /usr/bin/python3 "$APP_DIR/gafe_frontend.py" >>"$LOG_DIR/frontend.log" 2>&1
