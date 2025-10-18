# CNC XY Runner ドキュメント

このプロジェクトは、中央精機 XY ステージやシミュレーション環境で SVG パスやパターンを CNC 動作として実行する Python アプリケーションです。

## ドキュメント一覧

- [ユーザーガイド](user-guide.md)
  - セットアップ、使い方、設定例
- [開発者ガイド](developer-guide.md)
  - コード構成、拡張方法、テスト
- [README.md](../README.md)
  - プロジェクト概要、日本語説明

## 主な機能

- SVGファイルやパターンからCNC動作を生成
- シミュレーション（matplotlib）と実機制御（中央精機）
- YAMLによる柔軟な設定
- コマンドラインから簡単操作
- 拡張可能なドライバ設計

## 使い方概要 (最短)

1. 仮想環境を作る／有効化
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
2. 依存をインストール（最低限）
  ```bash
  pip install -r requirements.txt
  ```
3. シミュレーションで素早く動作確認（smoke）
  ```bash
  # XY シミュレーション（短距離移動）
  python - <<'PY'
  import sys
  sys.path.insert(0, '.')
  from xy_runner.xy_runner import SimDriver, GCodeWrapper
  d = SimDriver(); g = GCodeWrapper(d)
  g.exec('G21 G90'); g.exec('F100'); g.exec('G0 X1 Y1'); g.exec('G1 X2 Y2')
  print('OK', len(d.tracks))
  PY
  ```

4. 実機接続時は `--driver chuo` と設定ファイルで `port`/`baud` を指定して低速でテストしてください。

## 最近の変更（簡潔）

- 一部の `common/` モジュールをバックアップから復元し、`xy_runner` / `xyz_runner` が動作する状態にしました。
- 未使用と判断した `common/driver.py` と `common/utils.py` は可逆的に `archived/common/` に移動済みです。

上記の操作は master に反映済みで、シミュレーションの smoke テストは現状で動作確認済みです。

## サポート・コントリビュート

- Issue・Pull Request歓迎
- ドキュメント・コード改善提案も歓迎

---

詳細は各ガイドを参照してください。