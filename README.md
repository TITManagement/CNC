# XY Runner (中央精機 + SVG対応)

PowerPointで描いた図形をSVGとして保存し、そのパスを中央精機XYコントローラで描画・動作させるためのPythonスクリプトです。シミュレーション表示も可能です。

## 特徴

- **PowerPoint → SVG → CNC加工**: PowerPointで作成した図形を直接CNC加工
- **シミュレーション表示**: matplotlib による軌跡のリアルタイム表示
- **対話的操作**: 設定ファイルやSVGファイルをGUIで選択可能
- **柔軟な設定**: YAML設定ファイルで細かなパラメータ調整

## クイックスタート

### 1. 依存ライブラリのインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml matplotlib pyserial svgpathtools
```

### 2. 実行

```bash
# 設定ファイルを選択して実行
python xy_runner.py

# または、直接指定
python xy_runner.py --config job_svg.yaml
```

## ファイル構成

- **`xy_runner.py`** : メインスクリプト
- **`job_svg.yaml`** : SVG描画用設定（シミュレーション）
- **`job_svg_chuo.yaml`** : 中央精機実機用設定
- **`job.yaml`** : グリッド円パターンのサンプル設定
- **`drawing.svg`** : テスト用SVGサンプル

## 使い方

### 1. PowerPoint → SVG
1. PowerPointで図形を描く（**図形ツール**を使用、テキストは不可）
2. 図形を選択して **右クリック → 図として保存 → SVG形式** で保存
3. 設定ファイルで `file:` を空にするか、実行時にファイル選択ダイアログから選択

### 2. シミュレーション表示
```bash
python xy_runner.py --config job_svg.yaml
```
- matplotlibウィンドウに軌跡が表示されます
- `visual.animate: true` にすると経路をアニメーション表示
- `visual.fps: 75` で描画速度を調整可能

### 3. 中央精機実機制御
```bash
python xy_runner.py --config job_svg_chuo.yaml
```

### 4. グリッド円パターンのサンプル実行
```bash
python xy_runner.py --config job.yaml
```
- グリッド状に円を描くサンプル
- 設定は`job.yaml`で調整可能（セルサイズや円径など）

## 設定パラメータ

### `job_svg_chuo.yaml` の主なパラメータ
- `port` : 接続するシリアルポート (例: `COM3`, `/dev/ttyUSB0`)
- `baud` : ボーレート (通常 9600)
- `mm_per_pulse` : 1パルスあたりの移動量 [mm] (例: 2000 pulse/mm の場合は `0.0005`)
- `jobs[0].file` : PowerPointから保存したSVGファイル（空の場合はファイル選択ダイアログ）
- `origin` : 機械座標系での配置オフセット [mm]
- `px_to_mm` : px→mm 換算係数。96dpi前提なら `0.264583`
- `chord_mm` : 曲線サンプリング間隔 [mm] (小さいほど滑らか)
- `y_flip` : 機械座標とSVGのY方向が逆なら `true`
- `feed` : 送り速度 [mm/min]

## 精度調整の流れ
1. まず `job_svg.yaml` でシミュレーション確認
2. 実機で小さい図形を描き、定規で寸法を実測
3. `px_to_mm` を微調整 (例: 0.263〜0.266 など)
4. 曲線がカクカクする場合は `chord_mm` を小さくする (例: 0.2)

## SVGファイルについて

### 対応する図形
- **対応**: `<path>`, `<circle>`, `<rect>`, `<line>`, `<polygon>` などの図形要素
- **非対応**: `<text>` (テキスト要素はパス情報に変換されません)

### PowerPointでの作成ポイント
- **図形ツール**で描画する（円、四角、線、フリーハンドなど）
- テキストではなく、**線画**として作成
- 複数図形のグループ化も可能

### テスト用SVGサンプル
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <circle cx="50" cy="50" r="30" fill="none" stroke="black" stroke-width="2"/>
  <rect x="120" y="120" width="60" height="60" fill="none" stroke="black" stroke-width="2"/>
</svg>
```

## システム要件

- **Python**: 3.8〜3.13
- **依存ライブラリ**:
  - pyyaml 6.0以上
  - matplotlib 3.7以上
  - pyserial 3.5以上
  - svgpathtools 1.7以上

## 注意点

- 本スクリプトはあくまで簡易Gコードラッパです
- 複雑な加工用パスや高精度CAD用途にはInkscape + 専用CAMツールを推奨
- SVGは **線のパス** のみ対象です。塗りつぶし(Fill)は無視されます
- 中央精機コントローラに依存する実装のため、パルス単位の調整は必ず実機仕様を確認してください

## トラブルシューティング

### "No tracks" エラーが出る場合
- SVGファイルにパス情報（`<path>`, `<circle>` など）が含まれているか確認
- PowerPointでテキストではなく図形ツールを使用しているか確認

### matplotlibの警告について
- matplotlibのバージョンによってはアニメーション表示時に警告が出る場合がありますが、動作には問題ありません

## ライセンス

MIT