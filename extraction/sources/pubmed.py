"""
PubMed / NCBI — 36M+ biomedical citations, free
====================================================
Essential for ophthalmology and vision science research.
Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""

import httpx
import re
from extraction.source_interface import SourceResult

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESUM = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def search(query: str, limit: int = 20, year_range: str = None, min_citations: int = 0) -> list[SourceResult]:
    # Step 1: Search for PMIDs
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(limit, 50),
        "retmode": "json",
        "sort": "relevance",
    }
    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2:
            if parts[0]:
                params["mindate"] = f"{parts[0]}/01/01"
            if parts[1]:
                params["maxdate"] = f"{parts[1]}/12/31"
            params["datetype"] = "pdat"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(ESEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
    except httpx.HTTPError as e:
        print(f"  [PubMed] Search error: {e}")
        return []

    if not pmids:
        return []

    # Step 2: Fetch summaries for those PMIDs
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(ESUM, params={
                "db": "pubmed", "id": ",".join(pmids), "retmode": "json"
            })
            resp.raise_for_status()
            summaries = resp.json().get("result", {})
    except httpx.HTTPError as e:
        print(f"  [PubMed] Fetch error: {e}")
        return []

    # Step 3: Fetch abstracts via efetch XML
    abstracts = {}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(EFETCH, params={
                "db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "rettype": "abstract"
            })
            resp.raise_for_status()
            xml = resp.text
            # Simple XML extraction of abstracts
            for pmid in pmids:
                # Find abstract text within the article for this PMID
                pattern = f"<PMID[^>]*>{pmid}</PMID>.*?<AbstractText[^>]*>(.*?)</AbstractText>"
                match = re.search(pattern, xml, re.DOTALL)
                if match:
                    abstract = re.sub(r"<[^>]+>", "", match.group(1))[:500]
                    abstracts[pmid] = abstract
    except Exception:
        pass  # Abstracts are optional enhancement

    results = []
    for pmid in pmids:
        if pmid not in summaries:
            continue
        s = summaries[pmid]
        if isinstance(s, str):
            continue

        # Authors
        author_list = s.get("authors") or []
        authors = [a.get("name", "") for a in author_list[:10]]

        # Year
        pubdate = s.get("pubdate", "")
        year_match = re.search(r"(\d{4})", pubdate)
        year = int(year_match.group(1)) if year_match else None

        # DOI
        articleids = s.get("articleids") or []
        doi = ""
        for aid in articleids:
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
                break

        title = s.get("title", "")
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        results.append(SourceResult(
            source_type="academic_paper", title=title,
            authors=authors, year=year,
            abstract=abstracts.get(pmid, ""),
            url=url, doi=doi,
            credibility_tier="tier1_academic",
            has_open_access=False,  # Will be checked via Unpaywall
            source_api="pubmed", raw_data=s,
        ))
    return results
