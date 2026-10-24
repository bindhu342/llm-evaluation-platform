from typing import Generator

from datasets import load_dataset


def iter_squad(split: str = "validation") -> Generator[dict, None, None]:
    """
    Yields records normalized to the evaluation pipeline's
    canonical field names:

        {
            "question": str,
            "source_document": str,
            "reference_answer": str
        }
    """

    # SQuAD v1 dataset
    dataset = load_dataset("rajpurkar/squad", split=split)

    for row in dataset:
        answers = row.get("answers", {}).get("text", [])

        if not answers:
            continue

        yield {
            "question": row["question"],
            "source_document": row["context"],
            "reference_answer": answers[0],
        }