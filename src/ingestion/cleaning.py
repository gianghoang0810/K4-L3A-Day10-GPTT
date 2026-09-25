from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Lam sach danh sach PaperRecord thanh pandas DataFrame san sang de nhung vector."""
    if isinstance(run_date, datetime):
        run_date_val = run_date.date()
    elif hasattr(run_date, "date"):
        run_date_val = run_date.date()
    else:
        run_date_val = run_date

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for r in records:
        pid = str(r.paper_id).strip()
        if not pid or pid in seen_ids:
            continue
        seen_ids.add(pid)

        title = normalize_whitespace(str(r.title or ""))
        summary = normalize_whitespace(str(r.summary or ""))

        # Xu ly danh sach tac gia
        authors = [normalize_whitespace(str(a)) for a in r.authors if str(a).strip()]
        if not authors:
            authors = ["Unknown Author"]
        authors_joined = compact_join(authors, sep=", ")

        # Xu ly linh vuc / chuyen nganh
        categories = [normalize_whitespace(str(c)) for c in r.categories if str(c).strip()]
        if not categories:
            categories = ["General"]
        categories_joined = compact_join(categories, sep=", ")
        primary_category = normalize_whitespace(str(r.primary_category)) if r.primary_category else categories[0]

        published = str(r.published or "").strip()
        updated = str(r.updated or "").strip() or published

        # Tinh toan tuoi doi ban ghi (age_days)
        try:
            pub_date_val = datetime.strptime(published[:10], "%Y-%m-%d").date()
            age_days = (run_date_val - pub_date_val).days
        except Exception:
            age_days = 0

        summary_chars = len(summary)

        # Cau truc 5 phan bat buoc cho text_for_embedding
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": pid,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": str(r.abs_url or ""),
                "pdf_url": str(r.pdf_url or ""),
                "comment": str(r.comment or ""),
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        # Loc bo cac ban ghi khong hop le (rong paper_id hoac title)
        df = df[df["paper_id"].str.len() > 0]
        df = df[df["title"].str.len() > 0]
        # Sap xep theo thoi gian xuat ban moi nhat
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
