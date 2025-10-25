# drivers サブパッケージ

目的
- 実機やシミュレーションのステージ制御（ドライバ）をまとめたモジュール群。

主要モジュール
- `base.py` — `CncDriver` 抽象クラス。すべてのドライバはこれを継承します。
- `chuo_stage_driver.py` — QT-BMM2 / Chuo 用ドライバ実装（`ChuoDriver`）。
- `gsc02_stage_driver.py` / `gsc02_controller.py` — GSC-02 コントローラとドライバ（`GSC02Driver`）。
- `actual_machine_control.py` — 設定に応じて実機ドライバを生成するファクトリ（`create_actual_driver` 等）。
- `qtbmm2_controller.py` — QT-BMM2 低レベルコントローラ（内部利用）。

使い方（ランナー側）
```
from common.drivers import create_actual_driver
driver, name = create_actual_driver(cfg_name, cfg)
```

注意点
- 実機を操作するコードが含まれるため、テスト時は `driver: sim` を利用するか、ハードウェアをモックしてください。
- 新しいドライバを追加する場合は `actual_machine_control.create_actual_driver` に分岐を追加してください。
