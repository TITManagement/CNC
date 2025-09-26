# CNC XY Runner（日本語版）

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PowerPointで描いた図形をCNCで動かす！SVGパスベースXYコントローラ**

[特徴](#特徴) ・ [インストール](#インストール) ・ [使い方](#使い方) ・ [構成](#構成) ・ [ライセンス](#ライセンス)

</div>

## 概要

CNC XY Runnerは、PowerPointで作成した図形をSVG形式で保存し、そのパス情報をもとにCNC XYステージを制御するPythonツールです。シミュレーション表示や実機制御に対応しています。

### 主な機能

- PowerPoint → SVG → CNC制御の一気通貫ワークフロー
- GUIによるファイル選択
- matplotlibによる軌跡シミュレーション
- 中央精機XYステージ対応（シリアル通信）
- 柔軟なYAML設定
- 安全リミット・パラメータ管理

## 特徴

- ✅ PowerPoint図形をそのままCNCで描画
- ✅ SVGファイルの対話的選択
- ✅ 軌跡のリアルタイムシミュレーション
- ✅ 実機制御（中央精機XYステージ）
- ✅ YAMLによる柔軟なジョブ定義
- ✅ グリッド・円パターン生成
- ✅ 安全リミット設定
- ✅ 拡張性の高いドライバ設計

## インストール

### 推奨セットアップ

```bash
git clone https://github.com/TITManagement/CNC.git
cd CNC
./scripts/setup.sh
```

### 手動インストール

```bash
# リポジトリ取得
git clone https://github.com/TITManagement/CNC.git
cd CNC

# 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate

# 依存ライブラリインストール
pip install -r requirements.txt

# 開発モードインストール
pip install -e .
```

### 開発環境セットアップ

```bash
./scripts/setup.sh --dev
```

pytest, black, mypy等の開発ツールも導入されます。

## 使い方

### 1. 描画ソフトで図形作成 → SVG保存
例；PowerPointの場合
1. PowerPointで図形（テキスト不可）を描く
2. 「ファイル → エクスポート → SVG形式」で保存
3. 「現在のスライド」を選択

### 2. シミュレーション実行
```bash
python src/xy_runner.py examples/job_svg_path.yaml
```

### 3. SVGファイル選択
- ファイルダイアログが表示されるので、SVGファイルを選択
- matplotlibウィンドウで軌跡が表示されます

## 構成

```
CNC/
├── src/                    # ソースコード
│   └── xy_runner.py        # メインスクリプト
├── examples/               # 設定・サンプル
│   ├── job_svg_path.yaml   # SVG描画設定
│   ├── job_svg_chuo.yaml   # 実機制御設定
│   ├── job_grid_circles.yaml # グリッド円パターン
│   └── drawing.svg         # SVGサンプル
├── docs/                   # ドキュメント
│   ├── user-guide.md       # ユーザーガイド
│   └── developer-guide.md  # 開発者ガイド
├── scripts/                # ユーティリティ
│   └── setup.sh            # 環境セットアップ
├── requirements.txt        # 依存ライブラリ
├── pyproject.toml          # パッケージ設定
└── README.md               # このファイル
```
driver: sim                 # シミュレーション or 'chuo'で実機
svg_file: select            # GUIでSVGファイル選択

motion_params:
  cut_speed: 100            # 描画速度 (mm/min)
  lift_height: 5            # Z軸リフト高さ

```yaml
# examples/job_svg_path.yaml
driver: sim                 # シミュレーション or 'chuo'で実機
svg_file: select            # GUIでSVGファイル選択

  animate: true             # アニメーション表示
  title: "CNC XY Simulation"
```


## 実機対応

### 中央精機XYステージ
```
- PySerialによるシリアル通信
- COMポート・ボーレート設定可能
- 位置フィードバック
- 安全リミット管理

### シミュレーションモード
- 実機不要
- matplotlibで軌跡表示
- アニメーション・プレビュー

## ドキュメント

- 📖 [ユーザーガイド](docs/user-guide.md)
- 🔧 [開発者ガイド](docs/developer-guide.md)
- 📚 [総合ドキュメント](docs/index.md)

## コントリビュート

開発・改善への参加歓迎！詳細は[開発者ガイド](docs/developer-guide.md)参照。

### 開発フロー
1. リポジトリをフォーク
2. フィーチャーブランチ作成
3. テスト付きで修正
4. コード品質チェック（black, mypy等）
5. プルリクエスト提出

## 主な用途

- 試作・研究用途のパターン生成
- 教育・CNC原理学習
- 実験自動化
- 製造現場での図形→動作変換

## 技術情報

- Python 3.8以上対応
- 主要依存：PyYAML, matplotlib, PySerial, svgpathtools
- モジュール設計：ドライバ拡張可能
- テスト：pytest
- コード品質：black, mypy

## ライセンス

MITライセンス（詳細は[LICENSE](LICENSE)参照）

## サポート

- 📧 info@titmanagement.com
- 🐛 [GitHub Issues](https://github.com/TITManagement/CNC/issues)
- 📖 [総合ドキュメント](docs/index.md)

---

<div align="center">
<strong>PowerPoint図形をCNCで自在に動かす！教育・研究・製造現場で活用できます。</strong>
</div>