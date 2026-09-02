# Tech Stack

**Project:** Robust LLM Response Evaluation Platform  
**Milestone:** M1 — Proposed Technology Stack  
**Date:** August 2025

> All technologies listed below are **proposed** for the complete system. Technology choices will be confirmed and implemented in subsequent milestones.

---

## Proposed Tech Stack

| Component | Technology | Justification |
|---|---|---|
| Programming Language | Python 3.11+ | Industry standard for ML/AI projects; rich ecosystem of LLM and NLP libraries |
| Frontend | React.js | Component-based UI framework; suitable for building an interactive evaluation dashboard |
| Backend | FastAPI | Async-first Python web framework; automatic OpenAPI docs; native Pydantic integration |
| LLM Provider | OpenAI API / Hugging Face | OpenAI API for high-quality LLM-as-a-Judge scoring; Hugging Face as an open-source alternative |
| Embeddings | Sentence Transformers | Lightweight, local embedding model (`all-MiniLM-L6-v2`); no API key required; good semantic quality |
| Vector Database | ChromaDB | Open-source, lightweight vector store; persistent storage; integrates with LangChain |
| Dataset Source | Hugging Face `datasets` | Provides easy access to TruthfulQA and SQuAD v2 for benchmarking |
| RAG Framework | LangChain / Custom Python Pipeline | LangChain provides document loaders, text splitters, and retrieval chains; custom pipeline for flexibility |
| Evaluation Framework | RAGAS + Custom Evaluation Agents | RAGAS for standardised RAG metrics; custom agents for LLM-as-a-Judge scoring per dimension |
| Observability | TruLens | Evaluation tracking, tracing, and dashboards for LLM application monitoring |
| Database | SQLite | Lightweight relational database for storing evaluation results during development |
| API Testing | Postman | Manual API testing and documentation of REST endpoints |
| Version Control | Git + GitHub | Source control and collaboration |
| Documentation | Markdown | All project documentation written in Markdown for readability and GitHub rendering |

---

## Technology Notes

### FastAPI
Chosen for its async-first design, which is important for running multiple evaluation agents in parallel. The automatic Swagger UI at `/docs` makes API testing straightforward without additional tooling.

### OpenAI API / Hugging Face
The LLM-as-a-Judge approach requires a capable language model. OpenAI's GPT models provide high-quality evaluations. Hugging Face models (e.g. Mistral, Llama) are proposed as open-source alternatives that can run locally without API costs.

### Sentence Transformers
The `all-MiniLM-L6-v2` model from the `sentence-transformers` library generates high-quality semantic embeddings for English text. It runs entirely locally, requires no API key, and is fast enough for development use.

### ChromaDB
ChromaDB is a lightweight, open-source vector database that supports persistent storage on disk. It integrates natively with LangChain and is well-suited for development and small-scale deployment. It can be replaced with a managed vector database (e.g. Pinecone, Weaviate) for production scale.

### LangChain
LangChain provides ready-made components for document loading, text splitting, embedding, vector store integration, and retrieval chains. This reduces the amount of boilerplate code needed to build the RAG pipeline.

### RAGAS
RAGAS provides standardised, research-backed metrics for evaluating RAG pipelines. Its metrics (faithfulness, answer relevancy, context precision, context recall) complement our custom LLM-as-a-Judge agents and provide a basis for comparison with published benchmarks.

### TruLens
TruLens provides observability for LLM applications, including tracing of individual evaluation runs, feedback function tracking, and a local dashboard. It will be used to monitor the performance of our evaluation agents over time.

### SQLite
SQLite is used as the development database for storing evaluation results. It requires no server setup and is suitable for local development and testing. PostgreSQL is proposed for production deployment.

---

## Technology Stack Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                       │
│                      React.js                           │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────┐
│                  BACKEND / API LAYER                    │
│                      FastAPI                            │
└──────────────────────────┬──────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  RAG PIPELINE│  │  EVALUATION  │  │   DATABASE   │
│  LangChain   │  │    AGENTS    │  │   SQLite     │
│  ChromaDB    │  │  OpenAI API  │  └──────────────┘
│  Sentence    │  │  RAGAS       │
│  Transformers│  │  TruLens     │
└──────────────┘  └──────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│               REFERENCE KNOWLEDGE BASE                   │
│          TruthfulQA · SQuAD · Custom Documents           │
│              Hugging Face datasets library               │
└──────────────────────────────────────────────────────────┘
```
