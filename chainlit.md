# HR Policy RAG Assistant

Enterprise conversational assistant for company HR policies, powered by LangGraph, Qdrant hybrid retrieval, and FastEmbed ONNX embeddings.

### Core Capabilities

- **Leave and Time Off:** Annual, sick, casual, maternity/paternity, and carry-forward guidelines.
- **Remote Work Policies:** Work-from-home eligibility, equipment allowances, and approvals.
- **Probation and Notice:** Notice periods during and after probation, exit procedures, and settlements.
- **Expense Reimbursements:** Internet bills, certifications, travel allowances, and claim limits.

### Architecture Highlights

- **Two-Stage Retrieval:** Qdrant hybrid search (Dense + BM25) followed by Cross-Encoder re-ranking.
- **Conversational Memory:** Multi-turn session persistence using LangGraph checkpointing.
- **Observability:** End-to-end tracing and latency monitoring with LangSmith.
