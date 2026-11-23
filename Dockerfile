# Production Container for HR Policy RAG Assistant (Streamlit on Google Cloud Run)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package installation
RUN pip install --no-cache-dir uv

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Pre-download FastEmbed BM25 sparse text embedding model during build time
# to eliminate cold-start latency when running on serverless Google Cloud Run
RUN python -c "from fastembed import SparseTextEmbedding; SparseTextEmbedding(model_name='Qdrant/bm25')"

# Copy core application package and data directory
COPY hr_assistant/ ./hr_assistant/
COPY data/ ./data/

# Copy standalone runtime entrypoints
COPY app.py ingest.py evaluate.py main.py ./

# Expose standard Cloud Run port
EXPOSE 8080

# Health check probe for container readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# Launch Streamlit server configured for production container runtime
CMD ["streamlit", "run", "app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
