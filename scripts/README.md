# scripts ディレクトリ

このディレクトリには開発環境のセットアップを補助するスクリプトが入っています。

ファイル:
- `setup.sh` - シェル実装のセットアップスクリプト。仮想環境の作成、依存関係のインストール、開発モードでのインストールを行います。
- `setup_dev_environment.py` - Python 実装のセットアップスクリプト。`.venv` を作成して `requirements.txt` をインストールします。

使い分け:
- システムに bash/zsh がありシンプルに実行したい場合は `setup.sh` を使ってください:
  ```sh
  ./scripts/setup.sh
  # or with dev deps
  ./scripts/setup.sh --dev
  ```
- Python ベースで同等の処理を実行したい場合は次を使います:
  ```sh
  python3 scripts/setup_dev_environment.py
  ```

推奨ワークフロー:
1. リポジトリルートで `make setup` を実行（Makefile がプロジェクトルートにある場合）
2. 開発用依存も含めたい場合は `make dev-setup` を実行

注意点:
- スクリプトは `.venv` を作成します。既に存在する場合は再利用されます。
- `requirements-dev.txt` が存在する場合のみ `--dev` フラグで開発依存をインストールします。存在しない環境でもエラーにならないようスクリプトは設計されていますが、必要なら `requirements-dev.txt` を追加してください。

問題や改善案があれば README を更新して下さい。
