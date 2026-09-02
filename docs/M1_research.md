# Milestone 1 Research Document

**Project:** Robust LLM Response Evaluation Platform  
**Milestone:** M1 — Research Foundation  
**Date:** August 2026

---

## 1. LLM Evaluation

### What it is
LLM evaluation is the systematic process of measuring the quality of outputs produced by large language models. It covers multiple dimensions including factual correctness, relevance to the question, absence of hallucinations, and completeness of the answer. Evaluation can be performed by humans, by automated metrics, or by other LLMs acting as judges.

### Why it matters
Without structured evaluation, there is no reliable way to know whether an LLM's response is trustworthy or useful. Traditional NLP metrics such as BLEU and ROUGE measure surface-level text overlap and correlate poorly with human judgements of quality. A dedicated evaluation framework is essential for any production LLM application.

### How it will be used in our system
Our platform is an LLM evaluation system. Every component — the evaluation agents, the scoring module, the RAG pipeline — exists to produce a structured, multi-dimensional quality assessment of a given LLM response. We adopt an LLM-as-a-Judge approach where a capable model scores each quality dimension independently.

---

## 2. Hallucination Detection

### What it is
Hallucination in LLMs refers to the generation of content that is factually incorrect, fabricated, or not grounded in any provided source. Hallucinations can be intrinsic (contradicting the source) or extrinsic (introducing information not present in the source). It is one of the most critical failure modes of current LLMs.

### Why it matters
A response that sounds confident but contains fabricated facts is dangerous in real-world applications such as medical, legal, or financial advice. Detecting hallucinations is a primary objective of this platform.

### How it will be used in our system
A dedicated Hallucination Detection Agent is proposed in the architecture. It compares the LLM response against retrieved reference context and assigns a hallucination score from 0.0 (no hallucination) to 1.0 (fully hallucinated). The final scoring formula inverts this score so that lower hallucination improves the overall result.

---

## 3. Factuality

### What it is
Factuality measures whether the claims made in a response are objectively true and verifiable against a known reference. It is closely related to hallucination but focuses specifically on factual correctness rather than grounding in a provided document.

### Why it matters
A response can be grounded in a retrieved document but still contain factual errors if the model misinterprets the source. Factuality evaluation adds an additional layer of quality assurance beyond hallucination detection.

### How it will be used in our system
The Accuracy Agent evaluates factual correctness by comparing the response against a reference answer or retrieved context. Ground truth answers from TruthfulQA and SQuAD provide a factual baseline for this comparison.

---

## 4. Faithfulness

### What it is
Faithfulness measures whether a response is consistent with and fully supported by the provided source context. A faithful response does not introduce information beyond what the context contains, even if that information might be factually true from general knowledge.

### Why it matters
In RAG-based systems, faithfulness is critical. If the model retrieves relevant documents but then ignores or contradicts them, the retrieval step provides no safety benefit. Faithfulness is a core metric in the RAGAS framework.

### How it will be used in our system
Faithfulness is evaluated as part of the Hallucination Detection Agent. Retrieved context is passed alongside the response, and the agent checks whether the response stays within the bounds of that context. A response that introduces claims not present in the retrieved documents receives a higher hallucination score.

---

## 5. Relevance

### What it is
Relevance measures how well the response addresses the specific question or prompt that was asked. A response can be factually correct but still irrelevant if it answers a different question or drifts off-topic.

### Why it matters
Relevance is the most fundamental quality dimension. An irrelevant response fails the user regardless of its factual accuracy or completeness.

### How it will be used in our system
The Relevance Agent scores the semantic alignment between the input prompt and the LLM response using LLM-as-a-Judge prompting. It assigns a score from 0.0 (completely irrelevant) to 1.0 (perfectly relevant) and contributes 25% to the final weighted score.

---

## 6. Completeness

### What it is
Completeness measures whether the response addresses all aspects of the question. A response may be relevant and accurate but still incomplete if it only partially answers a multi-part question or omits important information.

### Why it matters
Incomplete responses can mislead users by omitting critical information. This is especially important for complex or multi-part questions where a partial answer may be worse than no answer.

### How it will be used in our system
The Completeness Agent evaluates whether the response covers all key aspects of the prompt. It contributes 20% to the final weighted score. The weight is slightly lower than accuracy and relevance because partial answers are acceptable in some contexts.

---

## 7. RAG (Retrieval-Augmented Generation)

### What it is
Retrieval-Augmented Generation (RAG) is an architecture that combines a retrieval system with a generative LLM. Before generating or evaluating a response, the system retrieves relevant documents from a knowledge base and provides them as context. This grounds the model's reasoning in real reference material rather than relying solely on parametric knowledge.

### Why it matters
RAG allows evaluation to be grounded in factual reference material. Without retrieved context, evaluation agents must rely entirely on the LLM's internal knowledge, which may be outdated or incorrect. RAG-based evaluation is more reliable and explainable.

### How it will be used in our system
The proposed RAG pipeline retrieves relevant reference documents from a vector store (ChromaDB) and passes them as context to the evaluation agents. This gives agents factual grounding when scoring accuracy and hallucination. The pipeline follows the standard pattern: ingest → chunk → embed → store → retrieve.

---

## 8. Embeddings

