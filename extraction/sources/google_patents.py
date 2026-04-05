"""
Google Patents — Direct patent lookup and text extraction
============================================================
Google Patents doesn't have a free search API, but we can
construct URLs for known patent numbers and extract text
from patent pages. For search, we rely on PatentsView (USPTO)
and EPO (European). This module handles direct lookups.
"""

import httpx
import re
from typing import Optional
from extraction.source_interface import SourceResult


def lookup_patent(patent_number: str) -> Optional[SourceResult]:
    """Look up a specific patent by number on Google Patents.

    Args:
        patent_number: e.g., "US12141346", "US20160042501A1", "EP3123456"

    Returns:
        SourceResult with patent information, or None
    """
    clean = patent_number.strip().replace(" ", "").replace(",", "")
    url = f"https://patents.google.com/patent/{clean}/en"

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        print(f"  [Google Patents] Lookup failed: {e}")
        return None

    # Extract title
    title_match = re.search(r'<meta name="DC\.title" content="([^"]+)"', html)
    title = title_match.group(1) if title_match else clean

    # Extract abstract
    abstract_match = re.search(r'<meta name="DC\.description" content="([^"]+)"', html)
    abstract = abstract_match.group(1)[:500] if abstract_match else ""

    # Extract inventors
    inventors = re.findall(r'<meta name="DC\.contributor" scheme="inventor" content="([^"]+)"', html)

    # Extract assignee
    assignee = re.findall(r'<meta name="DC\.contributor" scheme="assignee" content="([^"]+)"', html)

    # Extract date
    date_match = re.search(r'<meta name="DC\.date" content="(\d{4})', html)
    year = int(date_match.group(1)) if date_match else None

    return SourceResult(
        source_type="patent",
        title=f"{clean}: {title}",
        authors=inventors[:10],
        year=year,
        abstract=abstract,
        url=url,
        patent_number=clean,
        credibility_tier="tier2_patent",
        has_open_access=True,
        source_api="google_patents",
        raw_data={"assignees": assignee},
    )


def get_patent_pdf_url(patent_number: str) -> str:
    """Construct the Google Patents PDF download URL."""
    clean = patent_number.strip().replace(" ", "")
    return f"https://patents.google.com/patent/{clean}/en?download=true"


# Known key patents for the vision correction venture
KEY_PATENTS = [
    "US12141346",       # Rabbit Eyes — Vision Correction Display
    "US20160042501A1",  # UC Berkeley — Vision correcting display with aberration compensation
    "US10529059B2",     # UC Berkeley — Vision correcting display (granted)
    "US20200348519A1",  # Apple — Vision correction graphical outputs
]
