Quick run instructions (minimal)

macOS / Linux (zsh/bash)

1. Create a venv and install dependencies (from repo root):

   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .

2. Prepare environment (single-step):

From repo root run the environment setup helper (cross-platform):

   python env_setup.py

After that, activate the venv and run the application as needed (see below).


Windows (cmd.exe)

1. Create venv and install:

   python -m venv .venv
   .\.venv\Scripts\activate.bat
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .

2. Run a runner (Windows):

After running `python env_setup.py` and activating the venv, run:

   python xy_runner\xy_runner.py --config job.yaml

Notes:
- The launchers prefer a project-level `.venv`. If you used per-runner venvs like `.venv_xy_runner`, they will be used automatically.
- If the package was installed (pip install -e .), the installed entrypoint `cnc-xy-runner` / `cnc-xyz-runner` will be used instead of the repository script.
