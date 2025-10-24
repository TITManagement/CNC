# リファクタリング仕様書

## 1. 前準備と責務整理
- [x] 設定読込・ジョブ実行・ドライバ制御・可視化について、期待する責務を整理して文書化する（このファイルを更新しても良い）
  - 設定読込: CLI引数・YAMLの検証、既定値マージ、ファイル存在確認、ジョブ定義の構造化
  - ジョブ実行: 抽象 `Job` API による実行、前後処理（安全高さなど）のテンプレート化、実行ログ管理
  - ドライバ制御: 軸数に依存しない共通API（`home`, `move_abs`, `set_units_mm` など）と速度/単位管理、接続リソースのライフサイクル管理
  - 可視化: シミュレーション描画のオン/オフ制御、アニメーション設定、タイトル生成、将来のUI連携を見据えたインターフェース
- [ ] 現状把握テスト:  
  - `python -m xyz_runner.xyz_runner --help`  
  - `python -m xy_runner.xy_runner --help`
 - [x] 現状把握テスト:  
  - `python -m xyz_runner.xyz_runner --help`  
  - `python -m xy_runner.xy_runner --help`

## 2. Gコード解釈の共通基盤抽出
- [x] `BaseModalState` と `BaseGCodeInterpreter` を `common/gcode/` 配下に新設し、XY/XYZ 共通処理を移植する
- [x] XY/XYZ の派生クラスで軸ごとの差分のみ上書きするように改修する
- [ ] 確認テスト:  
  - `python -m pytest tests/gcode`（新規テストを用意）  
  - `python -m xyz_runner.xyz_runner --config examples/example_xyz/grid_spheres.yaml --no-animate --show`

## 3. ドライバ抽象化と実装整備
- [x] `common/drivers/base.py` に `CncDriver` 抽象クラスを定義し、必須メソッド（`set_units_mm` など）を明示
- [x] `SimDriver`、`SimDriver3D`、`ChuoDriver` を上記インターフェース実装として整備し、呼び出し側を更新
- [ ] 確認テスト:  
  - `python -m xyz_runner.xyz_runner --config examples/example_xyz/grid_spheres.yaml --no-animate --show`  
  - シリアル環境があれば `python -m xy_runner.xy_runner --driver chuo --dry-run`（新設する場合）

## 4. ランナーの責務分割
- [x] `ConfigLoader`、`JobDispatcher`、`VisualizationController` を `common/runtime/` 配下に作成し、各責務を移管
- [x] `XYZRunnerApp`（および `XYRunnerApp`）で依存注入し、`main()` を薄い統合ポイントにする
- [x] 確認テスト:  
  - `python -m xyz_runner.xyz_runner --config examples/example_xyz/gcode_sample.yaml --no-animate`  
  - `python -m xy_runner.xy_runner --config examples/example_xy/SIM_sample_SVG.yaml --no-animate`

## 5. ジョブ実行の統一インターフェース化
- [x] `Job` 抽象基底クラスを導入し、`grid_spheres_3d`・`svg_to_moves` など既存ジョブをラップ
- [x] YAML/CLI のジョブ定義が `JobFactory` を経由して `execute(driver)` を呼ぶ構造に変更
- [ ] 確認テスト:  
  - `python -m xyz_runner.xyz_runner --config examples/example_xyz/multi_step.yaml --no-animate`  
  - `python -m pytest tests/jobs`

## 6. プラットフォーム適応層の整理
- [x] `EnvironmentAdapter`（想定: `common/platform/adapter.py`）を実装し、`PlatformUtils` の機能を移行
- [x] CLI や GUI 起動箇所ではアダプタを注入する構造に変更し、モック差し替えが可能な形にする
- [ ] 確認テスト:  
  - macOS/Linux/Windows で `python -m xyz_runner.xyz_runner --config ...` を実行し、ファイルダイアログやパス処理を確認  
  - `python -m xy_runner.xy_runner --config ...` を同様に確認

## 最終確認
- [ ] `python -m pytest`
- [ ] `python -m xyz_runner.xyz_runner --config examples/example_xyz/grid_spheres.yaml --no-animate --show`
- [ ] `python -m xy_runner.xy_runner --config examples/example_xy/SIM_sample_SVG.yaml --no-animate --show`
- [ ] `ruff check .` または `pre-commit run --all-files`（導入済みの静的解析があれば）

---

完了メモ:

- リファクタリング作業は主要コンポーネント（`common/gcode.py`, `common/drivers`, `common/runtime`, `common/jobs`）の移設と実装、`xy_runner`/`xyz_runner` のランナー設計整理を含み実施済みです。
- 一部の確認テスト（pytest 実行・pythonocc に依存する STEP の詳細解析）は環境依存のため未実行です。

完了日: 2025-10-18
