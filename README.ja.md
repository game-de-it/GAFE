# GAFE

[English](README.md)

GAFE（Game Boy Advance Front End）は、StockOSで動作するANBERNIC RGSPをGBA専用機として使うためのフロントエンドです。StockOS付属のRetroArchとmGBAコアを起動し、カートリッジ型カルーセル、Boxart、Wi-Fi設定、本体音量の永続化、システム操作を提供します。

## 必要環境

- ANBERNIC RGSP StockOS v1.0.1
- StockOS付属のRetroArchと`mgba_libretro.so`
- PySDL2とPillowを利用できるStockOSのPython 3
- `/mnt/mmc/Roms/GBA`に配置したGBA ROM

RetroArch本体、mGBAコア、ROM、BIOSは同梱しません。

## 導入方法

1. GAFEのリリースZIPをダウンロードして展開します。
2. `GAFE-ON.sh`、`GAFE-OFF.sh`、`GAFE`フォルダをSDカードの`Roms/PORTS`直下へコピーします。
3. 実機で`RA game` -> `PORTS` -> `GAFE-ON`の順に選択します。
4. 自動的に再起動し、GAFEが表示されます。

配置後は次の構成になります。

```text
Roms/PORTS/GAFE-ON.sh
Roms/PORTS/GAFE-OFF.sh
Roms/PORTS/GAFE/
```

## 操作方法

| 操作 | 機能 |
|---|---|
| 十字キー左右 | ゲーム選択 |
| A | ゲーム起動、決定 |
| B | 戻る |
| START | Wi-Fi設定 |
| SELECT | システムメニュー |
| 本体音量ボタン | OS側音量の変更と保存 |

システムメニューには`Restore StockOS`、`Restart`、`Shut Down`があります。重要な操作では確認画面が開き、初期選択は`No`です。

## Boxartの取得

GAFEはRetroArchのGBAプレイリストとダウンロード済みサムネイルを利用します。事前に実機をWi-Fiへ接続してください。

### 1. プレイリストの作成

1. ゲームを開始します。
2. RetroArchメニューを表示します。
3. `Import Contents` -> `Scan Directory` -> `Parent Directory` -> `GBA` -> `Scan This Directory`の順に選択します。

### 2. プレイリスト画像のスクレイピング

1. RetroArchの`Main Menu`を開きます。
2. `Online Updater` -> `Playlist Thumbnails Updater`を選択します。
3. `Nintendo - Game Boy / Advance`を選択します。

ダウンロード完了後にGAFEへ戻ると、取得済みBoxartがクロップされずカートリッジのラベル領域へ表示されます。

## GAFE-ONで適用される内容

GAFE-ONは次の処理を行います。

- 端末固有のStockOSランチャーを初回のみバックアップします。
- GAFE用のランチャーラッパーとセッションスクリプトをインストールします。
- `/etc/gafe-mode`を作成してGAFEモードを有効にします。
- `/mnt/mmc/GAFE_HOME`へ永続データ領域を作成します。
- 同梱`retroarch.cfg`からGAFE専用の永続設定を初期作成します。
- 既存のグローバルシェーダー設定をバックアップし、同梱設定を適用します。
- 既存のGBAディレクトリ用mGBA設定をバックアップし、同梱設定を適用します。
- ゲーム選択位置、音量、ログ、GAFE専用RetroArch設定を再起動やモード変更後も維持します。

元のランチャーとRetroArch設定は`/mnt/mmc/GAFE_HOME/backups`へ保存されます。以後GAFE-ONを実行しても、既存バックアップは上書きしません。

## GAFE設定の永続化

GAFE使用中に変更した設定は次の場所へ保存されます。

```text
/mnt/mmc/GAFE_HOME/settings
```

対象は使用中の`retroarch.cfg`、グローバルシェーダー、GBAディレクトリ用mGBA設定です。GAFE-OFFはStockOS設定を復元する前に現在のGAFE設定を保存します。次回GAFE-ONでは配布物の初期値ではなく、保存済みのGAFE設定を再適用します。

## StockOSへ戻す

SELECTでシステムメニューを開き、`Restore StockOS`を選択して`Yes`で確定します。復元後、端末は自動的に再起動します。

GAFE-OFFで元に戻る内容：

- 元のStockOSランチャー
- 初回GAFE-ON前のグローバルシェーダー設定
- 初回GAFE-ON前のGBAディレクトリ用mGBA設定
- 通常のStockOS起動動作

GAFE-OFFで削除されない内容：

- ROM、BIOS、セーブ、ステートセーブ
- Wi-Fi接続情報
- `Roms/PORTS`内のGAFE本体
- `/mnt/mmc/GAFE_HOME`内のGAFE永続設定

再度GAFEを有効にする場合は、StockOSから`RA game` -> `PORTS` -> `GAFE-ON`を実行します。

FEを起動できない場合は、SSHから次を実行します。

```sh
/mnt/mmc/Roms/PORTS/GAFE-OFF.sh
```

詳しい復旧方法は[復旧手順](docs/RECOVERY.ja.md)を参照してください。

## 同梱設定

| ファイル | 用途 |
|---|---|
| `GAFE/retroarch.cfg` | GAFE用RetroArch初期設定 |
| `GAFE/gba-game.cfg` | 起動時の音量入力上書き設定 |
| `GAFE/config/global.glslp` | グローバルシェーダー初期設定 |
| `GAFE/config/mGBA/GBA.opt` | GBAディレクトリ用mGBA初期設定 |
| `GAFE/assets/xmb-wallpaper.png` | XMB壁紙 |

## 壁紙のクレジット

同梱壁紙は**Pixel Jeff（Jeff Lin）**氏の作品**Chill Mario 2023 ver.**を使用しています。

- 作者ページ: [Chill Mario 2023 ver.](https://www.artstation.com/artwork/RynnOv)
- 参照資料: [game-de-it/rg35xx chillmario.md](https://github.com/game-de-it/rg35xx/blob/main/chillmario.md)
- 同梱通知: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

壁紙はGAFEのMIT Licenseの対象外です。作品および描かれているキャラクターの権利は、それぞれの作者・権利者に帰属します。

## リリース作成

macOSまたはLinuxで次を実行します。

```sh
./scripts/verify.sh
./scripts/build-release.sh
```

`dist`にリリースZIPとSHA-256チェックサムが生成されます。

## ライセンス

GAFEのソースコードは[MIT License](LICENSE)で公開します。第三者のアートワークには個別のクレジットと条件が適用されます。
