# StockOS復旧手順

[English](RECOVERY.md)

## GAFE画面から

1. SELECTを押してシステムメニューを開きます。
2. `Restore StockOS`を選択してAを押します。
3. `Yes`を選択してAを押します。

現在のGAFE設定を保存し、元のStockOSランチャーとRetroArch設定を復元して自動的に再起動します。

## SSHから

```sh
ssh root@DEVICE_IP
/mnt/mmc/Roms/PORTS/GAFE-OFF.sh
```

## 手動復旧

端末固有のStockOSランチャーバックアップは次の場所にあります。

```text
/mnt/mmc/GAFE_HOME/backups/launcher.stock.sh
```

rootファイルシステムを操作できる環境で、このファイルを`/etc/init.d/launcher.sh`へ実行権限付きで戻します。`/etc/gafe-mode`と`/etc/rafe-mode`を削除して再起動します。別個体や別StockOS版のランチャーで代用しないでください。

導入前のRetroArchシェーダー設定とGBAコア設定は次の場所にあります。

```text
/mnt/mmc/GAFE_HOME/backups/retroarch-config
```

GAFE専用設定は`/mnt/mmc/GAFE_HOME/settings`に維持され、次回GAFE-ONで再適用されます。

GAFEの起動前検査に失敗した場合も、セッションはGAFE-OFFを自動実行してStockOSへ戻る処理を試みます。
