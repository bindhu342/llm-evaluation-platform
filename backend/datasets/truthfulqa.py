from datasets import load_dataset
from typing import Generator


def iter_truthfulqa(split: str = "validation") -> Generator[dict, None, None]:
    """
    Yields dicts normalized to the evaluation pipeline's canonical field names:
        { question, reference_answer }
    """
    ds = load_dataset("truthful_qa", "generation", split=split)
    for row in ds:
        yield {
            "question": row["question"],
            "reference_answer": row["best_answer"],
        }
