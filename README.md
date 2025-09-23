# XY Runner (中央精機 + SVG対応)

PowerPointで描いた図形をSVGとして保存し、そのパスを中央精機XYコントローラで描画・動作させるためのPythonスクリプトです。  
シミュレーション表示も可能です。

---

## インストール

依存ライブラリをインストールしてください:

```bash
pip install pyyaml matplotlib pyserial svgpathtools
```

---

## ファイル構成

- `xy_runner.py` : メインスクリプト
- `job_svg.yaml` : シミュレーション用サンプル設定
- `job_svg_chuo.yaml` : 中央精機実機用サンプル設定
- `job.yaml` : グリッド円パターンのサンプル設定（grid_circlesジョブ）

---

## 使い方

### 1. PowerPoint → SVG
1. PowerPointで図形を描く
2. 図形を選択して **右クリック → 図として保存 → SVG形式** で保存
3. 出力されたSVGファイルを `job_svg_chuo.yaml` の `jobs[0].file` に指定

### 2. シミュレーション表示
```bash
python xy_runner.py --config job_svg.yaml
```
- matplotlibウィンドウに軌跡が表示されます
- `visual.animate: true` にすると経路をアニメーション表示

### 3. 中央精機実機制御
```bash
python xy_runner.py --config job_svg_chuo.yaml
```

#### `job_svg_chuo.yaml` の主なパラメータ
- `port` : 接続するシリアルポート (例: `COM3`, `/dev/ttyUSB0`)
- `baud` : ボーレート (通常 9600)
- `mm_per_pulse` : 1パルスあたりの移動量 [mm]  
  (例: 2000 pulse/mm の場合は `0.0005`)
- `jobs[0].file` : PowerPointから保存したSVGファイル
- `origin` : 機械座標系での配置オフセット [mm]
- `px_to_mm` : px→mm 換算係数。96dpi前提なら `0.264583`  
  (実測してズレる場合は微調整)
- `chord_mm` : 曲線サンプリング間隔 [mm]  
  (小さいほど滑らかだがコマンドが多くなる)
- `y_flip` : 機械座標とSVGのY方向が逆なら `true` にする  
  → この場合は `svg_height_mm` を指定
- `feed` : 送り速度 [mm/min]

### 4. グリッド円パターンのサンプル実行

`job.yaml`にはグリッド状に円を描くサンプルジョブが定義されています。
シミュレーション表示で動作確認できます。

```bash
python xy_runner.py --config job.yaml
```
- matplotlibウィンドウにグリッド円の軌跡が表示されます
- 設定は`job.yaml`で調整できます（セルサイズや円径など）

---

## 精度調整の流れ
1. まず `job_svg.yaml` でSIM確認
2. 実機で小さい図形を描き、定規で寸法を実測
3. `px_to_mm` を微調整 (例: 0.263〜0.266 など)
4. 曲線がカクカクする場合は `chord_mm` を小さくする (例: 0.2)

---

## 注意点
- 本スクリプトはあくまで簡易Gコードラッパです。  
  複雑な加工用パスや高精度CAD用途にはInkscape + 専用CAMツールを推奨します。
- SVGは **線のパス** のみ対象です。塗りつぶし(Fill)は無視されます。
- 中央精機コントローラに依存する実装のため、パルス単位の調整は必ず実機仕様を確認してください。

---

## ライセンス
MIT

## 仮想環境の利用推奨

Pythonの仮想環境を使うことで、他のプロジェクトと依存関係が混ざるのを防げます。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml matplotlib pyserial svgpathtools
```

## 実行例

仮想環境を有効化した状態で、以下のコマンドを実行してください。

```bash
source .venv/bin/activate
python xy_runner.py --config job_svg.yaml
```

## SVGファイルについて

`job_svg.yaml`の`file:`に指定するSVGファイル（例: `drawing.svg`）が存在しない場合はエラーになります。
PowerPointからエクスポートしたSVGがない場合、以下のような簡単なSVGをテキストエディタで作成しても動作確認できます。

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <circle cx="50" cy="50" r="30" fill="none" stroke="black" stroke-width="2"/>
  <rect x="120" y="120" width="60" height="60" fill="none" stroke="black" stroke-width="2"/>
</svg>
```

## 依存ライブラリのバージョン例

- Python 3.8〜3.13
- pyyaml 6.0以上
- matplotlib 3.7以上
- pyserial 3.5以上
- svgpathtools 1.7以上

## matplotlibの警告について

matplotlibのバージョンによってはアニメーション表示時に警告が出る場合がありますが、動作には問題ありません。
警告を消したい場合は最新版にアップデートするか、FAQなどに対処法を記載してください。
