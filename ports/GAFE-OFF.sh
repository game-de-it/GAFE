#!/bin/bash
set -eu

GAFE_HOME=/mnt/mmc/GAFE_HOME
BACKUP="$GAFE_HOME/backups/launcher.stock.sh"
FALLBACK=/etc/init.d/launcher.gafe-stock.sh
LOG_DIR="$GAFE_HOME/logs"
LOG_FILE="$LOG_DIR/gafe-off.log"
RETRO_CONFIG_DIR=/mnt/vendor/deep/retro/config
CONFIG_BACKUP_DIR="$GAFE_HOME/backups/retroarch-config"
SETTINGS_DIR="$GAFE_HOME/settings"

restore_config() {
    target=$1
    name=$2
    captured="$CONFIG_BACKUP_DIR/$name.captured"
    present="$CONFIG_BACKUP_DIR/$name.present"
    backup="$CONFIG_BACKUP_DIR/$name"
    [ -e "$captured" ] || return
    if [ -e "$present" ]; then
        [ -f "$backup" ] || {
            echo "RetroArch backup is missing: $backup"
            exit 1
        }
        install -m 0644 "$backup" "$target"
    else
        rm -f "$target"
    fi
}

capture_gafe_setting() {
    target=$1
    saved=$2
    absent=$3
    mkdir -p "$(dirname "$saved")"
    if [ -f "$target" ]; then
        cp "$target" "$saved"
        rm -f "$absent"
    else
        rm -f "$saved"
        : >"$absent"
    fi
}

mkdir -p "$LOG_DIR"
exec >>"$LOG_FILE" 2>&1
printf '\n%s StockOS restoration started\n' "$(date '+%Y-%m-%d %H:%M:%S')"

[ "$(id -u)" -eq 0 ] || { echo "GAFE-OFF.sh must run as root"; exit 1; }

if [ -s "$BACKUP" ]; then
    source_launcher=$BACKUP
elif [ -s "$FALLBACK" ]; then
    source_launcher=$FALLBACK
else
    echo "StockOS launcher backup was not found; restoration stopped"
    exit 1
fi

mkdir -p "$RETRO_CONFIG_DIR/mGBA"
if [ -f /etc/gafe-mode ]; then
    capture_gafe_setting "$RETRO_CONFIG_DIR/global.glslp" \
        "$SETTINGS_DIR/global.glslp" "$SETTINGS_DIR/global.glslp.absent"
    capture_gafe_setting "$RETRO_CONFIG_DIR/mGBA/GBA.opt" \
        "$SETTINGS_DIR/mGBA/GBA.opt" "$SETTINGS_DIR/mGBA/GBA.opt.absent"
fi
restore_config "$RETRO_CONFIG_DIR/global.glslp" global.glslp
restore_config "$RETRO_CONFIG_DIR/mGBA/GBA.opt" GBA.opt
install -m 0755 "$source_launcher" /etc/init.d/launcher.sh
rm -f /etc/gafe-mode /etc/rafe-mode
sync
echo "StockOS launcher and RetroArch settings restored; rebooting"
systemctl reboot
