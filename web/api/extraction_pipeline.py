"""
Unified extraction pipeline.

Decides how to acquire content for a given source (ArXiv ID → arxiv PDF,
DOI → Unpaywall, patent → Google Patents PDF, otherwise → abstract text)
and runs the Epistemic Filter on whatever it can get.

Yields SSE events as a stream of ("event_name", data_dict) tuples. The
caller (web/api/routes/research.py) wraps these in `_sse(...)` frames and
emits them to the browser.

This module is the single place that knows about extraction strategy.
"""

import asyncio
import re
import sys
import tempfile
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx
from pydantic import BaseModel, Field

from core.epistemic_filter import extract_from_pdf, extract_from_text
from core.kb import (
    check_already_extracted,
    log_extraction,
    store_node,
    store_provenance,
)
from extraction.sources.arxiv import download_pdf as arxiv_download_pdf
from extraction.sources.arxiv import get_paper_metadata as arxiv_get_metadata
from extraction.sources.unpaywall import find_open_access
from extraction.sources.google_patents import get_patent_pdf_url


# ── Request shape ─────────────────────────────────────────
class ExtractSource(BaseModel):
    """Mirrors the shape of an extraction.source_interface.SourceResult,
    used to drive a unified extract pipeline."""

    arxiv_id: str = ""
    doi: str = ""
    patent_number: str = ""
    pdf_url: str = ""
    url: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    source_type: str = "academic_paper"  # "academic_paper" | "patent" | "website"
    source_api: str = ""
    credibility_tier: str = ""


