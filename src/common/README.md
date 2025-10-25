# common パッケージ概要

このディレクトリはランナー（XY/XYZ）から共通で利用する機能をまとめた場所。

主な役割
- 共通ドライバ実装 / ドライバ生成ファクトリ（`drivers/`）
- G-code の解釈・共通処理（`gcode.py`）
- ジョブ定義と JobFactory（`jobs/`）
- プラットフォーム依存処理（`platform/`）
- ランタイム周りのユーティリティ（`runtime/`）

簡単な使用例
```
from common.drivers import create_actual_driver
from common.jobs import JobFactory
```

注意
- モジュールはランナーから直接参照されるため、破壊的変更は事前に確認・テストを行ってください。
- 各サブディレクトリの README を参照して内部設計を把握してください。
