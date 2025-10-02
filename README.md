# CNC XY/XYZ Runner（クロスプラットフォーム対応）

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

**SVG・G-code・STEPファイル対応CNCコントローラ：Windows・Mac・Linuxで動作！**

[特徴](#特徴) ・ [インストール](#インストール) ・ [使い方](#使い方) ・ [構成](#構成) ・ [ライセンス](#ライセンス)

</div>

## 概要

汎用ドローソフト（Inkscape, Illustrator, PowerPoint等）で作成したSVG図形、G-codeファイル、STEPファイルをCNC制御で実行するクロスプラットフォーム対応Pythonツールです。

### サポートプラットフォーム
- 🪟 **Windows** (Windows 10/11)
- 🍎 **macOS** (macOS 10.15+)
- 🐧 **Linux** (Ubuntu 24.04, その他ディストリビューション)

### 主な機能

- **2D制御 (xy_runner)**: SVG（Inkscape, Illustrator, PowerPoint等） → CNC制御
- **3D制御 (xyz_runner)**: G-codeファイル・STEPファイル → 3D CNC制御
- GUIによる直感的なファイル選択
- matplotlibによる軌跡シミュレーション（2D/3D）
- 中央精機XYステージ対応（シリアル通信）
- クロスプラットフォーム自動セットアップ

## 特徴

### 2D制御 (xy_runner)
- ✅ SVG図形（Inkscape, Illustrator, PowerPoint等）をそのままCNCで描画
- ✅ SVGファイルの対話的選択
- ✅ 2D軌跡のリアルタイムシミュレーション

### 3D制御 (xyz_runner)
- ✅ G-codeファイル・STEPファイル直接実行
- ✅ 3D軌跡アニメーション表示
- ✅ ファイル選択のみのシンプルUI

### 共通機能
- ✅ クロスプラットフォーム対応（Windows・macOS・Linux）
- ✅ 実機制御（中央精機XYステージ）
- ✅ プラットフォーム別自動セットアップ
- ✅ 安全リミット設定
- ✅ 拡張性の高いドライバ設計

## インストール

### 🚀 ワンクリックセットアップ（推奨）

```bash
git clone https://github.com/TITManagement/CNC.git
cd CNC
python setup_platform.py
```

プラットフォームを自動検出し、仮想環境・依存関係・起動スクリプトを一括設定します。

### 🛠️ 手動インストール

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
Inkscape, Illustrator, PowerPointなど任意のドローソフトで図形（テキスト不可）を作成し、SVG形式で保存してください。
（PowerPointの場合は「ファイル → エクスポート → SVG形式」で保存、「現在のスライド」を選択）

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
- 🧪 [検証ガイド](VERIFICATION_GUIDE.md)

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
<strong>SVG図形（Inkscape, Illustrator, PowerPoint等）をCNCで自在に動かす！教育・研究・製造現場で活用できます。</strong>
</div>