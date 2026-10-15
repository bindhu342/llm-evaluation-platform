# Milestone 1 Research Document

**Project:** Robust LLM Response Evaluation Platform  
**Milestone:** M1 — Research Foundation  
**Date:** August 2026

---

## 1. LLM Evaluation

### What it is

LLM evaluation is the systematic process of measuring the quality of outputs produced by large language models. It covers multiple dimensions, including factual correctness, relevance to the question, absence of hallucinations, and completeness of the answer. Evaluation can be performed by humans, automated metrics, or other LLMs acting as judges.

### Why it matters

Without structured evaluation, there is no reliable way to know whether an LLM's response is trustworthy or useful. Traditional NLP metrics such as BLEU and ROUGE measure surface-level text overlap and may correlate poorly with human judgments of quality. A dedicated evaluation framework is essential for production LLM applications.

### How it will be used in our system

Our platform is an LLM evaluation system. Every component—the evaluation agents, scoring module, and RAG pipeline—exists to produce a structured, multidimensional quality assessment of an AI-generated response. We adopt an LLM-as-a-Judge approach in which a capable model scores each quality dimension independently.

---

## 2. Hallucination Detection

### What it is

Hallucination in LLMs refers to the generation of content that is factually incorrect, fabricated, or unsupported by the provided source. Hallucinations can be intrinsic, meaning they contradict the source, or extrinsic, meaning they introduce information that is not present in the source. It is one of the most critical failure modes of current LLMs.

### Why it matters

A response that sounds confident but contains fabricated facts can be dangerous in real-world applications such as medical, legal, and financial services. Detecting hallucinations is a primary objective of this platform.

### How it will be used in our system

A dedicated Hallucination Detection Agent is included in the proposed architecture. It compares the LLM response against retrieved reference context and assigns a hallucination score from 0.0 (no detected hallucination) to 1.0 (maximum detected hallucination). The final scoring formula inverts this score so that lower hallucination scores improve the overall result.

---

## 3. Factuality

### What it is

Factuality measures whether the claims made in a response are objectively true and verifiable against a known reference. It is closely related to hallucination detection but focuses specifically on factual correctness rather than whether claims are grounded in a particular document.

### Why it matters

A response can be grounded in a retrieved document but still contain factual errors if the model misinterprets the source. Factuality evaluation adds another layer of quality assurance beyond checking whether the response is supported by the provided context.

### How it will be used in our system

The Accuracy Agent evaluates factual correctness by comparing the response against a reference answer or retrieved context. Ground-truth answers from datasets such as TruthfulQA and SQuAD can provide factual baselines for evaluating the system.

---

## 4. Faithfulness

### What it is

Faithfulness measures whether a response is consistent with and supported by the provided source context. A faithful response does not introduce unsupported information beyond what the context contains, even if that information might be factually correct according to general knowledge.

### Why it matters

In Retrieval-Augmented Generation (RAG) systems, faithfulness is critical. If the model retrieves relevant documents but then ignores or contradicts them, the retrieval step provides little benefit. Faithfulness is an important metric in RAG evaluation frameworks such as RAGAS.

### How it will be used in our system

Faithfulness is evaluated as part of the Hallucination Detection Agent. Retrieved context is passed alongside the response, and the agent checks whether the response's claims are supported by that context. A response that introduces unsupported claims receives a higher hallucination score.

---

## 5. Relevance

### What it is

Relevance measures how well a response addresses the specific question or prompt that was asked. A response can be factually correct but still irrelevant if it answers a different question or drifts off-topic.

### Why it matters

Relevance is a fundamental quality dimension. An irrelevant response fails to satisfy the user's needs regardless of its factual accuracy or completeness.

### How it will be used in our system

The Relevance Agent scores the semantic alignment between the input prompt and the LLM response using LLM-as-a-Judge prompting. It assigns a score from 0.0 (completely irrelevant) to 1.0 (highly relevant) and contributes 25% to the final weighted score.

---

## 6. Completeness

### What it is

Completeness measures whether a response addresses all important aspects of the question. A response may be relevant and accurate but still incomplete if it answers only part of a multi-part question or omits essential information.

