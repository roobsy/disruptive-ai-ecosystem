#!/usr/bin/env python3
"""
USPTO Patent Search & Extract
================================
Searches USPTO Open Data Portal for patents and extracts them into the KB.

Usage:
    python scripts/extract_patents.py
    python scripts/extract_patents.py --query "vision correction display"
    python scripts/extract_patents.py --auto    # Skip confirmation
"""

import httpx
import os
import sys
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

from core.kb import get_venture_id, store_node, store_provenance
from core.epistemic_filter import extract_from_text

USPTO_BASE = "https://api.uspto.gov/api/v1/patent/applications/search"


def search_uspto(query, api_key, limit=10):
    """Search USPTO ODP for granted patents."""
    body = {
        "q": query,
        "filters": [
            {
                "name": "applicationMetaData.applicationStatusDescriptionText",
                "value": ["Patented Case"]
            }
        ],
        "fields": [
            "applicationNumberText",
            "applicationMetaData.inventionTitle",
            "applicationMetaData.patentNumber",
            "applicationMetaData.filingDate",
            "applicationMetaData.grantDate",
            "applicationMetaData.firstApplicantName",
            "applicationMetaData.inventorBag",
            "applicationMetaData.applicationStatusDescriptionText",
        ],
        "pagination": {"offset": 0, "limit": limit},
        "sort": [{"field": "applicationMetaData.filingDate", "order": "desc"}],
    }

    try:
        resp = httpx.post(
            USPTO_BASE,
            json=body,
            headers={"X-API-Key": api_key},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except httpx.HTTPError as e:
        print(f"  USPTO API error: {e}")
        return []


def extract_patent_to_kb(patent_info, venture_id):
    """Extract a single patent into the KB."""
    pat_num = "US" + patent_info["num"]
    title = patent_info["title"]
    applicant = patent_info["applicant"]
    filing_date = patent_info["date"]
    inventors = patent_info["inventor_names"]

    text = (
        f"Patent: {title}\n"
        f"Patent Number: {pat_num}\n"
        f"Applicant: {applicant}\n"
        f"Filing Date: {filing_date}\n"
        f"Grant Date: {patent_info.get('grant_date', 'N/A')}\n"
        f"Inventors: {inventors}\n"
    )

    response = extract_from_text(text, source_description=f"USPTO Patent {pat_num}")

    if not response.success or not response.parsed:
        print(f"  Extraction failed: {response.error}")
        return 0

    nodes = response.parsed.get("nodes", [])
    stored = 0
    for nd in nodes:
        node = store_node(
            venture_id=venture_id,
            epistemic_label=nd.get("epistemic_label", "cognitive_framework"),
            content=nd.get("content", ""),
            summary=nd.get("summary"),
            confidence=nd.get("confidence", 50),
            decay_rate=nd.get("decay_rate", 365),
            domain=nd.get("domain"),
            tags=nd.get("tags", []),
            created_by="research_agent",
        )
        if node:
            store_provenance(
                node_id=node["id"],
                source_type="patent",
                source_url=f"https://patents.google.com/patent/{pat_num}",
                source_title=title,
                source_authors=[inventors],
                source_doi=pat_num,
                source_year=int(filing_date[:4]) if filing_date else None,
                credibility_tier="tier2_patent",
                extraction_agent="research_agent",
            )
            stored += 1
    return stored


def main():
    parser = argparse.ArgumentParser(description="USPTO Patent Search & Extract")
    parser.add_argument("--query", "-q", nargs="+", help="Custom search queries")
    parser.add_argument("--auto", "-a", action="store_true", help="Skip confirmation")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max patents per query")
    args = parser.parse_args()

    api_key = os.getenv("USPTO_ODP_API_KEY", "")
    if not api_key:
        print("ERROR: No USPTO_ODP_API_KEY in .env")
        print("Get your key at: https://data.uspto.gov (My ODP)")
        sys.exit(1)

    venture_id = get_venture_id()

    # Default queries for vision correction display venture
    queries = args.query or [
        "vision correction display",
        "display refractive error compensation",
        "computational vision correction aberration",
        "light field display vision",
        "eye tracking display correction",
    ]

    # Step 1: Search
    all_patents = []
    seen_nums = set()

    for q in queries:
        print(f"Searching USPTO: {q}")
        results = search_uspto(q, api_key, limit=args.limit)
        print(f"  Found {len(results)} patents")

        for r in results:
            meta = r.get("applicationMetaData", {})
            pat_num = meta.get("patentNumber", "")
            title = meta.get("inventionTitle", "")

            if not pat_num or not title or pat_num in seen_nums:
                continue

            seen_nums.add(pat_num)

            # Extract inventor names
            inventor_bag = meta.get("inventorBag", [])
            if isinstance(inventor_bag, list):
                inventor_names = ", ".join(
                    inv.get("inventorNameText", "")
                    for inv in inventor_bag[:5]
                    if isinstance(inv, dict)
                )
            else:
                inventor_names = str(inventor_bag)

            all_patents.append({
                "num": pat_num,
                "title": title,
                "applicant": meta.get("firstApplicantName", ""),
                "date": meta.get("filingDate", ""),
                "grant_date": meta.get("grantDate", ""),
                "inventor_names": inventor_names,
            })

        time.sleep(1)

    # Step 2: Show results
    print(f"\nTotal unique patents found: {len(all_patents)}\n")

    if not all_patents:
        print("No patents found. Try different search queries.")
        return

    for i, p in enumerate(all_patents, 1):
        print(f"  {i}. US{p['num']}: {p['title'][:65]}")
        print(f"     Applicant: {p['applicant']}  |  Filed: {p['date']}")

    # Step 3: Confirm
    count = min(len(all_patents), 15)
    if not args.auto:
        confirm = input(f"\nExtract {count} patents into KB? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return

    # Step 4: Extract
    print(f"\nExtracting {count} patents...\n")
    total_nodes = 0

    for p in all_patents[:count]:
        pat_num = "US" + p["num"]
        print(f"  {pat_num}: {p['title'][:55]}...")
        nodes = extract_patent_to_kb(p, venture_id)
        total_nodes += nodes
        print(f"    -> {nodes} nodes stored")
        time.sleep(2)

    print(f"\nDone. Total patent nodes stored: {total_nodes}")
    print(f"Verify with: python -c \"from core.kb import get_stats, get_venture_id; print(get_stats(get_venture_id()))\"")


if __name__ == "__main__":
    main()
