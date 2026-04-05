"""
OpenAlex — 250M+ works, free, unlimited
==========================================
Open catalog of global research. Excellent for landscape mapping,
institutional data, and finding connections between works.
Docs: https://docs.openalex.org/
"""

import httpx
from extraction.source_interface import SourceResult

BASE = "https://api.openalex.org"
MAILTO = "ecosystem@disruptive.ai"  # Polite pool — gets faster responses


def search(query: str, limit: int = 20, year_range: str = None, min_citations: int = 0) -> list[SourceResult]:
    params = {
        "search": query,
        "per_page": min(limit, 50),
        "sort": "relevance_score:desc",
        "mailto": MAILTO,
    }
    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2:
            filters = []
            if parts[0]:
                filters.append(f"from_publication_date:{parts[0]}-01-01")
            if parts[1]:
                filters.append(f"to_publication_date:{parts[1]}-12-31")
            if filters:
                params["filter"] = ",".join(filters)
    if min_citations:
        filt = params.get("filter", "")
        cite_filter = f"cited_by_count:>{min_citations}"
        params["filter"] = f"{filt},{cite_filter}" if filt else cite_filter

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{BASE}/works", params=params)
            resp.raise_for_status()
            works = resp.json().get("results", [])
    except httpx.HTTPError as e:
        print(f"  [OpenAlex] Error: {e}")
        return []

    results = []
    for w in works:
        # Extract identifiers
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        ids = w.get("ids") or {}
        arxiv_raw = ids.get("openalex", "")

        # Extract authors
        authorships = w.get("authorships") or []
        authors = [a.get("author", {}).get("display_name", "") for a in authorships[:10]]

        # Open access
        oa_info = w.get("open_access") or {}
        oa_url = oa_info.get("oa_url") or ""
        best_oa = w.get("best_oa_location") or {}
        pdf_url = best_oa.get("pdf_url") or oa_url

        # Year
        year = w.get("publication_year")

        # Abstract reconstruction (OpenAlex stores inverted index)
        abstract = ""
        inv_abstract = w.get("abstract_inverted_index")
        if inv_abstract:
            word_positions = []
            for word, positions in inv_abstract.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join(w for _, w in word_positions)[:500]

        results.append(SourceResult(
            source_type="academic_paper", title=w.get("title") or "",
            authors=authors, year=year, abstract=abstract,
            url=w.get("id", "").replace("https://openalex.org/", "https://openalex.org/works/"),
            pdf_url=pdf_url, doi=doi,
            citation_count=w.get("cited_by_count") or 0,
            credibility_tier="tier1_academic",
            has_open_access=oa_info.get("is_oa", False),
            source_api="openalex", raw_data=w,
        ))
    return results
