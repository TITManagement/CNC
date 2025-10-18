#!/usr/bin/env python3
"""
開発環境セットアップスクリプト
- venv作成
- 必要パッケージインストール
"""
import os
import sys
import subprocess

def main():
    print("[SETUP] Python仮想環境を作成します...")
    if not os.path.exists(".venv"):
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    print("[SETUP] 必要パッケージをインストールします...")
    pip = os.path.join(".venv", "bin", "pip")
    subprocess.run([pip, "install", "-r", "requirements.txt"], check=True)
    print("[SETUP] 完了")

if __name__ == "__main__":
    main()
