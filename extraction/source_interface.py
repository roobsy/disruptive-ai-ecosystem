"""
Source Interface — Unified Contract for All Data Sources
==========================================================
Every data source (academic, patent, web) implements this
interface so the Research Agent can query any source
without knowing its implementation details.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceResult:
    """Standardized result from any data source."""
    source_type: str            # "academic_paper", "patent", "website", "market_data"
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    url: str = ""
    pdf_url: str = ""           # Direct PDF download link (if available)
    doi: str = ""
    arxiv_id: str = ""
    patent_number: str = ""
    citation_count: int = 0
    credibility_tier: str = ""  # "tier1_academic", "tier2_patent", etc.
    has_open_access: bool = False
    source_api: str = ""        # Which API found this: "semantic_scholar", "openalex", etc.
    raw_data: dict = field(default_factory=dict)  # Full API response for reference

    def summary_line(self) -> str:
        """One-line human-readable summary."""
        pdf_flag = "PDF" if self.has_open_access else "no-pdf"
        author = self.authors[0] if self.authors else "Unknown"
        id_str = ""
        if self.arxiv_id:
            id_str = f" [arXiv:{self.arxiv_id}]"
        elif self.patent_number:
            id_str = f" [{self.patent_number}]"
        elif self.doi:
            id_str = f" [DOI:{self.doi[:30]}]"
        return f"[{self.year or '?'}] [{self.citation_count} cites] [{pdf_flag}]{id_str} {author} — {self.title[:80]}"
