"""
Semantic Scholar — 200M+ papers, authenticated API
=====================================================
Rate limit: 1 request/second with API key.
"""

import os
import time
import httpx
from pathlib import Path
from extraction.source_interface import SourceResult
from dotenv import load_dotenv

# Load .env from ecosystem root (not dependent on process cwd).
_ecosystem_root = Path(__file__).resolve().parents[2]
load_dotenv(_ecosystem_root / ".env")
load_dotenv()

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,abstract,year,citationCount,openAccessPdf,authors,externalIds,journal"

_last_request = 0.0


def _headers() -> dict:
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    h = {}
    if key:
        h["x-api-key"] = key
    return h


def _rate_limit():
    """Enforce 1 request per second."""
    global _last_request
    now = time.time()
    wait = 1.1 - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()


def search(query: str, limit: int = 20, year_range: str = None, min_citations: int = 0) -> list[SourceResult]:
    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS}
    if year_range:
        params["year"] = year_range

    _rate_limit()
    # #region agent log
    try:
        _k = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        _logf = Path(__file__).resolve().parents[6] / "debug-170d42.log"
        with _logf.open("a", encoding="utf-8") as _lf:
            _lf.write(
                json.dumps(
                    {
                        "sessionId": "170d42",
                        "hypothesisId": "H1",
                        "location": "semantic_scholar.search",
                        "message": "pre-request env state",
                        "data": {
                            "has_key": bool(_k),
                            "key_len": len(_k),
                            "dotenv_root": str(_ecosystem_root),
                        },
                        "timestamp": int(time.time() * 1000),
                        "runId": "pre-fix",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{BASE}/paper/search", params=params, headers=_headers())
            # #region agent log
            try:
                _logf2 = Path(__file__).resolve().parents[6] / "debug-170d42.log"
                with _logf2.open("a", encoding="utf-8") as _lf2:
                    _lf2.write(
                        json.dumps(
                            {
                                "sessionId": "170d42",
                                "hypothesisId": "H2",
                                "location": "semantic_scholar.search",
                                "message": "response status",
                                "data": {"status_code": resp.status_code},
                                "timestamp": int(time.time() * 1000),
                                "runId": "pre-fix",
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion
            resp.raise_for_status()
            papers = resp.json().get("data", [])
    except httpx.HTTPError as e:
        print(f"  [Semantic Scholar] Error: {e}")
        return []

    results = []
    for p in papers:
        if min_citations and (p.get("citationCount") or 0) < min_citations:
            continue
        ext = p.get("externalIds") or {}
        oa = p.get("openAccessPdf") or {}
        results.append(SourceResult(
            source_type="academic_paper", title=p.get("title", ""),
            authors=[a.get("name", "") for a in (p.get("authors") or [])],
            year=p.get("year"), abstract=p.get("abstract") or "",
            url=f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}",
            pdf_url=oa.get("url", ""), doi=ext.get("DOI", ""),
            arxiv_id=ext.get("ArXiv", ""), citation_count=p.get("citationCount") or 0,
            credibility_tier="tier1_academic", has_open_access=bool(oa.get("url")),
            source_api="semantic_scholar", raw_data=p,
        ))
    return results


def get_references(paper_id: str, limit: int = 20) -> list[SourceResult]:
    _rate_limit()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{BASE}/paper/{paper_id}/references",
                            params={"fields": FIELDS, "limit": limit}, headers=_headers())
            resp.raise_for_status()
            refs = resp.json().get("data", [])
    except httpx.HTTPError:
        return []
    results = []
    for r in refs:
        p = r.get("citedPaper", {})
        if not p.get("title"):
            continue
        ext = p.get("externalIds") or {}
        oa = p.get("openAccessPdf") or {}
        results.append(SourceResult(
            source_type="academic_paper", title=p.get("title", ""),
            authors=[a.get("name", "") for a in (p.get("authors") or [])],
            year=p.get("year"), abstract=p.get("abstract") or "",
            doi=ext.get("DOI", ""), arxiv_id=ext.get("ArXiv", ""),
            citation_count=p.get("citationCount") or 0, has_open_access=bool(oa.get("url")),
            pdf_url=oa.get("url", ""), source_api="semantic_scholar", credibility_tier="tier1_academic",
        ))
    return results
