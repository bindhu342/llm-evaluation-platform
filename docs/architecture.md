# Architecture

## System Overview

```
Client
  │
  ▼
FastAPI (main.py)
  │
  ▼
EvaluationOrchestrator
  ├── RelevanceAgent
  ├── AccuracyAgent
  ├── HallucinationAgent
  ├── CompletenessAgent
  └── VerdictAgent
        │
        ▼
    Final Score + Report

RAG Pipeline (context retrieval)
  ├── Ingestion → Chunking → Embeddings
  └── FAISS Vector Store → Retriever

Database (SQLite / SQLAlchemy)
  └── Stores evaluation results
```

## Data Flow

1. Client sends `{prompt, response, context?}` to `POST /evaluate`
2. Orchestrator runs all agents in parallel
3. Each agent calls Amazon Bedrock (Claude) with a scoring prompt
4. VerdictAgent aggregates scores into a final verdict
5. Result persisted to DB and returned to client

## AWS Services Used
- **Amazon Bedrock**: LLM inference (Claude) + embeddings (Titan)
- **FAISS**: Local vector store (can swap to OpenSearch)
