"""
EPO Open Patent Services — European & worldwide patents
==========================================================
Free developer tier. Requires registration for API key.
Register at: https://developers.epo.org/
Docs: https://developers.epo.org/ops-v3-2/apis
"""

import os
import httpx
import base64
from typing import Optional
from extraction.source_interface import SourceResult
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search"
BIBLIO_URL = "https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc"

_token: Optional[str] = None


def _get_token() -> Optional[str]:
    """Authenticate with EPO OPS using consumer key/secret."""
    global _token
    if _token:
        return _token

    key = os.getenv("EPO_CONSUMER_KEY")
    secret = os.getenv("EPO_CONSUMER_SECRET")

    if not key or not secret:
        return None  # EPO not configured — skip silently

    credentials = base64.b64encode(f"{key}:{secret}".encode()).decode()

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(AUTH_URL, headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }, data="grant_type=client_credentials")
            resp.raise_for_status()
            _token = resp.json().get("access_token")
            return _token
    except httpx.HTTPError as e:
        print(f"  [EPO] Auth failed: {e}")
        return None


def search(query: str, limit: int = 20, year_range: str = None, **kwargs) -> list[SourceResult]:
    """Search EPO for patents matching a query.

    Note: Requires EPO_CONSUMER_KEY and EPO_CONSUMER_SECRET in .env.
    Register free at https://developers.epo.org/
    """
    token = _get_token()
    if not token:
        # EPO not configured — return empty silently
        return []

    # Build CQL query
    cql = f'ta="{query}"'  # Search in title and abstract
    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2 and parts[0]:
            cql += f' and pd>={parts[0]}'

    params = {"q": cql, "Range": f"1-{min(limit, 25)}"}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(SEARCH_URL, params=params, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            })
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        print(f"  [EPO] Search error: {e}")
        return []

    # Parse the response (EPO has a complex nested structure)
    results = []
    try:
        search_result = data.get("ops:world-patent-data", {}).get("ops:biblio-search", {})
        docs = search_result.get("ops:search-result", {}).get("ops:publication-reference", [])
        if isinstance(docs, dict):
            docs = [docs]

        for doc in docs[:limit]:
            doc_id = doc.get("document-id", {})
            if isinstance(doc_id, list):
                doc_id = doc_id[0]
            country = doc_id.get("country", {}).get("$", "")
            number = doc_id.get("doc-number", {}).get("$", "")
            kind = doc_id.get("kind", {}).get("$", "")
            pat_num = f"{country}{number}{kind}"

            results.append(SourceResult(
                source_type="patent",
                title=pat_num,  # Title requires additional API call
                patent_number=pat_num,
                url=f"https://worldwide.espacenet.com/patent/search?q={pat_num}",
                credibility_tier="tier2_patent",
                has_open_access=True,
                source_api="epo",
            ))
    except (KeyError, TypeError) as e:
        print(f"  [EPO] Parse error: {e}")

    return results
