from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh danh sach PaperRecord chuan hoa."""
    if not isinstance(payload, dict):
        return []

    items = []
    if "message" in payload and isinstance(payload["message"], dict):
        items = payload["message"].get("items", [])
    elif "items" in payload:
        items = payload.get("items", [])

    records: list[PaperRecord] = []
    for item in items:
        doi = str(item.get("DOI", "")).strip()
        if not doi:
            continue

        # Title
        raw_title = item.get("title", "")
        if isinstance(raw_title, list):
            title_str = raw_title[0] if raw_title else ""
        else:
            title_str = str(raw_title)
        title = normalize_whitespace(title_str)
        if not title:
            title = f"Paper {doi}"

        # Abstract / summary: loai bo the XML/HTML (nhu <jats:p>)
        raw_abstract = str(item.get("abstract", "") or "")
        cleaned_abstract = re.sub(r"<[^>]+>", " ", raw_abstract)
        summary = normalize_whitespace(cleaned_abstract)

        # Authors
        authors: list[str] = []
        for author in item.get("author", []):
            if isinstance(author, dict):
                given = author.get("given", "").strip()
                family = author.get("family", "").strip()
                name = author.get("name", "").strip()
                if given and family:
                    full_name = f"{given} {family}".strip()
                elif family:
                    full_name = family
                elif given:
                    full_name = given
                elif name:
                    full_name = name
                else:
                    full_name = ""
                if full_name:
                    authors.append(full_name)
            elif isinstance(author, str) and author.strip():
                authors.append(author.strip())
        if not authors:
            authors = ["Unknown Author"]

        # Categories / Subjects
        categories: list[str] = []
        for cat in item.get("subject", []):
            if cat and str(cat).strip():
                categories.append(normalize_whitespace(str(cat)))
        if not categories:
            categories = ["Computer Science"]
        primary_category = categories[0]

        # Published date: dinh dang YYYY-MM-DD
        date_parts = item.get("published", {}).get("date-parts", [[]])
        published = ""
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            if len(parts) >= 3:
                published = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            elif len(parts) == 2:
                published = f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
            elif len(parts) == 1:
                published = f"{int(parts[0]):04d}-01-01"

        if not published:
            created_dt = item.get("created", {}).get("date-time", "")
            if created_dt and len(created_dt) >= 10:
                published = created_dt[:10]
            else:
                published = "2026-01-01"

        # Updated date
        updated = ""
        updated_parts = item.get("updated", {}).get("date-parts", [[]])
        if updated_parts and updated_parts[0]:
            parts = updated_parts[0]
            if len(parts) >= 3:
                updated = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            elif len(parts) == 2:
                updated = f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
            elif len(parts) == 1:
                updated = f"{int(parts[0]):04d}-01-01"
        if not updated:
            updated = published

        # URLs
        url = item.get("URL", f"https://doi.org/{doi}")
        abs_url = url
        pdf_url = url
        comment = f"Crossref record {doi}"

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API (kem retry) hoac doc local snapshot fallback."""
    payload: dict | None = None

    if settings.refresh_source:
        import time
        import requests

        url = "https://api.crossref.org/works"
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        headers = {
            "User-Agent": "Day10Lab/1.0 (mailto:student@vinuni.edu.vn)"
        }
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=15)
                if response.status_code == 200:
                    payload = response.json()
                    write_json(settings.paths.raw_api_response, payload)
                    break
                elif response.status_code in {429, 503, 504}:
                    time.sleep(1.5 * (attempt + 1))
            except Exception:
                if attempt == 2:
                    break
                time.sleep(1)

    # Offline / Dev fallback mode
    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(
                f"No raw source available. Could not fetch from API and local snapshot not found at {settings.paths.raw_api_response}"
            )

    records = parse_crossref_payload(payload)
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh list PaperRecord."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")
    raw_data = read_json(path)
    records: list[PaperRecord] = []
    for item in raw_data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=item.get("primary_category", ""),
                published=item.get("published", ""),
                updated=item.get("updated", ""),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    return records
