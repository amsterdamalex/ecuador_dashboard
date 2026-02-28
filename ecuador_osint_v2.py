"""Compatibility entrypoint — executes app.py."""
# Streamlit Cloud or other services may be configured to launch this filename.
# The actual application lives in app.py (with logic in config.py, analysis.py, fetchers.py).

from pathlib import Path

exec(compile(Path("app.py").read_text(), "app.py", "exec"))
