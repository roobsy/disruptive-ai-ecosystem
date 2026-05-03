"""
USPTO Open Data Portal (ODP) — US Patent search
==================================================
Searches US patent applications and granted patents via the
USPTO ODP search API.

Docs: https://api.uspto.gov/api/v1/patent/applications/search

Auth: API key in the X-API-Key header.
Env: USPTO_ODP_API_KEY (set via .env)

Rate limit: 1 second between requests (conservative default).
"""

import os
import time
import httpx
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from extraction.source_interface import SourceResult

# Load .env from the ecosystem root so this module works regardless of cwd.
_ecosystem_root = Path(__file__).resolve().parents[2]
load_dotenv(_ecosystem_root / ".env")
load_dotenv()

BASE = "https://api.uspto.gov/api/v1/patent/applications/search"

DEFAULT_FIELDS = [
    "applicationNumberText",
    "applicationMetaData.inventionTitle",
    "applicationMetaData.filingDate",
    "applicationMetaData.grantDate",
    "applicationMetaData.patentNumber",
    "applicationMetaData.inventorBag",
    "applicationMetaData.firstApplicantName",
    "applicationMetaData.applicationStatusDescriptionText",
    "abstractText",
]

_last_request = 0.0


def _api_key() -> str:
    return os.getenv("USPTO_ODP_API_KEY", "").strip()


