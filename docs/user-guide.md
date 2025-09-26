# ユーザーガイド

## インストール

### クイックセットアップ
自動セットアップスクリプトを使います:
```bash
./scripts/setup.sh
```

### 手動セットアップ
1. 仮想環境の作成:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリのインストール:
   ```bash
   pip install -r requirements.txt
   ```

## 基本的な使い方

### SVGジョブの実行
1. SVGを準備する。PowerPointスライドからも作成可能
2. 設定ファイルで実行:
   ```bash
   python src/xy_runner.py examples/job_svg.yaml
   ```

### 設定ファイル
- `job_svg.yaml` - SVGファイル選択ダイアログ付きの設定
- `job_svg_chuo.yaml` - 実機制御用設定
- `job.yaml` - グリッドパターン生成

## PowerPoint → SVG ワークフロー

1. **PowerPointでスライド作成**
   - 図形ツールのみ使用（テキスト不可）
   - シンプルなデザイン推奨
   - コントラストの高い色を使う

2. **SVGとしてエクスポート**
   - ファイル → エクスポート → ファイル形式変更 → SVG
   - 「現在のスライド」を選択

3. **CNC XY Runnerで処理**
   - SVG設定ファイルを使う
   - 実行時にSVGファイルを選択

## モーションパラメータ

YAML設定で以下を調整できます:

```yaml
motion_params:
  rapid_speed: 1000    # 高速移動速度
  cut_speed: 100       # 描画速度
  lift_height: 5       # Z軸リフト高さ
```

## 安全設定

機械保護のためのリミット設定:

```yaml
safety:
  max_x: 100
  max_y: 100
  max_speed: 2000
  enable_limits: true
```

## トラブルシューティング

### よくある問題

1. **「No tracks」エラー**
   - SVGにパス要素が含まれているか確認
   - PowerPointで図形のみを使い再エクスポート

2. **ファイル選択ダイアログが表示されない**
   - tkinterがインストールされているか確認
   - デスクトップ環境がGUI対応か確認

3. **シリアル通信が失敗する**
   - COMポート設定を確認
   - ハードウェア接続を確認
   - まずはシミュレーションモードでテスト

### デバッグモード

デバッグ出力を有効化:
```yaml
debug: true
```

表示される内容:
- SVG要素の解析結果
- 生成された動作コマンド
- シリアル通信の詳細