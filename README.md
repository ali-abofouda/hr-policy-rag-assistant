# HR Policy RAG Assistant with Enterprise AI Security

An end-to-end, enterprise-grade Retrieval-Augmented Generation (RAG) assistant designed for Human Resources policy resolution in corporate multi-national environments. Engineered with defense-in-depth security, adversarial resilience, multi-model routing, and cloud-native containerization.

---

## Architectural Evolution and Execution Modes

The project is architected with a **Dual Pipeline Design**, allowing developers to run either a 100% free offline local pipeline or an enterprise cloud-native deployment:

### 1. Local-First Zero-Cost Pipeline (Active Default)
- **Local Multi-Format Ingestion**: Ingests official HR text policies alongside multi-format distractor documents (`.pdf`, `.docx`, `.pptx`, `.txt`) directly from local storage (`data/policies` and `data/noise`).
- **Parse Once to JSON Pattern**: Converts heavy binary documents into intermediate structured JSON records inside `data/processed/`. Downstream indexing reads clean JSON, preventing redundant parsing.
- **Cost-Free Cloud & Local Compute**: Connects to Qdrant Cloud Free Tier for vector storage, Jina AI free credits for embeddings/re-ranking (with local `sentence-transformers/all-MiniLM-L6-v2` offline fallback), and Google AI Studio / Groq LPU for LLM inference.
- **Zero Cloud Billing Requirement**: Bypasses Google Cloud Platform (GCP) billing barriers, enabling offline experimentation and CI/CD testing without cloud infrastructure charges.

### 2. Google Cloud Storage (GCS) Pipeline (Enterprise Reference)
- **Cloud-Native Storage Hierarchy**: Preserves full architectural logic for GCP Cloud Storage buckets partitioned into `raw/` and `processed/` zones (`raw-hr-policies`, `raw-other-data`, `processed-hr-policies`, `processed-other-data`).
- **Documented & Ready for Production**: Code for GCS blob streaming and upload is preserved and documented in `hr_assistant/processor.py` and `hr_assistant/document_loader.py`, ready to be activated when enterprise GCP service account credentials and billing are attached.

---

## Architecture Highlights

1. **Enterprise Identity & Access Management (IAM)**:
   - Google OAuth 2.0 integration with role-based access control (RBAC), strictly white-listing authorized employee email identities.
2. **Hybrid Retrieval with High-Precision Re-Ranking**:
   - Hybrid dense vector search (Jina 768-dim embeddings) coupled with sparse lexical search (BM25 via FastEmbed) in Qdrant Cloud.
   - Deterministic point IDs (`UUID5`) ensuring idempotent upserts without duplicate records.
   - Cross-Encoder Re-ranking (`jina-reranker-v2-base-multilingual`) filtering out false-positive noise chunks.
3. **Multi-Layer Defense & AI Security Guardrails**:
   - Strict out-of-domain rejection preventing non-HR query processing.
   - Google Model Armor and system prompt isolation neutralizing prompt injection and jailbreak attacks.
   - Red Teaming evaluation suite verifying adversarial attack mitigation.
4. **Self-Hosted AI Gateway (`LiteLLM`)**:
   - Containerized proxy abstracting multi-provider LLM endpoints, enabling dynamic failover, rate limiting, and cost observability.
5. **Semantic Caching**:
   - Caching layer intercepting high-frequency employee queries to deliver sub-millisecond responses without downstream inference cost.
6. **Verifiable Explanations**:
   - Source document, policy category, and clause citations on all generated employee responses.

---

## Directory Layout

```text
01-hr-policy-rag-assistant/
├── README.md               # Architecture specification and manual
├── requirements.txt        # Pinned project dependencies
├── .env.example            # Environment template
├── ingest.py               # Ingestion pipeline CLI entry point (--force, --hr-only, --noisy-only)
├── docs/                   # Full architectural specifications and lecture guides
│   ├── README.md           # Roadmap and lecture-by-lecture index
│   ├── 01-hr-policy-assistant-architecture-and-overview.md
│   ├── 02-project-architecture-and-three-phase-evolution.md
│   ├── 03-phase-1-local-hybrid-rag-foundations.md
│   ├── 04-project-settings-and-configuration-management.md
│   ├── 05-document-loading-and-multi-format-processing.md
│   ├── 06-document-chunking-and-vector-store-ingestion.md
│   └── 07-data-ingestion-pipeline-orchestration.md
├── commands/
│   └── commands-basic-rag.md # Local-first execution and testing commands
├── hr_assistant/           # Core production package
│   ├── __init__.py
│   ├── config.py           # Centralized settings and environment validation
│   ├── logging_config.py   # Process-wide logging configuration
│   ├── prompts.py          # System prompts and behavioral guidelines
│   ├── document_loader.py  # Local and cloud document loaders (LangChain Documents)
│   ├── processor.py        # Multi-format binary parser (.pdf, .docx, .pptx, .txt)
│   ├── splitter.py         # Recursive character text chunking (500/60 overlap)
│   ├── embeddings.py       # Jina AI embeddings with local MiniLM fallback
│   ├── vector_store.py     # Qdrant hybrid vector store, stable IDs, payload index
│   └── ingestion.py        # SOLID ingestion orchestrator (Dual pipelines: Clean & Noisy)
├── data/
│   ├── policies/           # 10 official HR policy documents (.txt)
│   ├── noise/              # 8 synthetic enterprise distractor files (.pdf, .docx, .pptx, .txt)
│   └── processed/          # Pre-parsed JSON records (hr-policies/ and other-data/)
├── tests/                  # Automated unit and integration test suites
│   ├── test_splitter_and_vectorstore.py
│   └── test_ingestion.py
└── hrrenv/                 # Isolated Python 3.12 virtual environment
```

---

## Quickstart Guide

### 1. Environment Setup

Clone the repository and set up a Python 3.12 virtual environment:

```bash
cd projects/01-rag-applications/01-hr-policy-rag-assistant
python -m venv hrrenv
.\hrrenv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your free API credentials:

```bash
cp .env.example .env
```

Required keys:
- `JINA_API_KEY`: Free 1M tokens from [jina.ai](https://jina.ai).
- `QDRANT_URL` and `QDRANT_API_KEY`: Free cluster from [cloud.qdrant.io](https://cloud.qdrant.io).
- `GEMINI_API_KEY`: Free tier key from Google AI Studio.

### 3. Parse Raw Documents (Parse Once to JSON)

Execute local multi-format parsing across all policies and noise files:

```bash
python -c "from hr_assistant.processor import process_raw_to_json; print('Processed files:', process_raw_to_json())"
```

### 4. Run Unit Tests

Execute the automated test suite:

```bash
python -m unittest discover -s tests
```

---

## Course Roadmap Alignment

- **Phase 1: Basic RAG (Lectures 142 - 151)** `[Branch: basic-rag]`:
  - 142: Architecture & Live System Overview
  - 143: 3-Phase Evolution Roadmap
  - 144: Local Hybrid RAG & Data Engineering
  - 145: Configuration Management
  - 146: Document Loading & Multi-format Processing
  - 147: Document Chunking, Embeddings & Qdrant Hybrid Vector Store
  - 148 - 149: Ingestion Pipeline & Corpus Population
  - 150 - 151: Re-ranker, Guardrails & Retrieval Pipeline
- **Phase 2: Enterprise AI Security & Evals (Lectures 152 - 159)** `[Branch: ai-security]`
- **Phase 3: Production Cloud Deployment (Lectures 160 - 163)** `[Branch: deployment]`
