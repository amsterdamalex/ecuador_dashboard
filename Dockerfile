FROM python:3.11-slim

WORKDIR /app

# Install build deps, Python packages, then remove build deps to shrink image
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m textblob.download_corpora && \
    apt-get purge -y --auto-remove build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy Streamlit config (disables file watcher, telemetry)
COPY .streamlit/ .streamlit/

# Copy application code
COPY config.py analysis.py fetchers.py app.py ./

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]
