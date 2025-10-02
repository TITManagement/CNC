# 検証ガイド


このプロジェクトの検証手順やテスト方針を記載します。

## シミュレーション動作確認

1. 仮想環境を有効化し、依存パッケージをインストール
	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
	```
2. サンプルYAML（例: examples/[SIM]sample_SVG.yaml）でシミュレーション実行
	```bash
	python src/xy_runner.py --config examples/[SIM]sample_SVG.yaml --show
	```
3. matplotlibウィンドウで軌跡が表示されることを確認

## 実機動作確認

1. 実機（中央精機XYステージ）をPCに接続
2. 実機用YAML（例: examples/[REAL]job_svg_path_chuo.yaml）を選択
3. ポート・ボーレート等の設定値を確認
4. 実行コマンド例
	```bash
	python src/xy_runner.py --config examples/[REAL]job_svg_path_chuo.yaml
	```
5. 実機が指定通り動作することを確認

## SVGパス処理検証

1. Inkscape, Illustrator, PowerPoint等でSVGファイルを作成
2. サンプルYAMLでSVGファイルを指定し、シミュレーションまたは実機で実行
3. SVGのパスが正しくCNC動作に変換されることを確認

## その他

- テストコード（pytest）による自動検証も推奨
- 依存パッケージのバージョン違いによる動作差異に注意
