#!/bin/bash
set -u

GAFE_MARKER=/etc/gafe-mode
GAFE_DIR=/mnt/mmc/Roms/PORTS/GAFE
GAFE_HOME=/mnt/mmc/GAFE_HOME
STOCK_LAUNCHER=/etc/init.d/launcher.gafe-stock.sh
ACTION_FILE="$GAFE_HOME/session-action"
SETTINGS_DIR="$GAFE_HOME/settings"
RETRO_CONFIG_DIR=/mnt/vendor/deep/retro/config

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

restore_stock() {
    log "GAFE startup failed; restoring StockOS launcher"
    if [ -x /mnt/mmc/Roms/PORTS/GAFE-OFF.sh ]; then
        exec /mnt/mmc/Roms/PORTS/GAFE-OFF.sh --startup-failure
    fi
    rm -f "$GAFE_MARKER" /etc/rafe-mode
    if [ -s "$STOCK_LAUNCHER" ]; then
        install -m 0755 "$STOCK_LAUNCHER" /etc/init.d/launcher.sh
    fi
    sync
    systemctl reboot
    exit 1
}

apply_gafe_setting() {
    saved=$1
    absent=$2
    target=$3

    if [ -e "$absent" ]; then
        rm -f "$target"
        log "Applied saved absence: $target"
    elif [ -f "$saved" ]; then
        install -m 0644 "$saved" "$target"
        log "Applied saved GAFE setting: $target"
    else
        log "Saved GAFE setting is missing: $saved"
        restore_stock
    fi
}

set_cpu_governor() {
    policies=0

    for governor_path in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
        [ -e "$governor_path" ] || continue
        policies=$((policies + 1))
        policy_dir=${governor_path%/*}
        available="$policy_dir/scaling_available_governors"

        if [ -r "$available" ] && ! grep -qw ondemand "$available"; then
            log "Warning: ondemand is unavailable for $policy_dir"
            continue
        fi
        if printf '%s\n' ondemand >"$governor_path"; then
            log "CPU governor set to ondemand for $policy_dir"
        else
            log "Warning: could not set CPU governor for $policy_dir"
        fi
    done

    [ "$policies" -gt 0 ] || log "Warning: no CPU frequency policy was found"
}

mkdir -p /mnt/vendor /mnt/mmc /mnt/data /mnt/sdcard
mountpoint -q /mnt/vendor || \
    mount -t ext4 -o rw,noatime,nodiratime /dev/mmcblk0p6 /mnt/vendor || restore_stock
mountpoint -q /mnt/mmc || \
    mount -t vfat -o rw,utf8,uid=1000,gid=1000,dmask=000,fmask=000,noatime,nodiratime \
        /dev/mmcblk0p1 /mnt/mmc || restore_stock
if [ -b /dev/mmcblk0p7 ] && ! mountpoint -q /mnt/data; then
    mount -t ext4 -o rw,noatime,nodiratime /dev/mmcblk0p7 /mnt/data || \
        log "Warning: UDISK could not be mounted"
fi
mkdir -p "$GAFE_HOME/logs" "$GAFE_HOME/config"
if [ -x /mnt/vendor/ctrl/mmc_new.sh ]; then
    /mnt/vendor/ctrl/mmc_new.sh add
fi
mountpoint -q /mnt/sdcard || mount --bind /mnt/mmc /mnt/sdcard || restore_stock
set_cpu_governor

# StockOS boot helpers may reset RetroArch's active configuration after
# GAFE-ON runs. Reapply GAFE-owned settings after those helpers finish.
mkdir -p "$RETRO_CONFIG_DIR/mGBA"
apply_gafe_setting "$SETTINGS_DIR/global.glslp" \
    "$SETTINGS_DIR/global.glslp.absent" "$RETRO_CONFIG_DIR/global.glslp"
apply_gafe_setting "$SETTINGS_DIR/mGBA/GBA.opt" \
    "$SETTINGS_DIR/mGBA/GBA.opt.absent" "$RETRO_CONFIG_DIR/mGBA/GBA.opt"

for required in \
    "$GAFE_DIR/launch.sh" \
    "$GAFE_DIR/gafe_frontend.py" \
    "$GAFE_HOME/settings/retroarch.cfg" \
    /mnt/vendor/deep/retro/retroarch \
    /mnt/vendor/deep/retro/cores/mgba_libretro.so; do
    [ -e "$required" ] || restore_stock
done

export HOME="$GAFE_HOME"
export XDG_CONFIG_HOME="$GAFE_HOME/config"
export XDG_RUNTIME_DIR=/run/user/0
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus
export LD_LIBRARY_PATH=/usr/lib32:/usr/lib:/mnt/vendor/lib
export SDL_VIDEODRIVER=mali
export SDL_AUDIODRIVER=alsa

log "Starting GAFE"
rm -f "$ACTION_FILE"
"$GAFE_DIR/launch.sh"
status=$?
log "GAFE exited with status $status"

action=
if [ -f "$ACTION_FILE" ]; then
    action=$(head -n 1 "$ACTION_FILE")
    rm -f "$ACTION_FILE"
fi

case "$action" in
    restore-stock)
        log "StockOS restoration requested from GAFE"
        if [ -x /mnt/mmc/Roms/PORTS/GAFE-OFF.sh ]; then
            exec /mnt/mmc/Roms/PORTS/GAFE-OFF.sh --from-fe
        fi
        restore_stock
        ;;
    reboot)
        log "Restart requested from GAFE"
        sync
        systemctl reboot
        exit 0
        ;;
    poweroff)
        log "Shutdown requested from GAFE"
        sync
        systemctl poweroff
        exit 0
        ;;
esac

if [ "$status" -ne 0 ] && [ -f "$GAFE_MARKER" ]; then
    restore_stock
fi

# A normal frontend exit is treated as a power-off request. GAFE-OFF removes
# the marker before rebooting, so it never reaches this branch.
if [ -f "$GAFE_MARKER" ]; then
    sync
    systemctl poweroff
fi
