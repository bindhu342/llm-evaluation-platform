from typing import Generator

from datasets import load_dataset


def iter_truthfulqa(split: str = "validation") -> Generator[dict, None, None]:
    """
    Yields records normalized to the evaluation pipeline's
    canonical field names:

        {
            "question": str,
            "reference_answer": str
        }
    """

    dataset = load_dataset(
        "truthfulqa/truthful_qa",
        "generation",
        split=split,
    )

    for row in dataset:
        yield {
            "question": row["question"],
            "reference_answer": row["best_answer"],
        }