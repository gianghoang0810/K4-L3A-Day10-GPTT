from datetime import UTC, datetime
import pandas as pd
import pytest

from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord


def test_build_clean_dataframe_structure():
    records = [
        PaperRecord(
            paper_id="10.1234/test.001",
            title="A Great AI Paper",
            summary="This is a valid research summary exceeding thirty characters.",
            authors=["Alice Smith", "Bob Jones"],
            categories=["Computer Science", "Artificial Intelligence"],
            primary_category="Computer Science",
            published="2026-05-01",
            updated="2026-05-01",
            abs_url="https://doi.org/10.1234/test.001",
            pdf_url="",
            comment="",
        )
    ]
    run_date = datetime(2026, 7, 1, tzinfo=UTC)
    df = build_clean_dataframe(records, run_date)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["paper_id"] == "10.1234/test.001"
    assert row["age_days"] == (run_date.date() - datetime(2026, 5, 1).date()).days

    lines = row["text_for_embedding"].strip().split("\n")
    assert len(lines) == 5
    assert lines[0] == "Title: A Great AI Paper"
    assert lines[1] == "Authors: Alice Smith, Bob Jones"
    assert lines[2] == "Published: 2026-05-01"
    assert lines[3] == "Categories: Computer Science, Artificial Intelligence"
    assert lines[4].startswith("Summary:")


def test_build_clean_dataframe_deduplication():
    records = [
        PaperRecord(
            paper_id="10.1234/dup",
            title="Dup Title 1",
            summary="Valid summary content longer than 30 characters here.",
            authors=["Author One"],
            categories=["AI"],
            primary_category="AI",
            published="2026-01-01",
            updated="2026-01-01",
            abs_url="",
            pdf_url="",
            comment="",
        ),
        PaperRecord(
            paper_id="10.1234/dup",
            title="Dup Title 2",
            summary="Valid summary content longer than 30 characters here.",
            authors=["Author Two"],
            categories=["AI"],
            primary_category="AI",
            published="2026-01-01",
            updated="2026-01-01",
            abs_url="",
            pdf_url="",
            comment="",
        ),
    ]
    run_date = datetime.now(UTC)
    df = build_clean_dataframe(records, run_date)
    assert len(df) == 1
    assert df["paper_id"].iloc[0] == "10.1234/dup"
