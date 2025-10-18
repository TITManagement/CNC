Developer tools and setup
=========================

This directory contains developer-facing helper scripts and wrappers.

Layout
- dev/scripts/: original setup scripts (shell and python)
- dev/wrappers/: small wrappers to call packaged entrypoints

Important: `pyproject.toml` must remain at the repository root for packaging and editable installs
(`pip install -e .`). We therefore do not move `pyproject.toml` into `dev/`.

Usage
- Use the root Makefile which now points to `dev/scripts/setup.sh`.
- Or call the packaged entrypoint:
  ```sh
  python3 -m cnc_tools.setup_platform
  ```

If you prefer a different layout, we can adjust the Makefile or create additional wrappers.
