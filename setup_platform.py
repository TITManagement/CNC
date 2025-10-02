#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XYZ Runner クロスプラットフォーム セットアップスクリプト
Windows, macOS, Linux (Ubuntu 24.04) 対応
"""
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

class PlatformSetup:
    """プラットフォーム別セットアップクラス"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == 'windows'
        self.is_macos = self.system == 'darwin'
        self.is_linux = self.system == 'linux'
        self.project_root = Path(__file__).parent
        
    def print_platform_info(self):
        """プラットフォーム情報を表示"""
        platform_name = {
            'windows': 'Windows',
            'darwin': 'macOS',
            'linux': 'Linux'
        }.get(self.system, self.system.title())
        
        print(f"🖥️  プラットフォーム: {platform_name}")
        print(f"📋 バージョン: {platform.release()}")
        print(f"🏗️  アーキテクチャ: {platform.machine()}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print()
    
    def check_python_version(self):
        """Python バージョンチェック"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ Python 3.8以上が必要です")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    
    def get_python_executable(self):
        """プラットフォーム別のPython実行可能ファイル"""
        if self.is_windows:
            return 'python'
        else:
            return 'python3'
    
    def get_venv_activate_script(self, venv_path):
        """仮想環境のアクティベートスクリプトパス"""
        if self.is_windows:
            return venv_path / 'Scripts' / 'activate.bat'
        else:
            return venv_path / 'bin' / 'activate'
    
    def create_virtual_environment(self, venv_name):
        """仮想環境を作成"""
        print(f"📦 仮想環境 '{venv_name}' を作成中...")
        venv_path = self.project_root / venv_name
        
        if venv_path.exists():
            print(f"⚠️  既存の仮想環境 '{venv_name}' が見つかりました")
            response = input("削除して再作成しますか？ (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                shutil.rmtree(venv_path)
            else:
                print("既存の仮想環境を使用します")
                return venv_path
        
        try:
            python_cmd = self.get_python_executable()
            subprocess.run([python_cmd, '-m', 'venv', str(venv_path)], check=True)
            print(f"✅ 仮想環境 '{venv_name}' を作成しました")
            return venv_path
        except subprocess.CalledProcessError as e:
            print(f"❌ 仮想環境の作成に失敗: {e}")
            return None
    
    def install_dependencies(self, venv_path, requirements):
        """依存関係をインストール"""
        print("📦 依存関係をインストール中...")
        
        if self.is_windows:
            pip_cmd = str(venv_path / 'Scripts' / 'pip')
        else:
            pip_cmd = str(venv_path / 'bin' / 'pip')
        
        try:
            # pip を最新版にアップグレード
            subprocess.run([pip_cmd, 'install', '--upgrade', 'pip'], check=True)
            
            # 依存関係をインストール
            for package in requirements:
                print(f"  📦 {package} をインストール中...")
                subprocess.run([pip_cmd, 'install', package], check=True)
            
            # pythonocc-core は別途試行（失敗しても続行）
            try:
                print("  📦 pythonocc-core をインストール中（オプション）...")
                subprocess.run([pip_cmd, 'install', 'pythonocc-core>=7.7.0'], 
                             check=True, capture_output=True)
                print("  ✅ pythonocc-core のインストールに成功")
            except subprocess.CalledProcessError:
                print("  ⚠️  pythonocc-core のインストールに失敗（STEPファイル機能は制限されます）")
            
            print("✅ 依存関係のインストールが完了しました")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依存関係のインストールに失敗: {e}")
            return False
    
    def create_platform_launch_script(self, runner_name):
        """プラットフォーム別の起動スクリプトを作成"""
        runner_dir = self.project_root / runner_name
        venv_name = f'.venv_{runner_name}'
        
        if self.is_windows:
            # Windows バッチファイル
            script_path = runner_dir / f'run_{runner_name}.bat'
            script_content = f"""@echo off
cd /d "%~dp0"
call {venv_name}\\Scripts\\activate.bat
python {runner_name}.py %*
pause
"""
        else:
            # Unix系 シェルスクリプト
            script_path = runner_dir / f'run_{runner_name}.sh'
            script_content = f"""#!/bin/bash
cd "$(dirname "$0")"
source {venv_name}/bin/activate
python3 {runner_name}.py "$@"
"""
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Unix系では実行権限を付与
            if not self.is_windows:
                os.chmod(script_path, 0o755)
            
            print(f"✅ 起動スクリプト '{script_path.name}' を作成しました")
            return script_path
        except Exception as e:
            print(f"❌ 起動スクリプトの作成に失敗: {e}")
            return None
    
    def setup_runner(self, runner_name):
        """ランナーのセットアップ"""
        print(f"\n🚀 {runner_name} のセットアップを開始...")
        
        # 仮想環境作成
        venv_name = f'.venv_{runner_name}'
        venv_path = self.create_virtual_environment(f'{runner_name}/{venv_name}')
        if not venv_path:
            return False
        
        # 依存関係のリスト
        requirements = [
            'pyyaml>=6.0',
            'matplotlib>=3.7.0',
            'pyserial>=3.5',
            'numpy>=1.24.0'
        ]
        
        # xyz_runner の場合は追加の依存関係
        if runner_name == 'xyz_runner':
            requirements.extend([
                'svgpathtools>=1.7.0'
                # 'pythonocc-core>=7.7.0'  # インストールが困難な場合はコメントアウト
            ])
            
            # pythonocc-core のインストールは install_dependencies 内で処理
        
        # 依存関係インストール
        if not self.install_dependencies(venv_path, requirements):
            return False
        
        # 起動スクリプト作成
        script_path = self.create_platform_launch_script(runner_name)
        if not script_path:
            return False
        
        print(f"✅ {runner_name} のセットアップが完了しました")
        return True
    
    def display_usage_instructions(self):
        """使用方法を表示"""
        print("\n📖 使用方法:")
        print("=" * 50)
        
        if self.is_windows:
            print("🪟 Windows:")
            print("  xy_runner:  xy_runner\\run_xy_runner.bat")
            print("  xyz_runner: xyz_runner\\run_xyz_runner.bat")
        else:
            print("🐧 Linux / 🍎 macOS:")
            print("  xy_runner:  ./xy_runner/run_xy_runner.sh")
            print("  xyz_runner: ./xyz_runner/run_xyz_runner.sh")
        
        print("\n🔧 手動実行:")
        if self.is_windows:
            print("  cd xy_runner")
            print("  .venv_xy_runner\\Scripts\\activate.bat")
            print("  python xy_runner.py")
        else:
            print("  cd xy_runner")
            print("  source .venv_xy_runner/bin/activate")
            print("  python3 xy_runner.py")

def main():
    """メイン関数"""
    print("🛠️  XYZ Runner クロスプラットフォーム セットアップ")
    print("=" * 60)
    
    setup = PlatformSetup()
    setup.print_platform_info()
    
    # Python バージョンチェック
    if not setup.check_python_version():
        sys.exit(1)
    
    # 各ランナーのセットアップ
    runners = ['xy_runner', 'xyz_runner']
    success_count = 0
    
    for runner in runners:
        runner_path = setup.project_root / runner
        if runner_path.exists():
            if setup.setup_runner(runner):
                success_count += 1
        else:
            print(f"⚠️  {runner} ディレクトリが見つかりません")
    
    # 結果表示
    print(f"\n🎉 セットアップ完了: {success_count}/{len(runners)} ランナー")
    
    if success_count > 0:
        setup.display_usage_instructions()
    
    print("\n✨ セットアップが完了しました！")

if __name__ == "__main__":
    main()