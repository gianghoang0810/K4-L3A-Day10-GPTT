from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tao bo evaluation set gom 10 cau hoi chuan tu cleaned dataframe qua 4 nhom nghiep vu."""
    if df.empty or len(df) < 4:
        raise ValueError(f"Cleaned DataFrame needs at least 4 papers to build test set, found {len(df)}")

    # Sap xep on dinh va lay toi da 10 paper dai dien
    records = df.to_dict(orient="records")
    total_target = min(10, len(records))

    # 5 dang cau hoi chuan hoa theo yeu cau bai lab:
    # 1. summary: Tom tat noi dung nghien cuu chinh
    # 2. authors: Ai la tac gia cua nghien cuu?
    # 3. date: Nghien cuu duoc cong bo vao nam/thang nao?
    # 4. category: Cong trinh nay thuoc linh vuc chuyen mon nao?
    # 5. multi_hop: Cau hoi ket hop lien nganh giua hai chu de
    question_types = [
        "summary",
        "authors",
        "date",
        "category",
        "multi_hop",
        "summary",
        "authors",
        "date",
        "category",
        "multi_hop",
    ][:total_target]

    test_set: list[dict[str, Any]] = []

    for index, q_type in enumerate(question_types):
        row = records[index % len(records)]
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        doc_ids = [paper_id]

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif q_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"])
        elif q_type == "category":
            question = f"What category does the paper '{title}' belong to?"
            ground_truth = str(row["categories_joined"])
        elif q_type == "multi_hop":
            # Cau hoi ket hop lien nganh giua 2 bai bao
            other_index = (index + 4) % len(records)
            other_row = records[other_index]
            other_title = str(other_row["title"])
            other_paper_id = str(other_row["paper_id"])
            question = f"What categories describe the research topics in '{title}' related to '{other_title}'?"
            ground_truth = str(row["categories_joined"])
            doc_ids = [paper_id, other_paper_id]
        else:
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))

        test_set.append(
            {
                "id": f"eval_{index + 1:03d}",
                "type": q_type,
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": doc_ids,
            }
        )

    out_file = Path(output_path)
    write_json(out_file, test_set)
    return test_set


class TestSet(list):
    """Wrapper cho bo test set chua danh sach cau hoi kem thuoc tinh .samples."""

    def __init__(self, samples: list[dict[str, Any]]):
        super().__init__(samples)
        self.samples = samples


def load_or_create_test_set(df: pd.DataFrame, output_path: Path | str) -> TestSet:
    """Doc file test set da co hoac sinh moi neu chua ton tai, tra ve doi tuong TestSet co thuoc tinh .samples."""
    out_file = Path(output_path)
    if out_file.exists():
        from core.utils import read_json

        samples = read_json(out_file)
    else:
        samples = build_test_set(df, out_file)
    return TestSet(samples)

