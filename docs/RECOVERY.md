# StockOS復旧手順

## GAFE画面から

1. SELECTを押します。
2. `StockOSへ戻す`をAで選びます。
3. 確認画面で`はい`を選び、Aを押します。

端末はStockOSランチャーと導入前のRetroArchシェーダー／GBAコア設定を復元して再起動します。

GAFE内で変更した設定は`/mnt/mmc/GAFE_HOME/settings`に保存されるため、再度GAFEを有効にすると復元されます。

## SSHから

```sh
ssh root@DEVICE_IP
/mnt/mmc/Roms/PORTS/GAFE-OFF.sh
```

## OFFスクリプトも実行できない場合

復旧に使う端末固有バックアップは次の場所にあります。

```text
/mnt/mmc/GAFE_HOME/backups/launcher.stock.sh
```

rootファイルシステムを操作できる環境で、このファイルを`/etc/init.d/launcher.sh`へ実行権限付きで戻し、`/etc/gafe-mode`と`/etc/rafe-mode`を削除します。別個体や別StockOS版のランチャーで代用しないでください。

GAFEの起動前検査またはFE起動が失敗した場合も、利用可能なバックアップからStockOSへ自動復旧して再起動します。
