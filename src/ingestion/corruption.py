from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Gia lap 6 dang data corruption thuc te de thu nghiem kha nang phat hien cua Quality Gate."""
    corrupted = df.copy().reset_index(drop=True)
    total_orig = len(corrupted)

    log_entries: list[dict[str, Any]] = []

    # 1. Drop latest records (bo 20% ban ghi moi nhat)
    drop_count = max(1, int(total_orig * 0.20))
    dropped_ids = list(corrupted.iloc[:drop_count]["paper_id"])
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)
    log_entries.append(
        {
            "scenario": "drop_latest",
            "description": f"Dropped {drop_count} latest records (20%)",
            "affected_count": drop_count,
            "affected_ids": dropped_ids,
        }
    )

    # 2. Blank summary (xoa trang phan tom tat)
    blank_indices = [0, 1] if len(corrupted) > 2 else [0]
    blank_ids = []
    for idx in blank_indices:
        corrupted.loc[idx, "summary"] = ""
        corrupted.loc[idx, "summary_chars"] = 0
        blank_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "scenario": "blank_summary",
            "description": "Cleared summary content to empty string",
            "affected_count": len(blank_indices),
            "affected_ids": blank_ids,
        }
    )

    # 3. Inject noise (chen ky tu rac vao tom tat)
    noise_indices = [2, 3] if len(corrupted) > 4 else []
    noise_ids = []
    for idx in noise_indices:
        corrupted.loc[idx, "summary"] = "@@CORRUPTED_NOISE_GARBAGE_TEXT@@ " + str(corrupted.loc[idx, "summary"])
        corrupted.loc[idx, "summary_chars"] = len(str(corrupted.loc[idx, "summary"]))
        noise_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "scenario": "inject_noise",
            "description": "Injected random text noise into summary",
            "affected_count": len(noise_indices),
            "affected_ids": noise_ids,
        }
    )

    # 4. Truncate title (cat ngan tieu de xuong duoi 8 ky tu)
    truncate_indices = [4, 5] if len(corrupted) > 6 else []
    truncate_ids = []
    for idx in truncate_indices:
        corrupted.loc[idx, "title"] = "Short"
        truncate_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated title to less than 8 characters",
            "affected_count": len(truncate_indices),
            "affected_ids": truncate_ids,
        }
    )

    # 5. Stale date (doi ngay xuat ban ve 5 nam truoc de vi pham Freshness SLA)
    stale_count = min(10, len(corrupted))
    stale_ids = []
    for idx in range(stale_count):
        cur_pub = str(corrupted.loc[idx, "published"])
        try:
            cur_dt = datetime.strptime(cur_pub[:10], "%Y-%m-%d")
            stale_dt = cur_dt - timedelta(days=5 * 365)
            corrupted.loc[idx, "published"] = stale_dt.strftime("%Y-%m-%d")
            corrupted.loc[idx, "age_days"] = int(corrupted.loc[idx, "age_days"]) + 5 * 365
        except Exception:
            corrupted.loc[idx, "published"] = "2020-01-01"
            corrupted.loc[idx, "age_days"] = 1825
        stale_ids.append(str(corrupted.loc[idx, "paper_id"]))
    log_entries.append(
        {
            "scenario": "stale_date",
            "description": "Pushed published date back 5 years to violate freshness SLA",
            "affected_count": stale_count,
            "affected_ids": stale_ids,
        }
    )

    # 6. Duplicate rows (nhan doi dong de gay loi uniqueness va giu nguyen tong so 24 dong)
    dup_slice = corrupted.iloc[:drop_count].copy()
    dup_ids = list(dup_slice["paper_id"])
    corrupted = pd.concat([corrupted, dup_slice], ignore_index=True)
    log_entries.append(
        {
            "scenario": "duplicate_rows",
            "description": "Duplicated rows to violate uniqueness expectations",
            "affected_count": len(dup_slice),
            "affected_ids": dup_ids,
        }
    )

    # 7. Rebuild text_for_embedding tu du lieu da bi lam ban
    corrupted["text_for_embedding"] = (
        "Title: "
        + corrupted["title"].astype(str)
        + "\nAuthors: "
        + corrupted["authors_joined"].astype(str)
        + "\nPublished: "
        + corrupted["published"].astype(str)
        + "\nCategories: "
        + corrupted["categories_joined"].astype(str)
        + "\nSummary: "
        + corrupted["summary"].astype(str)
    )

    # 8. Ghi log chi tiet
    log_payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "original_rows": total_orig,
        "corrupted_rows": len(corrupted),
        "scenarios": log_entries,
    }
    write_json(Path(output_log_path), log_payload)

    return corrupted
