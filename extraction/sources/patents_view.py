"""
USPTO PatentsView — US Patent search, free, no auth
======================================================
Searches US granted patents and applications.
Docs: https://patentsview.org/apis/api-endpoints
"""

import httpx
import json
from extraction.source_interface import SourceResult

BASE = "https://api.patentsview.org/patents/query"
APP_BASE = "https://api.patentsview.org/patent_applications/query"


def search(query: str, limit: int = 20, year_range: str = None, **kwargs) -> list[SourceResult]:
    """Search USPTO patents by keyword.

    Uses the PatentsView query API with text search across
    title, abstract, and claims.
    """
    # Build the query
    q_parts = []
    for word in query.split():
        q_parts.append({"_text_any": {"patent_abstract": word}})

    if len(q_parts) == 1:
        q = q_parts[0]
    else:
        q = {"_and": q_parts[:5]}  # Limit to 5 terms

    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2 and parts[0]:
            q = {"_and": [q, {"_gte": {"patent_date": f"{parts[0]}-01-01"}}]}

    body = {
        "q": q,
        "f": [
            "patent_number", "patent_title", "patent_abstract",
            "patent_date", "patent_type",
            "inventor_first_name", "inventor_last_name",
            "assignee_organization",
        ],
        "o": {"page": 1, "per_page": min(limit, 50)},
        "s": [{"patent_date": "desc"}],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(BASE, json=body)
            resp.raise_for_status()
            data = resp.json()
            patents = data.get("patents") or []
    except httpx.HTTPError as e:
        print(f"  [PatentsView] Error: {e}")
        return []

    results = []
    for p in patents:
        # Patent number
        pat_num = p.get("patent_number", "")

        # Title
        title = p.get("patent_title", "")

        # Date and year
        pat_date = p.get("patent_date", "")
        year = int(pat_date[:4]) if pat_date and len(pat_date) >= 4 else None

        # Abstract
        abstract = p.get("patent_abstract", "")[:500]

        # Inventors
        inventors = p.get("inventors") or []
        authors = []
        for inv in inventors[:5]:
            name = f"{inv.get('inventor_first_name', '')} {inv.get('inventor_last_name', '')}".strip()
            if name:
                authors.append(name)

        # Assignee
        assignees = p.get("assignees") or []
        assignee_names = [a.get("assignee_organization", "") for a in assignees if a.get("assignee_organization")]

        # URL
        url = f"https://patents.google.com/patent/US{pat_num}" if pat_num else ""

        results.append(SourceResult(
            source_type="patent",
            title=f"US{pat_num}: {title}",
            authors=authors,
            year=year,
            abstract=abstract,
            url=url,
            patent_number=f"US{pat_num}",
            credibility_tier="tier2_patent",
            has_open_access=True,  # Patents are public
            source_api="patentsview",
            raw_data={**p, "assignees": assignee_names},
        ))
    return results


def search_by_assignee(assignee: str, limit: int = 20) -> list[SourceResult]:
    """Search patents by assignee organization name."""
    body = {
        "q": {"_contains": {"assignee_organization": assignee}},
        "f": [
            "patent_number", "patent_title", "patent_abstract",
            "patent_date", "assignee_organization",
            "inventor_first_name", "inventor_last_name",
        ],
        "o": {"page": 1, "per_page": min(limit, 50)},
        "s": [{"patent_date": "desc"}],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(BASE, json=body)
            resp.raise_for_status()
            data = resp.json()
            patents = data.get("patents") or []
    except httpx.HTTPError as e:
        print(f"  [PatentsView] Assignee search error: {e}")
        return []

    results = []
    for p in patents:
        pat_num = p.get("patent_number", "")
        title = p.get("patent_title", "")
        pat_date = p.get("patent_date", "")
        year = int(pat_date[:4]) if pat_date and len(pat_date) >= 4 else None
        inventors = p.get("inventors") or []
        authors = [f"{i.get('inventor_first_name', '')} {i.get('inventor_last_name', '')}".strip() for i in inventors[:5]]

        results.append(SourceResult(
            source_type="patent", title=f"US{pat_num}: {title}",
            authors=authors, year=year,
            abstract=p.get("patent_abstract", "")[:500],
            url=f"https://patents.google.com/patent/US{pat_num}",
            patent_number=f"US{pat_num}",
            credibility_tier="tier2_patent", has_open_access=True,
            source_api="patentsview", raw_data=p,
        ))
    return results
