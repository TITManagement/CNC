# 開発者ガイド

## プロジェクト構成

```
CNC/
├── src/              # ソースコード
│   ├── common/       # 共有ロジック
│   ├── xy_runner/    # 2D ランナー
│   └── xyz_runner/   # 3D ランナー
├── examples/         # 設定・サンプル
│   ├── example_xy/   # XY ランナー用 YAML
│   └── example_xyz/  # XYZ ランナー用 YAML
├── docs/             # ドキュメント
├── env_setup.py      # 仮想環境セットアップ補助
└── pyproject.toml    # パッケージ設定
```

## コードアーキテクチャ

### 主要クラス

#### GCodeWrapper
Gコード生成・コマンド処理を管理:
```python
class GCodeWrapper:
    def __init__(self, config):
        # YAML設定で初期化
    def run_job(self):
        # メイン実行ループ
    def process_svg_file(self, svg_path):
        # SVG→動作コマンド変換
```

#### SimDriver
matplotlibによるシミュレーション:
```python
class SimDriver:
    def animate_tracks(self, tracks):
        # CNC動作のアニメーション
        # リアルタイム可視化
        # 軌跡表示
```

#### ChuoDriver
中央精機用ハードウェアインターフェース:
```python
class ChuoDriver:
    def __init__(self, com_port):
        # シリアル通信初期化
    def move_to(self, x, y):
        # 移動コマンド送信
```

## 開発環境セットアップ

1. **クローン＆セットアップ**:
   ```bash
   git clone https://github.com/TITManagement/CNC.git
   cd CNC
   python3 -m venv .venv_CNC
   source .venv_CNC/bin/activate
   pip install --no-build-isolation -e .
   ```

2. **pre-commitフックのインストール**:
   ```bash
   pre-commit install
   ```

## コードスタイル

Blackで整形:
```bash
black src/ --line-length 100
```

mypyで型チェック:
```bash
mypy src/
```

## テスト

pytestでテスト実行:
```bash
pytest tests/
```

## 新しいハードウェアドライバ追加

1. **ドライバクラス作成**:
   ```python
   class NewDriver:
       def __init__(self, config):
           pass
       def move_to(self, x, y):
           # ハードウェア固有の動作
           pass
       def set_speed(self, speed):
           # 速度設定
           pass
   ```

2. **mainで登録**:
   ```python
   driver_map = {
       'sim': SimDriver,
       'chuo': ChuoDriver,
       'new': NewDriver,  # 追加
   }
   ```

## 設定システム

YAML設定で以下をサポート:
- モーションパラメータ
- ハードウェア設定
- 安全リミット
- デバッグオプション

例:
```yaml
# ハードウェアドライバ選択
driver: sim  # または 'chuo', 'new'
port: /dev/tty.usbserial-XXXX
baud: 9600
mm_per_pulse: 0.0005
qt_enable_response: true
driver_settings:
  rapid_speed: 3000
  cut_speed: 1200
  accel: 100

# モーション制御
motion_params:
  rapid_speed: 1000
  cut_speed: 100

# 入力ソース
svg_file: examples/drawing.svg
# または
pattern:
  type: grid_circles
  rows: 3
  cols: 3

# XYZ Runner でステージ制御する例
driver: chuo
port: /dev/tty.usbserial-XXXX
baud: 9600
mm_per_pulse: 0.0005
qt_enable_response: true
driver_settings:
  rapid_speed: 5000
  cut_speed: 1500
  accel: 150

# GSC-02 ドライバを使う例
driver: gsc02
port: /dev/tty.usbserial-GSC02
baud: 9600
timeout: 1.5
write_timeout: 1.5
mm_per_pulse: 0.001
```

## SVG処理

`svgpathtools`でパス抽出:

```python
from svgpathtools import svg2paths

def process_svg_file(self, svg_path):
    paths, attributes = svg2paths(svg_path)
    for path in paths:
        # パス→座標変換
        points = self.path_to_points(path)
        # 動作コマンド生成
        self.add_track(points)
```

## デバッグ

設定でデバッグモード有効化:
```yaml
debug: true
```

詳細な解析・コマンド生成・通信・アニメーション情報が表示されます。

## コントリビュート

1. リポジトリをフォーク
2. フィーチャーブランチ作成
3. テスト付きで修正
4. コード品質チェック
5. プルリクエスト提出

### コード品質チェックリスト
- [ ] Black整形済み
- [ ] 型ヒント追加
- [ ] テスト作成
- [ ] ドキュメント更新
- [ ] Lintエラーなし
