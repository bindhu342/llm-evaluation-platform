from datasets import load_dataset
from typing import Generator


def iter_squad(split: str = "validation") -> Generator[dict, None, None]:
    """
    Yields dicts normalized to the evaluation pipeline's canonical field names:
        { question, source_document, reference_answer }
    """
    ds = load_dataset("squad_v2", split=split)
    for row in ds:
        answers = row["answers"]["text"]
        if not answers:
            continue
        yield {
            "question": row["question"],
            "source_document": row["context"],
            "reference_answer": answers[0],
        }
