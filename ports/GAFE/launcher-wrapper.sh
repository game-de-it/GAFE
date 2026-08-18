#!/bin/sh

STOCK_LAUNCHER=/etc/init.d/launcher.gafe-stock.sh
GAFE_SESSION=/usr/local/sbin/gafe-session.sh
GAFE_MARKER=/etc/gafe-mode
GAFE_LOG=/var/log/gafe-session.log

start_gafe() {
    if [ ! -x "$GAFE_SESSION" ]; then
        rm -f "$GAFE_MARKER"
        exec "$STOCK_LAUNCHER" start
    fi
    "$GAFE_SESSION" >>"$GAFE_LOG" 2>&1 &
}

case "${1:-start}" in
    start)
        if [ -f "$GAFE_MARKER" ]; then
            start_gafe
        else
            exec "$STOCK_LAUNCHER" start
        fi
        ;;
    stop)
        if [ -f "$GAFE_MARKER" ]; then
            pkill -f '/mnt/mmc/Roms/PORTS/GAFE/gafe_frontend.py' 2>/dev/null || true
            pkill -f '/mnt/vendor/deep/retro/retroarch' 2>/dev/null || true
        else
            exec "$STOCK_LAUNCHER" stop
        fi
        ;;
    restart)
        "$0" stop
        sleep 1
        "$0" start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}" >&2
        exit 2
        ;;
esac