# ── PDF download with validation ──────────────────────────
async def _download_pdf_to_tmp(url: str, timeout: float = 30.0) -> Optional[Path]:
    """Download a URL; return path only if the response is a real PDF.

    Validates with the %PDF magic bytes. Returns None on any failure or if
    the content is HTML (a paywall landing page).
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "DisruptiveEcosystem/0.1"})
            if r.status_code != 200:
                return None
            content = r.content
    except Exception as e:
        print(f"[pipeline] PDF download error from {url}: {e}", file=sys.stderr)
        return None

    if not content.startswith(b"%PDF"):
        return None

    tmp = Path(tempfile.gettempdir()) / f"ecosystem_extract_{abs(hash(url))}.pdf"
    tmp.write_bytes(content)
    return tmp


# ── Strategy decision ─────────────────────────────────────
Strategy = str  # "arxiv_pdf" | "google_patents_pdf" | "url_pdf" | "unpaywall_pdf" | "text_only" | "unavailable"


def decide_strategy(source: ExtractSource, require_pdf: bool) -> tuple[Strategy, str]:
    """Return (strategy, reason). Strategy is what we'll *try* first; if it
    fails we may fall back to text_only (unless require_pdf is True)."""
    if source.arxiv_id:
        return "arxiv_pdf", "ArXiv ID present — full PDF available"
    if source.pdf_url:
        return "url_pdf", f"Direct PDF URL: {source.pdf_url[:60]}"
    if source.doi:
        return "unpaywall_pdf", f"DOI {source.doi} — checking Unpaywall for open-access PDF"
    if source.patent_number:
        return "google_patents_pdf", f"Patent {source.patent_number} — trying Google Patents PDF"
    if source.abstract:
        if require_pdf:
            return "unavailable", "No PDF source available and require_pdf is set"
        return "text_only", "No PDF — using abstract text"
    return "unavailable", "No content sources (no IDs, no URL, no abstract)"


# ── Source URL canonicalization (for dedup) ───────────────
def canonical_source_url(source: ExtractSource) -> str:
    if source.arxiv_id:
        return f"https://arxiv.org/abs/{source.arxiv_id}"
    if source.doi:
        return f"https://doi.org/{source.doi.replace('https://doi.org/', '')}"
    if source.patent_number:
        return f"https://patents.google.com/patent/{source.patent_number.strip().replace(' ', '')}/en"
    return source.url or source.pdf_url or ""


# ── Text fallback composition ─────────────────────────────
def build_fallback_text(source: ExtractSource) -> str:
    """Compose the best text we have when no PDF is available."""
    parts: list[str] = []
    if source.title:
        parts.append(f"Title: {source.title}")
    if source.authors:
        parts.append(f"Authors: {', '.join(source.authors[:8])}")
    if source.year:
        parts.append(f"Year: {source.year}")
    if source.patent_number:
        parts.append(f"Patent: {source.patent_number}")
    if source.doi:
        parts.append(f"DOI: {source.doi}")
    if source.abstract:
        parts.append("\nAbstract:\n" + source.abstract.strip())
    return "\n".join(parts)


# ── Pipeline ──────────────────────────────────────────────
async def run_extraction(
    source: ExtractSource,
    context: str,
    force: bool,
    require_pdf: bool,
    venture_id: str,
) -> AsyncIterator[tuple[str, dict]]:
    """Async generator yielding ('event', payload) tuples for SSE.

    Stages:
        plan        → show chosen strategy + reason
        metadata    → fetched / known title/authors
        download    → trying to acquire content
        epistemic   → running the Epistemic Filter
        store       → persisting nodes to the KB
        done | error | skipped

    Per-node `stored` events fire as each node lands in the KB so the UI
    can tick them off as the mutation happens.
    """
    source_url = canonical_source_url(source)

    # 1. Plan
    strategy, reason = decide_strategy(source, require_pdf)
    yield "plan", {
        "strategy": strategy,
        "reason": reason,
        "source_url": source_url,
        "require_pdf": require_pdf,
    }
    if strategy == "unavailable":
        yield "error", {"message": reason}
        return

    # 2. Already-extracted check
    if not force and source_url:
        already = await asyncio.to_thread(check_already_extracted, venture_id, source_url)
        if already:
            yield "skipped", {
                "message": "This source has already been extracted. Pass force=true to re-extract.",
                "url": source_url,
            }
            yield "done", {"stop_reason": "already_extracted"}
            return

    # 3. Acquire content
    pdf_path: Optional[Path] = None
    text_content: Optional[str] = None
    used_strategy = strategy
    fallback_used = False

    if strategy == "arxiv_pdf":
        yield "stage", {"name": "download", "message": f"Downloading ArXiv PDF for {source.arxiv_id}…"}
        pdf_path_str = await asyncio.to_thread(arxiv_download_pdf, source.arxiv_id)
        if pdf_path_str:
            pdf_path = Path(str(pdf_path_str))
            yield "downloaded", {"path": str(pdf_path), "via": "arxiv"}
        # Optionally enrich metadata
        meta = await asyncio.to_thread(arxiv_get_metadata, source.arxiv_id)
        if meta:
            if not source.title and meta.get("title"):
                source.title = meta["title"]
            if not source.authors and meta.get("authors"):
                source.authors = meta["authors"]
            if not source.year and meta.get("year"):
                source.year = meta["year"]

    elif strategy == "url_pdf":
        yield "stage", {"name": "download", "message": "Downloading PDF from source URL…"}
        pdf_path = await _download_pdf_to_tmp(source.pdf_url)
        if pdf_path:
            yield "downloaded", {"path": str(pdf_path), "via": "direct_url"}

    elif strategy == "unpaywall_pdf":
        yield "stage", {"name": "unpaywall", "message": f"Looking up open-access PDF for {source.doi}…"}
        oa = await asyncio.to_thread(find_open_access, source.doi)
        if oa and oa.get("pdf_url"):
            yield "stage", {"name": "download", "message": f"Downloading OA PDF: {oa['pdf_url'][:60]}…"}
            pdf_path = await _download_pdf_to_tmp(oa["pdf_url"])
            if pdf_path:
                yield "downloaded", {"path": str(pdf_path), "via": "unpaywall"}
        else:
            yield "stage", {"name": "unpaywall", "message": "No open-access version found."}

    elif strategy == "google_patents_pdf":
        url = get_patent_pdf_url(source.patent_number)
        yield "stage", {"name": "download", "message": f"Trying Google Patents PDF for {source.patent_number}…"}
        pdf_path = await _download_pdf_to_tmp(url)
        if pdf_path:
            yield "downloaded", {"path": str(pdf_path), "via": "google_patents"}

    # 4. Decide whether to fall back to text
    if pdf_path is None and strategy != "text_only":
        if require_pdf:
            yield "error", {
                "message": (
                    "No PDF could be acquired. Disable 'Require PDF' in the "
                    "confirmation modal to use abstract-text fallback (lower-quality)."
                )
            }
            await asyncio.to_thread(
                log_extraction, venture_id, source_url,
                status="failed", error_message="PDF acquisition failed; require_pdf=true",
            )
            return
        # Fallback to text
        text_content = build_fallback_text(source)
        if not text_content.strip():
            yield "error", {"message": "No abstract or text content available for fallback."}
            await asyncio.to_thread(
                log_extraction, venture_id, source_url,
                status="failed", error_message="No content available",
            )
            return
        used_strategy = "text_only"
        fallback_used = True
        yield "fallback", {
            "from": strategy,
            "to": "text_only",
            "char_count": len(text_content),
            "message": (
                "PDF unavailable — falling back to abstract text. "
                "Extracted nodes will be tagged 'abstract_only' and may have lower confidence."
            ),
        }

    # 5. Run the Epistemic Filter
    if pdf_path is not None:
        yield "stage", {
            "name": "epistemic_filter",
            "message": "Running Epistemic Filter on the PDF (30–60s)…",
        }
        response = await asyncio.to_thread(extract_from_pdf, str(pdf_path), context)
    else:
        yield "stage", {
            "name": "epistemic_filter",
            "message": (
                "Running Epistemic Filter on text (faster than PDF, lower yield)…"
                if text_content else "Running Epistemic Filter…"
            ),
        }
        # Augment context to nudge the model to be more conservative on abstract-only
        text_context = context
        if fallback_used:
            text_context = (
                "This is an ABSTRACT-ONLY extraction (full PDF was unavailable). "
                "Be conservative with confidence (cap at 75 unless universally agreed). "
                "Extract fewer claims (5–15) — focus on the strongest signals.\n\n"
                + (context or "")
            )
        source_desc = f"{source.source_type} · {source.source_api or 'unknown'}"
        if source.title:
            source_desc += f" · {source.title[:80]}"
        response = await asyncio.to_thread(
            extract_from_text, text_content or "", source_desc + ("\n\n" + text_context if text_context else "")
        )

    if not response.success:
        await asyncio.to_thread(
            log_extraction, venture_id, source_url,
            status="failed", error_message=response.error,
            cost_input_tokens=response.input_tokens,
            cost_output_tokens=response.output_tokens,
        )
        yield "error", {"message": f"Extraction failed: {response.error}"}
        return

    if not response.parsed:
        await asyncio.to_thread(
            log_extraction, venture_id, source_url,
            status="failed", error_message="JSON parse failed",
            cost_input_tokens=response.input_tokens,
            cost_output_tokens=response.output_tokens,
        )
        yield "error", {"message": "Could not parse JSON response from the model."}
        return

    nodes_data = response.parsed.get("nodes", [])
    source_summary = response.parsed.get("source_summary", "")
    parsed_source_type = response.parsed.get("source_type") or source.source_type or "academic_paper"

    yield "extracted", {
        "node_count": len(nodes_data),
        "summary": source_summary,
        "model": response.model,
        "duration_ms": response.duration_ms,
        "cost_usd": round(response.cost_estimate, 4),
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "strategy": used_strategy,
        "fallback_used": fallback_used,
        "nodes_preview": [
            {
                "epistemic_label": n.get("epistemic_label"),
                "summary": n.get("summary") or n.get("content", "")[:120],
                "domain": n.get("domain"),
                "confidence": n.get("confidence"),
            }
            for n in nodes_data
        ],
    }

    # 6. Store
    yield "stage", {"name": "store", "message": "Storing nodes in KB…"}

    credibility = source.credibility_tier or (
        "tier2_patent" if source.patent_number else "tier1_academic"
    )
    if fallback_used:
        credibility += "_abstract"

    abstract_tag = "abstract_only" if fallback_used else None

    def _store_one(node_data: dict):
        tags = list(node_data.get("tags") or [])
        if abstract_tag and abstract_tag not in tags:
            tags.append(abstract_tag)
        node = store_node(
            venture_id=venture_id,
            epistemic_label=node_data.get("epistemic_label", "cognitive_framework"),
            content=node_data.get("content", ""),
            summary=node_data.get("summary"),
            confidence=node_data.get("confidence", 50),
            decay_rate=node_data.get("decay_rate", 365),
            domain=node_data.get("domain"),
            tags=tags,
            created_by="extraction_engine",
        )
        if node:
            store_provenance(
                node_id=node["id"],
                source_type=parsed_source_type,
                source_url=source_url,
                source_title=source.title,
                source_authors=source.authors,
                source_doi=source.doi or source.arxiv_id,
                source_year=source.year,
                credibility_tier=credibility,
            )
        return node

    stored = 0
    errors: list[str] = []
    for i, node_data in enumerate(nodes_data, 1):
        try:
            node = await asyncio.to_thread(_store_one, node_data)
            if node:
                stored += 1
                yield "stored", {
                    "index": i,
                    "total": len(nodes_data),
                    "node_id": node.get("id"),
                    "summary": node_data.get("summary") or node_data.get("content", "")[:120],
                }
        except Exception as e:
            errors.append(str(e))

    await asyncio.to_thread(
        log_extraction, venture_id, source_url,
        source_type=parsed_source_type,
        status="completed",
        nodes_created=stored,
        cost_input_tokens=response.input_tokens,
        cost_output_tokens=response.output_tokens,
        processing_time_ms=response.duration_ms,
    )

    yield "done", {
        "stop_reason": "completed",
        "stored": stored,
        "errors": errors,
        "cost_usd": round(response.cost_estimate, 4),
        "duration_seconds": round(response.duration_ms / 1000, 1),
        "strategy": used_strategy,
        "fallback_used": fallback_used,
    }
