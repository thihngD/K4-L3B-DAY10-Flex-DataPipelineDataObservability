from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

from core.utils import write_json


def _compose_text_for_embedding(row) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Return a deterministic corrupted copy and persist its scenario log."""
    corrupted = df.copy(deep=True)
    input_rows = len(corrupted)
    columns = list(corrupted.columns)
    rng = np.random.default_rng(42)

    latest_first = corrupted.sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    drop_count = ceil(0.2 * input_rows)
    dropped = latest_first.iloc[:drop_count]
    remaining = latest_first.iloc[drop_count:].sort_values(
        "paper_id", ascending=True, kind="stable"
    ).reset_index(drop=True)
    permutation = rng.permutation(len(remaining))
    cursor = 0

    def take_positions(requested: int) -> list[int]:
        nonlocal cursor
        end = min(cursor + requested, len(permutation))
        positions = permutation[cursor:end].tolist()
        cursor = end
        return positions

    blank_positions = take_positions(3)
    noise_positions = take_positions(3)
    truncate_positions = take_positions(3)
    stale_count = ceil(0.3 * len(remaining))
    stale_positions = take_positions(stale_count)
    duplicate_positions = take_positions(2)

    def paper_ids(positions: list[int]) -> list[str]:
        return [str(remaining.at[position, "paper_id"]) for position in positions]

    for position in blank_positions:
        remaining.at[position, "summary"] = ""

    noise_token = "@#$%&*~^"
    for position in noise_positions:
        summary = str(remaining.at[position, "summary"])
        midpoint = len(summary) // 2
        remaining.at[position, "summary"] = f"{noise_token} {summary[:midpoint]} {noise_token} {summary[midpoint:]}"

    for position in truncate_positions:
        remaining.at[position, "title"] = str(remaining.at[position, "title"])[:6]

    for position in stale_positions:
        published = date.fromisoformat(str(remaining.at[position, "published"]))
        remaining.at[position, "published"] = (published - timedelta(days=400)).isoformat()
        remaining.at[position, "age_days"] = int(remaining.at[position, "age_days"]) + 400

    duplicate_rows = remaining.loc[duplicate_positions].copy()
    output = pd.concat([remaining, duplicate_rows], ignore_index=True)

    try:
        from ingestion.cleaning import compose_text_for_embedding
    except ImportError:
        compose_text_for_embedding = _compose_text_for_embedding

    output["summary_chars"] = output["summary"].map(len)
    output["text_for_embedding"] = [
        compose_text_for_embedding(row) for row in output.to_dict(orient="records")
    ]
    output = output.sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    output = output.loc[:, columns]

    scenarios = [
        {
            "name": "drop_latest_records",
            "description": "Drop the 20% most recently published records",
            "params": {"fraction": 0.2, "count": drop_count},
            "affected_rows": len(dropped),
            "affected_paper_ids": dropped["paper_id"].astype(str).tolist(),
        },
        {
            "name": "blank_summary",
            "description": "Set summary to empty string",
            "params": {"count": len(blank_positions)},
            "affected_rows": len(blank_positions),
            "affected_paper_ids": paper_ids(blank_positions),
        },
        {
            "name": "inject_noise",
            "description": "Insert noise token into summary",
            "params": {"count": len(noise_positions), "noise_token": noise_token},
            "affected_rows": len(noise_positions),
            "affected_paper_ids": paper_ids(noise_positions),
        },
        {
            "name": "truncate_title",
            "description": "Truncate title to 6 characters",
            "params": {"count": len(truncate_positions), "max_len": 6},
            "affected_rows": len(truncate_positions),
            "affected_paper_ids": paper_ids(truncate_positions),
        },
        {
            "name": "stale_date",
            "description": "Shift published date 400 days into the past",
            "params": {"count": len(stale_positions), "shift_days": 400},
            "affected_rows": len(stale_positions),
            "affected_paper_ids": paper_ids(stale_positions),
        },
        {
            "name": "duplicate_rows",
            "description": "Append exact duplicate rows",
            "params": {"count": len(duplicate_positions)},
            "affected_rows": len(duplicate_positions),
            "affected_paper_ids": paper_ids(duplicate_positions),
        },
    ]
    log = {
        "seed": 42,
        "input_rows": input_rows,
        "output_rows": len(output),
        "generated_at": datetime.now(UTC).isoformat(),
        "scenarios": scenarios,
    }
    write_json(Path(output_log_path), log)
    print(f"[corruption] input={input_rows} output={len(output)} scenarios=6")
    return output
