from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Tạo bộ benchmark test set 10 câu hỏi theo chuẩn Contract C3.
    
    Quy tắc nghiệp vụ:
    1. Lọc pool các bài báo không chứa dấu nháy đơn trong title và summary không rỗng.
    2. Sắp xếp pool theo paper_id tăng dần để đảm bảo tính tất định (deterministic).
    3. Chọn 10 bài đại diện tại vị trí round(i * (len(pool) - 1) / 9) với i = 0..9.
    4. Phân bổ đúng 4 loại câu hỏi: 3 summary, 3 authors, 2 date, 2 categories.
    5. Định dạng title trong nháy đơn để khớp bộ định tuyến (router) của retrieval/qa.py.
    6. Lưu ra file JSON tại output_path và trả về list dict.
    """
    # 1. Lọc pool hợp lệ
    pool = df[~df["title"].str.contains("'") & (df["summary"].str.len() > 0)].sort_values("paper_id").reset_index(drop=True)
    if len(pool) < 10:
        raise ValueError(f"Need at least 10 valid papers for test set, got {len(pool)}")

    # 2. Phân bổ 4 nhóm câu hỏi cố định theo Contract C3-§4
    question_types = [
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
    ]

    test_items: list[dict[str, Any]] = []

    for i in range(10):
        # Chọn paper theo công thức tất định
        idx = round(i * (len(pool) - 1) / 9)
        row = pool.iloc[idx]
        title = str(row["title"])
        qtype = question_types[i]

        if qtype == "summary":
            question = f"What is the main contribution of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif qtype == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif qtype == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"])
        elif qtype == "categories":
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(row["categories_joined"])
        else:
            raise ValueError(f"Unknown question type: {qtype}")

        test_items.append({
            "id": f"q{i + 1:02d}",
            "question_type": qtype,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [str(row["paper_id"])],
        })

    # Ghi file JSON ra output_path
    write_json(Path(output_path), test_items)
    return test_items