### What it is
Embeddings are dense vector representations of text that capture semantic meaning. Similar texts produce vectors that are close together in vector space, enabling semantic similarity search. Embedding models are trained to map text into a high-dimensional space where semantic relationships are preserved.

### Why it matters
Embeddings are the foundation of the retrieval pipeline. Without good embeddings, the system cannot find relevant reference documents for a given query. The quality of embeddings directly affects the quality of retrieved context, which in turn affects evaluation accuracy.

### How it will be used in our system
We propose using `sentence-transformers` (specifically `all-MiniLM-L6-v2`) to generate embeddings locally. This model is lightweight, runs without an API key, and produces good-quality semantic embeddings for English text. Document chunks and queries are both embedded using the same model to enable cosine similarity search.

---

## 9. Vector Search

### What it is
Vector search (also called semantic search or approximate nearest neighbour search) finds the most semantically similar documents to a query by comparing embedding vectors using distance metrics such as cosine similarity or dot product. Unlike keyword search, vector search finds relevant documents even when they share no exact words with the query.

### Why it matters
Vector search enables the retrieval of relevant reference context even when the query does not share exact keywords with the documents. This is essential for robust RAG-based evaluation where the question and the reference document may use different terminology.

### How it will be used in our system
We propose using ChromaDB as the vector store. ChromaDB is a lightweight, open-source vector database that supports persistent storage and integrates well with LangChain. Given a query (the evaluation prompt), the retriever performs a similarity search and returns the top-k most relevant document chunks as context for the evaluation agents.

---

## 10. LLM-as-a-Judge

### What it is
LLM-as-a-Judge is an evaluation approach where a capable LLM (the "judge") is prompted to assess the quality of another LLM's response. The judge is given a rubric and asked to produce a numerical score or qualitative verdict. Research has shown that strong LLMs such as GPT-4 can produce evaluations that correlate well with human judgements.

### Why it matters
Traditional metrics like BLEU and ROUGE measure surface-level text overlap and correlate poorly with human quality judgements. LLM-as-a-Judge produces more nuanced, human-aligned evaluations and can assess dimensions like relevance and completeness that are impossible to measure with string-matching metrics.

### How it will be used in our system
All four evaluation agents (Relevance, Accuracy, Hallucination, Completeness) will use LLM-as-a-Judge prompting. Each agent sends a carefully crafted prompt to the LLM with a specific scoring rubric and parses a 0.0–1.0 score from the response. The judge model will be configurable (OpenAI API or Hugging Face model).

---

## 11. RAGAS

### What it is
RAGAS (Retrieval-Augmented Generation Assessment) is an open-source framework specifically designed to evaluate RAG pipelines. It provides standardised metrics including faithfulness, answer relevancy, context precision, and context recall. RAGAS uses LLM-as-a-Judge internally to compute these metrics without requiring human-annotated labels.

### Why it matters
RAGAS provides a well-established, research-backed set of metrics that align closely with our evaluation dimensions. Its faithfulness metric directly corresponds to our hallucination detection goal, and its answer relevancy metric corresponds to our relevance agent.

### How it will be used in our system
RAGAS is proposed for integration in a later milestone to complement our custom evaluation agents with standardised, comparable metrics. Studying RAGAS informed the design of our scoring rubric and the choice of evaluation dimensions.

---

## 12. TruLens

### What it is
TruLens is an open-source library for evaluating and tracking LLM applications. It provides feedback functions for measuring groundedness, answer relevance, and context relevance, and includes a dashboard for observability and tracing of LLM application runs.

### Why it matters
TruLens provides observability capabilities that allow developers to monitor evaluation quality over time, debug individual evaluation runs, and track performance across different model versions or configurations.

### How it will be used in our system
TruLens is proposed for integration in a later milestone, primarily for observability and evaluation tracking. It will allow us to monitor the performance of our evaluation agents over time and identify cases where the agents disagree or produce unexpected scores.

---

## 13. TruthfulQA

### What it is
TruthfulQA is a benchmark dataset of 817 questions designed to test whether LLMs generate truthful answers. The questions are crafted to target common misconceptions and areas where LLMs tend to produce confident but false answers. Each question has a known correct answer and a set of known incorrect answers.

### Why it matters
TruthfulQA is directly relevant to our hallucination and accuracy evaluation goals. It provides a standardised set of questions with known correct answers, making it ideal for benchmarking our evaluation agents.

### How it will be used in our system
TruthfulQA will be loaded via the Hugging Face `datasets` library and used to populate the reference knowledge base. Question-answer pairs from TruthfulQA will serve as ground truth for benchmarking the accuracy and hallucination agents.

---

## 14. SQuAD

### What it is
SQuAD (Stanford Question Answering Dataset) is a reading comprehension dataset where questions are posed about Wikipedia passages and answers are extractive spans from those passages. SQuAD v2 adds unanswerable questions to test whether models can recognise when a question cannot be answered from the given context.

### Why it matters
SQuAD provides question-context-answer triples, which are ideal for testing our accuracy and hallucination agents because both the correct answer and its source context are known. This allows grounded evaluation where the agent can verify whether the response is supported by the context.

### How it will be used in our system
SQuAD v2 will be loaded via the Hugging Face `datasets` library. The Wikipedia passage serves as the reference context for the RAG pipeline, the question serves as the evaluation prompt, and the extractive answer serves as the ground truth. This provides a rich, grounded benchmark for the full evaluation pipeline.
