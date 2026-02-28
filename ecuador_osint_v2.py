"""Compatibility entrypoint — runs app.py via runpy."""
# Streamlit Cloud or other services may be configured to launch this filename.
# The actual application lives in app.py (with logic in config.py, analysis.py, fetchers.py).
#
# NOTE: We use runpy instead of exec(compile(...)) because exec() breaks
# Streamlit's caching (@st.cache_data, @st.cache_resource) — the decorators
# rely on the module's __name__ which exec() sets incorrectly.

import runpy

runpy.run_path("app.py", run_name="__main__")
