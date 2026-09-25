from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tao bo evaluation set gom 10 cau hoi thuoc 4 loai tu cleaned dataframe."""
    if len(df) < 5:
        raise ValueError(f"Cleaned DataFrame has only {len(df)} rows, need at least 5 to build evaluation set.")

    papers = df.to_dict(orient="records")
    n_papers = len(papers)
    test_set: list[dict[str, Any]] = []

    # 1. Summary questions (3 questions)
    for i in range(3):
        p = papers[i % n_papers]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1}",
                "question_type": "summary",
                "question": f"What is the summary of the paper '{p['title']}'?",
                "ground_truth": first_sentence(p["summary"]),
                "ground_truth_doc_ids": [p["paper_id"]],
            }
        )

    # 2. Authors questions (3 questions)
    for i in range(3):
        p = papers[(i + 3) % n_papers]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1}",
                "question_type": "authors",
                "question": f"Who authored the paper '{p['title']}'?",
                "ground_truth": p["authors_joined"],
                "ground_truth_doc_ids": [p["paper_id"]],
            }
        )

    # 3. Date questions (2 questions)
    for i in range(2):
        p = papers[(i + 6) % n_papers]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1}",
                "question_type": "date",
                "question": f"When was the study '{p['title']}' published?",
                "ground_truth": p["published"],
                "ground_truth_doc_ids": [p["paper_id"]],
            }
        )

    # 4. Categories questions (2 questions)
    for i in range(2):
        p = papers[(i + 8) % n_papers]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1}",
                "question_type": "categories",
                "question": f"What categories describe the paper '{p['title']}'?",
                "ground_truth": p["categories_joined"],
                "ground_truth_doc_ids": [p["paper_id"]],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
