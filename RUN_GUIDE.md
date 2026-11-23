# Execution and Run Guide: HR Policy RAG Assistant

This guide details all execution commands, endpoints, and operational workflows for running, testing, and deploying the HR Policy Assistant locally on Windows or within Docker containers.

---

## 1. Environment Activation and Verification

Ensure your PowerShell session has navigated to the project root directory and the virtual environment is activated:

```powershell
# Navigate to the project root
cd d:\Code\AI\rag-mastery\projects\01-rag-applications\01-hr-policy-rag-assistant

# Activate the virtual environment
.\hrrenv\Scripts\Activate.ps1
```

Verify your environment configuration file (`.env`):
- Ensure `GEMINI_API_KEY` is set.
- Ensure `QDRANT_URL` and `QDRANT_API_KEY` are configured.

---

## 2. Interactive Streamlit Web UI

Run the human-facing chat interface directly:

```powershell
# Launch Streamlit with auto-reloading
.\hrrenv\Scripts\streamlit run app.py
```

- **Local URL:** `http://localhost:8501`
- **Network URL:** `http://192.168.x.x:8501`
- **Access Control:** Operates in `Open (Local)` mode without Google OAuth gating.

---

## 3. Production FastAPI REST Service

Run the high-performance async REST API server powered by Uvicorn:

```powershell
# Launch Uvicorn with auto-reload on port 8000
.\hrrenv\Scripts\uvicorn src.main:app --reload --port 8000
```

### Essential API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `http://127.0.0.1:8000/docs` | `GET` | Interactive Swagger UI documentation |
| `http://127.0.0.1:8000/redoc` | `GET` | ReDoc API specifications |
| `http://127.0.0.1:8000/health` | `GET` | Health check and subsystem latency |
| `http://127.0.0.1:8000/api/v1/query` | `POST` | Primary RAG generation query endpoint |
| `http://127.0.0.1:8000/api/v1/feedback` | `POST` | User feedback collection endpoint |

### Example Query Request (PowerShell / curl)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/query" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"query": "How many days of annual leave do I get?", "department": "Engineering"}'
```

---

## 4. Knowledge Ingestion Pipeline

Process policy documents, chunk text, generate dense and sparse embeddings, and synchronize vectors into Qdrant:

```powershell
# Run ingestion (skips already processed files based on MD5 hash)
.\hrrenv\Scripts\python ingest.py

# Force full re-ingestion of all documents
.\hrrenv\Scripts\python ingest.py --force
```

---

## 5. Automated RAG Triad Evaluation Pipeline

Run automated offline evaluation against ground-truth datasets to compute Faithfulness, Answer Relevance, and Context Precision:

```powershell
# Run evaluation across evaluation dataset
.\hrrenv\Scripts\python evaluate.py
```

Evaluation summaries and CSV trace reports are written to the `evaluation/` directory.

---

## 6. Automated Unit and Integration Test Suite

Execute the comprehensive 53-test test suite covering core domain services, safety guardrails, semantic caching, vector stores, and REST endpoints:

```powershell
# Execute full test suite via unittest discovery
$env:PYTHONPATH="."
.\hrrenv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

To run a single test module:

```powershell
# Example: Run container and access control tests
.\hrrenv\Scripts\python -m unittest tests/test_container_and_access_control.py

# Example: Run REST API router tests
.\hrrenv\Scripts\python -m unittest tests/test_api.py
```

---

## 7. Docker and Docker Compose (Multi-Container Execution)

Run microservices using the official container architecture:

```powershell
# Build container images
docker compose build

# Start the Streamlit App and FastAPI REST API in the background
docker compose up -d app api

# Run the Ingestion batch service using the tools profile
docker compose run --rm ingest

# Run the Evaluation batch service using the tools profile
docker compose run --rm eval

# View live container logs
docker compose logs -f

# Stop and tear down running containers
docker compose down
```

---

## 8. Summary of Ports and Default URLs

- **Streamlit Frontend:** `http://localhost:8501`
- **FastAPI REST API:** `http://localhost:8000`
- **Swagger Documentation:** `http://localhost:8000/docs`
- **Health Probe:** `http://localhost:8000/health`
