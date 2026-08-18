#!/bin/bash
set -eu

PORTS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
GAFE_DIR="$PORTS_DIR/GAFE"
GAFE_HOME=/mnt/mmc/GAFE_HOME
BACKUP_DIR="$GAFE_HOME/backups"
LOG_DIR="$GAFE_HOME/logs"
STOCK_BACKUP="$BACKUP_DIR/launcher.stock.sh"
INSTALLED_STOCK=/etc/init.d/launcher.gafe-stock.sh
LOG_FILE="$LOG_DIR/gafe-on.log"
RETRO_CONFIG_DIR=/mnt/vendor/deep/retro/config
CONFIG_BACKUP_DIR="$BACKUP_DIR/retroarch-config"

backup_config() {
    target=$1
    name=$2
    captured="$CONFIG_BACKUP_DIR/$name.captured"
    present="$CONFIG_BACKUP_DIR/$name.present"
    backup="$CONFIG_BACKUP_DIR/$name"
    [ -e "$captured" ] && return
    if [ -f "$target" ]; then
        cp "$target" "$backup"
        : >"$present"
    fi
    : >"$captured"
}

mkdir -p "$BACKUP_DIR" "$LOG_DIR"
exec >>"$LOG_FILE" 2>&1
printf '\n%s GAFE installation started\n' "$(date '+%Y-%m-%d %H:%M:%S')"

[ "$(id -u)" -eq 0 ] || { echo "GAFE-ON.sh must run as root"; exit 1; }

for required in \
    "$GAFE_DIR/gafe_frontend.py" \
    "$GAFE_DIR/launch.sh" \
    "$GAFE_DIR/gafe-session.sh" \
    "$GAFE_DIR/launcher-wrapper.sh" \
    "$GAFE_DIR/retroarch.cfg" \
    "$GAFE_DIR/gba-game.cfg" \
    "$GAFE_DIR/config/global.glslp" \
    "$GAFE_DIR/config/mGBA/GBA.opt" \
    /usr/bin/python3 \
    /mnt/vendor/deep/retro/retroarch \
    /mnt/vendor/deep/retro/cores/mgba_libretro.so; do
    [ -e "$required" ] || { echo "Required file missing: $required"; exit 1; }
done

/usr/bin/python3 -c 'import sdl2; from PIL import Image' || {
    echo "Required Python modules are unavailable: PySDL2 and Pillow"
    exit 1
}

mkdir -p "$CONFIG_BACKUP_DIR" "$RETRO_CONFIG_DIR/mGBA"
backup_config "$RETRO_CONFIG_DIR/global.glslp" global.glslp
backup_config "$RETRO_CONFIG_DIR/mGBA/GBA.opt" GBA.opt

if [ ! -s "$STOCK_BACKUP" ]; then
    source_launcher=
    if [ -s "$INSTALLED_STOCK" ]; then
        source_launcher=$INSTALLED_STOCK
    elif [ -s /etc/init.d/launcher.stock.sh ]; then
        source_launcher=/etc/init.d/launcher.stock.sh
    elif [ -s /etc/init.d/launcher.sh ] && ! grep -q 'GAFE_SESSION=' /etc/init.d/launcher.sh; then
        source_launcher=/etc/init.d/launcher.sh
    fi
    [ -n "$source_launcher" ] || {
        echo "Could not identify the original StockOS launcher; installation stopped"
        exit 1
    }
    install -m 0755 "$source_launcher" "$STOCK_BACKUP"
fi

install -m 0755 "$STOCK_BACKUP" "$INSTALLED_STOCK"
install -m 0755 "$GAFE_DIR/launcher-wrapper.sh" /etc/init.d/launcher.sh
install -m 0755 "$GAFE_DIR/gafe-session.sh" /usr/local/sbin/gafe-session.sh
install -m 0644 "$GAFE_DIR/config/global.glslp" "$RETRO_CONFIG_DIR/global.glslp"
install -m 0644 "$GAFE_DIR/config/mGBA/GBA.opt" "$RETRO_CONFIG_DIR/mGBA/GBA.opt"
chmod 0755 "$PORTS_DIR/GAFE-ON.sh" "$PORTS_DIR/GAFE-OFF.sh" "$GAFE_DIR/launch.sh"

if [ ! -e "$GAFE_HOME/state.json" ] && [ -e /mnt/mmc/RAFE_HOME/gba-frontend/state.json ]; then
    cp -p /mnt/mmc/RAFE_HOME/gba-frontend/state.json "$GAFE_HOME/state.json"
fi
if [ ! -e "$GAFE_HOME/volume.json" ] && [ -e /mnt/mmc/RAFE_HOME/gba-frontend/volume.json ]; then
    cp -p /mnt/mmc/RAFE_HOME/gba-frontend/volume.json "$GAFE_HOME/volume.json"
fi

sha256sum "$STOCK_BACKUP" >"$BACKUP_DIR/launcher.stock.sha256"
: >/etc/gafe-mode
rm -f /etc/rafe-mode
sync
echo "GAFE installation completed; rebooting"
systemctl reboot
