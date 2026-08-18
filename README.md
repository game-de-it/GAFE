# GAFE

GAFE (Game Boy Advance Front End) は、ANBERNIC RGSPのStockOSをGBA専用機として使うためのフロントエンドです。mGBA版RetroArchを起動し、カートリッジ型カルーセル、Boxart、日本語表示、Wi-Fi設定、ゲーム中も有効な本体音量調整を提供します。

## 対象

- ANBERNIC RGSP StockOS
- StockOS同梱のRetroArchと`mgba_libretro.so`
- `/usr/bin/python3`、PySDL2、Pillowが利用できる環境

RetroArch本体、mGBAコア、ROM、BIOSは同梱しません。

## インストール

1. リリースZIPを展開します。
2. `GAFE-ON.sh`、`GAFE-OFF.sh`、`GAFE`フォルダをSDカードの`Roms/PORTS`直下へ配置します。
3. StockOSのPORTSから`GAFE-ON.sh`を実行します。
4. 自動再起動後、GAFEが起動します。

初回導入時、端末固有のStockOSランチャーを`/mnt/mmc/GAFE_HOME/backups/launcher.stock.sh`へ退避します。このバックアップは再インストールや更新では上書きしません。

## 操作

- 十字キー左右: ゲーム選択
- A: ゲーム起動、決定
- B: 戻る
- START: Wi-Fi画面
- SELECT: システム画面
- 本体音量ボタン: OS側音量の変更と保存

## StockOSへ戻す

GAFEのメイン画面でSELECTを押し、`StockOSへ戻す`を選びます。確認画面で`はい`を選ぶと、退避済みランチャーを復元して再起動します。

GAFEを起動できない場合は、SSHから次を実行できます。

```sh
/mnt/mmc/Roms/PORTS/GAFE-OFF.sh
```

復旧後もROM、セーブ、Wi-Fi設定、GAFE本体と設定データは削除されません。再度有効にする場合はPORTSから`GAFE-ON.sh`を実行します。

より詳しい復旧手順は[docs/RECOVERY.md](docs/RECOVERY.md)を参照してください。

## 設定とデータ

- 配布RetroArch設定: `Roms/PORTS/GAFE/retroarch.cfg`
- ゲーム用追加設定: `Roms/PORTS/GAFE/gba-game.cfg`
- 選択位置、音量、ログ、StockOSバックアップ: `/mnt/mmc/GAFE_HOME`
- GBA ROM: `/mnt/mmc/Roms/GBA`

`retroarch.cfg`は開発機で動作確認した現在の設定を収録しています。

## リリース作成

macOSまたはLinuxで次を実行します。

```sh
./scripts/verify.sh
./scripts/build-release.sh
```

`dist`にZIPとSHA-256チェックサムが生成されます。
