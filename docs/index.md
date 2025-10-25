# CNC ドキュメント ハブ

このディレクトリは「誰が・何をしたいのか」に合わせて必要な情報へ素早くたどり着くための入り口です。

## まず把握したいこと（用途別）

| 知りたいこと / やりたいこと | 読むべき資料 |
| --- | --- |
| 初めてセットアップして実行したい | [ユーザーガイド](user-guide.md) – セットアップ手順とサンプル使用方法 |
| コード構成や実機ドライバの仕組みを理解したい | [開発者ガイド](developer-guide.md) – モジュール構成と実機ドライバ呼び出しの流れ |
| プロジェクト全体の紹介がほしい | [README](../README.md) – 機能概要と背景 |

## クイックスタート

1. **仮想環境を用意**
   ```bash
   python3 -m venv .venv_CNC
   source .venv_CNC/bin/activate
   ```
2. **依存をインストール**
   ```bash
   pip install --no-build-isolation -e .
   ```
3. **シミュレーション動作確認**
   ```bash
   python -m xy_runner.xy_runner --config examples/example_xy/SIM_sample_SVG.yaml
   ```
4. **実機接続テスト**（中央精機や GSC-02 を利用する場合）
   - 設定ファイルの `driver` を `chuo` あるいは `gsc02` に変更し、ポート名・ボーレートなどを記入
   - 低速モードで安全に動作確認

## このプロジェクトでできること
- SVG / G-code / STEP から CNC 動作を生成
- matplotlib を使った 2D / 3D シミュレーション表示
- 中央精機 QT-BMM2 と OptoSigma GSC-02 ステージの制御
- YAML による柔軟な設定とドライバ拡張

---

目的にあった資料を読むことで、必要な情報へすばやくアクセスできます。分からない点は Issue や Pull Request で遠慮なくご相談ください。