def _headers() -> dict:
    return {
        "X-API-Key": _api_key(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _rate_limit():
    """Enforce 1-second gap between requests."""
    global _last_request
    now = time.time()
    wait = 1.0 - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()


def _year_range_to_dates(year_range: Optional[str]) -> Optional[tuple[str, str]]:
    """Convert "YYYY-YYYY" into ISO date strings for filing-date range filtering."""
    if not year_range:
        return None
    parts = year_range.split("-")
    if len(parts) != 2 or not parts[0]:
        return None
    start = f"{parts[0]}-01-01"
    end = f"{parts[1]}-12-31" if parts[1] else "2026-12-31"
    return start, end


def _post(body: dict, max_retries: int = 2) -> dict:
    """POST to the ODP search endpoint with rate limiting, auth, and 429 retry."""
    if not _api_key():
        return {}

    backoff = 2.0
    for attempt in range(max_retries + 1):
        _rate_limit()
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(BASE, json=body, headers=_headers())
                if resp.status_code == 429 and attempt < max_retries:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else backoff
                    print(f"  [USPTO-ODP] 429 throttled, sleeping {wait:.1f}s")
                    time.sleep(wait)
                    backoff *= 2
                    continue
                resp.raise_for_status()
                return resp.json() or {}
        except httpx.HTTPError as e:
            if attempt < max_retries:
                print(f"  [USPTO-ODP] Transient error ({e}), retrying...")
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"  [USPTO-ODP] Error: {e}")
            return {}
    return {}


def _extract_inventors(meta: dict) -> list[str]:
    """Pull inventor names from applicationMetaData.inventorBag."""
    bag = meta.get("inventorBag") or []
    names = []
    for inv in bag[:8]:
        if not isinstance(inv, dict):
            continue
        first = (inv.get("firstName") or inv.get("inventorNameFirstName") or "").strip()
        last = (inv.get("lastName") or inv.get("inventorNameLastName") or "").strip()
        full = f"{first} {last}".strip()
        if not full:
            full = (inv.get("inventorOrAuthorName") or inv.get("name") or "").strip()
        if full:
            names.append(full)
    return names


def _normalize_patent_number(raw: str) -> str:
    """Strip whitespace and ensure a US prefix for the patent_number field."""
    if not raw:
        return ""
    raw = str(raw).strip().replace(",", "").replace(" ", "")
    if not raw:
        return ""
    if raw.upper().startswith("US"):
        return raw.upper()
    return f"US{raw}"


def _record_to_result(record: dict) -> Optional[SourceResult]:
    """Map a single ODP record into a SourceResult."""
    if not isinstance(record, dict):
        return None

    meta = record.get("applicationMetaData") or {}
    title = (meta.get("inventionTitle") or "").strip()
    raw_pat = meta.get("patentNumber") or ""
    patent_number = _normalize_patent_number(raw_pat)
    app_num = (record.get("applicationNumberText") or "").strip()

    grant_date = meta.get("grantDate") or ""
    filing_date = meta.get("filingDate") or ""
    date_for_year = grant_date or filing_date
    year = None
    if date_for_year and len(date_for_year) >= 4 and date_for_year[:4].isdigit():
        year = int(date_for_year[:4])

    abstract = (record.get("abstractText") or "").strip()[:500]
    authors = _extract_inventors(meta)

    if patent_number:
        # Build a Google Patents URL using the bare digits for the canonical form.
        bare = patent_number[2:] if patent_number.upper().startswith("US") else patent_number
        url = f"https://patents.google.com/patent/US{bare}"
        display_id = patent_number
    elif app_num:
        url = f"https://patentcenter.uspto.gov/applications/{app_num}"
        display_id = f"App {app_num}"
    else:
        url = ""
        display_id = ""

    title_with_id = f"{display_id}: {title}" if display_id and title else (title or display_id)

    return SourceResult(
        source_type="patent",
        title=title_with_id,
        authors=authors,
        year=year,
        abstract=abstract,
        url=url,
        patent_number=patent_number,
        credibility_tier="tier2_patent",
        has_open_access=True,
        source_api="uspto_odp",
        raw_data=record,
    )


def _build_body(
    q: str,
    limit: int,
    year_range: Optional[str] = None,
    granted_only: bool = False,
    extra_filters: Optional[list[dict]] = None,
) -> dict:
    body: dict = {
        "q": q,
        "fields": DEFAULT_FIELDS,
        "sort": [{"field": "applicationMetaData.filingDate", "order": "desc"}],
        "pagination": {"offset": 0, "limit": min(max(limit, 1), 100)},
    }

    filters: list[dict] = []
    if granted_only:
        filters.append({
            "name": "applicationMetaData.applicationStatusDescriptionText",
            "value": ["Patented Case"],
        })
    if extra_filters:
        filters.extend(extra_filters)
    if filters:
        body["filters"] = filters

    date_range = _year_range_to_dates(year_range)
    if date_range:
        start, end = date_range
        body["rangeFilters"] = [{
            "field": "applicationMetaData.filingDate",
            "valueFrom": start,
            "valueTo": end,
        }]

    return body


def search(
    query: str,
    limit: int = 20,
    year_range: str = None,
    granted_only: bool = False,
    **kwargs,
) -> list[SourceResult]:
    """Free-text search across the USPTO ODP patent applications corpus.

    Args:
        query: Free-text or field-qualified ODP query string.
        limit: Max records to return (1-100).
        year_range: Optional "YYYY-YYYY" string applied to filing date.
        granted_only: When True, restrict to "Patented Case" status.

    Returns an empty list if USPTO_ODP_API_KEY is unset.
    """
    if not _api_key():
        return []

    body = _build_body(
        q=query,
        limit=limit,
        year_range=year_range,
        granted_only=granted_only,
    )

    data = _post(body)
    records = (
        data.get("patentFileWrapperDataBag")
        or data.get("results")
        or data.get("data")
        or []
    )

    results: list[SourceResult] = []
    for rec in records:
        sr = _record_to_result(rec)
        if sr is not None:
            results.append(sr)
    return results


def search_by_assignee(
    assignee: str,
    limit: int = 20,
    year_range: str = None,
    **kwargs,
) -> list[SourceResult]:
    """Search patents by first applicant name (assignee).

    Uses a field-qualified query against
    applicationMetaData.firstApplicantName so phrase matching works.
    """
    if not _api_key():
        return []

    safe = assignee.replace('"', '\\"')
    q = f'applicationMetaData.firstApplicantName:"{safe}"'

    body = _build_body(q=q, limit=limit, year_range=year_range)
    data = _post(body)
    records = (
        data.get("patentFileWrapperDataBag")
        or data.get("results")
        or data.get("data")
        or []
    )

    results: list[SourceResult] = []
    for rec in records:
        sr = _record_to_result(rec)
        if sr is not None:
            results.append(sr)
    return results
