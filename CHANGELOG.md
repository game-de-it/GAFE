# Changelog

All notable changes to GAFE are documented in this file.

## [0.1.2] - 2026-08-19

### Added

- Added persistent `Balanced`, `Battery Saver`, and `Performance` CPU modes to the SELECT menu.
- Use the latency-sensitive `interactive` governor as the default balanced mode.
- Persist screen brightness changes and reapply them after display initialization.
- Documented the update path that preserves existing GAFE state and StockOS backups.

## [0.1.1] - 2026-08-18

### Fixed

- Reapplied the saved global shader and mGBA settings after StockOS runtime initialization.

## [0.1.0] - 2026-08-18

### Added

- GBA cartridge carousel with animated navigation and fitted RetroArch Boxart.
- Japanese game-title rendering with font fallback support.
- Wi-Fi scanning, password entry, connection status, and radio control.
- Persistent hardware volume control during both GAFE and RetroArch gameplay.
- StockOS brightness shortcuts without unintended volume changes.
- System menu actions for StockOS restoration, restart, and shutdown.
- StockOS launcher backup and automatic recovery on GAFE startup failure.
- Separate persistent GAFE RetroArch, shader, and mGBA content-directory settings.
- Packaged XMB configuration and attributed wallpaper.
- English and Japanese installation, operation, Boxart, and recovery documentation.

### Compatibility

- ANBERNIC RGSP StockOS v1.0.1.
- Uses the RetroArch and mGBA core included with StockOS.