### Why it matters

Incomplete responses can mislead users by omitting important details. This is especially significant for complex or multi-part questions where a partial answer may not meet the user's needs.

### How it will be used in our system

The Completeness Agent evaluates whether the response covers the key aspects of the prompt. It contributes 20% to the final weighted score. The weight is slightly lower than accuracy and relevance because partial answers may be acceptable in some contexts.

---

## 7. RAG (Retrieval-Augmented Generation)

### What it is

Retrieval-Augmented Generation (RAG) is an architecture that combines a retrieval system with a generative LLM. The system retrieves relevant documents from a knowledge base and provides them as context to support generation or evaluation. This helps ground the model's reasoning in reference material rather than relying solely on its internal knowledge.

### Why it matters

RAG allows evaluation to be grounded in factual reference material. Without retrieved context, evaluation agents may rely heavily on an LLM's internal knowledge, which may be outdated or incorrect. RAG-based evaluation can improve grounding and make evaluations more explainable.

### How it will be used in our system

The proposed RAG pipeline retrieves relevant reference documents from a vector store, such as ChromaDB, and passes them as context to the evaluation agents. This provides grounding when evaluating accuracy and hallucination. The pipeline follows the standard process: ingest, chunk, embed, store, and retrieve.

---

## 8. Embeddings

### What it is

Embeddings are dense vector representations of text that capture semantic meaning. Texts with similar meanings can have vectors that are close together in vector space, enabling semantic similarity search. Embedding models map text into a high-dimensional space where semantic relationships are represented numerically.

### Why it matters

Embeddings are a foundation of the retrieval pipeline. Without suitable embeddings, the system may fail to find relevant reference documents for a given query. Embedding quality affects the relevance of retrieved context, which in turn affects evaluation quality.

### How it will be used in our system

We propose using `sentence-transformers`, specifically `all-MiniLM-L6-v2`, to generate embeddings locally. This model is lightweight and can generate embeddings without requiring a separate embedding API key. Document chunks and queries are embedded using the same model to enable similarity-based retrieval.

---

## 9. Vector Search

### What it is

Vector search, also called semantic search or approximate nearest-neighbor search, finds documents that are semantically similar to a query by comparing embedding vectors using measures such as cosine similarity or dot product. Unlike keyword search, vector search can identify relevant documents even when they do not share exact words with the query.

### Why it matters

Vector search helps retrieve relevant reference context even when a query and a reference document use different terminology. This is essential for RAG-based evaluation, where the question and supporting documents may express the same concept in different ways.

### How it will be used in our system

We propose using ChromaDB as the vector store. ChromaDB is an open-source vector database that supports persistent storage and can integrate with common AI development frameworks. Given an evaluation prompt, the retriever performs a similarity search and returns relevant document chunks as context for the evaluation agents.

---

## 10. LLM-as-a-Judge

### What it is

LLM-as-a-Judge is an evaluation approach in which a capable LLM is prompted to assess the quality of another LLM's response. The judge receives an evaluation rubric and produces numerical scores, explanations, or qualitative verdicts.

### Why it matters

Traditional metrics such as BLEU and ROUGE measure surface-level text overlap and may not reflect human judgments of response quality. LLM-as-a-Judge can evaluate more nuanced dimensions, such as relevance, factual correctness, and completeness, that are difficult to measure through simple string matching.

### How it will be used in our system

All four evaluation agents—Relevance, Accuracy, Hallucination, and Completeness—use LLM-as-a-Judge prompting. Each agent applies a specific scoring rubric and produces a score between 0.0 and 1.0, together with its evaluation reasoning where supported. The judge model can be configured according to the project's available model provider.

---

## 11. RAGAS

### What it is

RAGAS (Retrieval-Augmented Generation Assessment) is an open-source framework designed to evaluate RAG pipelines. It provides metrics such as faithfulness, answer relevancy, context precision, and context recall. These metrics help assess different aspects of retrieval and generation quality.

### Why it matters

RAGAS provides a well-established set of evaluation metrics that align with several of our system's evaluation dimensions. Its faithfulness metric is relevant to hallucination detection, while answer relevancy is relevant to the Relevance Agent.

