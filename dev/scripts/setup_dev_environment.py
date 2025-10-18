#!/usr/bin/env python3
"""Wrapper proxy to repository-level scripts/setup_dev_environment.py"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SCRIPT = os.path.join(ROOT, 'scripts', 'setup_dev_environment.py')
subprocess.run([sys.executable, SCRIPT] + sys.argv[1:], check=True)
