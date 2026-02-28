"""Compatibility entrypoint — redirects to app.py."""
# Streamlit Cloud or other services may be configured to launch this filename.
# The actual application lives in app.py (with logic in config.py, analysis.py, fetchers.py).

import runpy
runpy.run_path("app.py", run_name="__main__")