### How it will be used in our system

RAGAS is considered for possible integration in a later milestone to complement our custom evaluation agents with standardized metrics. Research into RAGAS informed the design of our scoring rubric and the selection of evaluation dimensions.

---

## 12. TruLens

### What it is

TruLens is an open-source library for evaluating and tracking LLM applications. It provides feedback functions for measuring properties such as groundedness and relevance, along with tools for observing and tracing application runs.

### Why it matters

Observability tools can help developers monitor evaluation quality over time, investigate individual runs, and compare results across different model versions or configurations.

### How it will be used in our system

TruLens is considered for possible integration in a later milestone, primarily for observability and evaluation tracking. Such integration could help identify cases where evaluation agents disagree or produce unexpected scores.

---

## 13. TruthfulQA

### What it is

TruthfulQA is a benchmark dataset designed to test whether language models generate truthful answers to questions that target common misconceptions. The benchmark includes questions for which models may produce confident but incorrect responses.

### Why it matters

TruthfulQA is relevant to hallucination detection and factual accuracy evaluation. It provides a benchmark for examining whether models and evaluation agents can identify common forms of false or misleading answers.

### How it will be used in our system

TruthfulQA can be loaded through the Hugging Face `datasets` library and used to benchmark the evaluation pipeline. Its questions and reference information can help assess the behavior of the Accuracy and Hallucination Detection Agents.

---

## 14. SQuAD

### What it is

SQuAD (Stanford Question Answering Dataset) is a reading-comprehension dataset containing questions based on Wikipedia passages, with answers generally represented as spans from those passages. SQuAD v2 also includes unanswerable questions to test whether a system can recognize when the provided context does not contain an answer.

### Why it matters

SQuAD provides question-context-answer examples that are useful for evaluating accuracy and hallucination detection. Because the supporting passage is available, it enables grounded evaluation of whether a response is supported by its source.

### How it will be used in our system

SQuAD can be loaded through the Hugging Face `datasets` library. The Wikipedia passage serves as the reference context, the question serves as the evaluation prompt, and the annotated answer serves as a reference answer. SQuAD v2 can also be used to test whether the system recognizes questions that cannot be answered from the supplied context.

---

## 15. Weighted Scoring and Verdict Generation

### What it is

Weighted scoring combines multiple evaluation dimensions into a single overall score. Each dimension receives a weight based on its importance, and the weighted values are combined to calculate the final score.

### Why it matters

A single evaluation metric cannot capture every aspect of response quality. Weighted scoring allows the platform to account for relevance, factual accuracy, hallucination risk, and completeness in a consistent way.

### How it will be used in our system

The proposed scoring formula assigns the following weights:

- Relevance: 25%
- Accuracy: 30%
- Hallucination-free score: 25%
- Completeness: 20%

The final score is calculated as:

**Final Score = (0.25 × Relevance) + (0.30 × Accuracy) + (0.25 × Hallucination-Free Score) + (0.20 × Completeness)**

The hallucination-free score is calculated by inverting the hallucination score when that score represents hallucination severity:

**Hallucination-Free Score = 1 − Hallucination Score**

The resulting score can be mapped to verdict categories such as Excellent, Good, Fair, or Poor, using the thresholds configured in the application. The implementation's actual thresholds should remain consistent with the project's scoring code.

---

## 16. Conclusion

This research establishes the theoretical foundation for the Robust LLM Response Evaluation Platform. It examines the main concepts behind response evaluation, including hallucination detection, factuality, faithfulness, relevance, completeness, retrieval-augmented generation, embeddings, vector search, and LLM-as-a-Judge.

It also reviews established evaluation resources and frameworks, including RAGAS, TruLens, TruthfulQA, and SQuAD. These concepts inform the design of a platform that evaluates AI-generated responses across multiple dimensions and provides scores, verdicts, and supporting reasoning rather than relying on a single quality metric.

The research serves as the foundation for the subsequent milestones involving implementation, dashboard development, batch evaluation, report generation, and end-to-end testing.
