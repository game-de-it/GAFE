# StockOS Recovery

[日本語版](RECOVERY.ja.md)

## From GAFE

1. Press SELECT to open the system menu.
2. Select `Restore StockOS` and press A.
3. Select `Yes` and press A.

GAFE saves its current settings, restores the original StockOS launcher and RetroArch settings, and reboots automatically.

## Over SSH

```sh
ssh root@DEVICE_IP
/mnt/mmc/Roms/PORTS/GAFE-OFF.sh
```

## Manual Recovery

The device-specific launcher backup is stored at:

```text
/mnt/mmc/GAFE_HOME/backups/launcher.stock.sh
```

From an environment that can access the root filesystem, restore this file to `/etc/init.d/launcher.sh` with executable permissions. Remove `/etc/gafe-mode` and `/etc/rafe-mode`, then reboot. Never substitute a launcher from a different device or StockOS release.

The pre-install RetroArch shader and GBA core settings are stored under:

```text
/mnt/mmc/GAFE_HOME/backups/retroarch-config
```

GAFE-specific settings remain under `/mnt/mmc/GAFE_HOME/settings` and are reapplied the next time GAFE-ON runs.

If GAFE startup validation fails, the session attempts to run GAFE-OFF automatically and return to StockOS.
