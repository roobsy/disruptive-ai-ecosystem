"""Research endpoints — preview, extract, and gap metadata.

Mutating endpoints (extract) stream Server-Sent Events with stage updates so
the UI can render live progress and the user can see what's being inserted
into the KB before/while it happens.
"""

import asyncio
import json
import os
import sys
import traceback
from dataclasses import asdict
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from extraction.source_router import (
    search_academic,
    search_patents,
    search_all,
    lookup_known_patents,
)
from extraction.source_interface import SourceResult
from extraction.sources.arxiv import download_pdf, get_paper_metadata
from core.epistemic_filter import extract_from_pdf
from core.kb import (
    get_venture_id,
    store_node,
    store_provenance,
    log_extraction,
    check_already_extracted,
)

router = APIRouter()


# ── Static gap definitions (from Master Brain strategic review) ──
GAPS = [
    {
        "id": "GAP1",
        "title": "Patent landscape",
        "severity": "showstopper",
        "status": "partially_filled",
        "description": (
            "Comprehensive coverage of vision-correction-display patent prior art. "
            "Currently filled with academic proxies; needs real patent data once "
            "PatentsView/USPTO ODP API key is active."
        ),
        "suggested_queries": [
            "vision correction display patent",
            "computational aberration correction display",
            "pre-distorted display refractive correction",
        ],
        "suggested_mode": "patents",
    },
    {
        "id": "GAP2",
        "title": "Ophthalmology",
        "severity": "showstopper",
        "status": "filled",
        "description": "Refractive errors, accommodation, optical biology. Coverage achieved (150+ nodes).",
        "suggested_queries": [
            "presbyopia accommodation",
            "myopia refractive error",
            "Zernike polynomial wavefront ocular",
        ],
        "suggested_mode": "academic",
    },
    {
        "id": "GAP3",
        "title": "Psychophysics / Perception",
        "severity": "showstopper",
        "status": "partially_filled",
        "description": (
            "Visual perception thresholds, contrast sensitivity, retinal sampling. "
            "50+ nodes added; deeper coverage of Stiles–Crawford, MTF limits, and "
            "supra-threshold perception still needed."
        ),
        "suggested_queries": [
            "contrast sensitivity function display",
            "Stiles-Crawford effect retinal",
            "perceptual sharpness deconvolution display",
        ],
        "suggested_mode": "academic",
    },
    {
        "id": "GAP4",
        "title": "Quantitative limits of pre-distortion",
        "severity": "critical",
        "status": "open",
        "description": (
            "What are the achievable diopter-correction ranges and SNR penalties "
            "for software-only pre-distortion? Hard physics limits not yet researched."
        ),
        "suggested_queries": [
            "PSF deconvolution limit display",
            "computational vision correction diopter range",
            "Wiener deconvolution noise amplification display",
        ],
        "suggested_mode": "academic",
    },
    {
        "id": "GAP5",
        "title": "Real-time processing architecture",
        "severity": "critical",
        "status": "open",
        "description": (
            "Latency, compute, and pipeline architecture for live per-frame "
            "vision correction. GPU/NPU feasibility, foveation strategies."
        ),
        "suggested_queries": [
            "real-time deconvolution GPU display",
            "low-latency display pipeline foveated",
            "neural rendering vision correction realtime",
        ],
        "suggested_mode": "academic",
    },
    {
        "id": "GAP6",
        "title": "Regulatory classification",
        "severity": "strategic",
        "status": "open",
        "description": (
            "Whether vision-correcting displays qualify as Class I/II medical "
            "devices in US/EU/JP. Affects go-to-market significantly."
        ),
        "suggested_queries": [
            "FDA medical device class II vision",
            "MDR EU display medical classification",
            "consumer optical aid regulation",
        ],
        "suggested_mode": "all",
    },
]


# ── Request/response models ───────────────────────────────
class PreviewRequest(BaseModel):
    query: str
    mode: Literal["academic", "patents", "all"] = "academic"
    limit: int = 8
    year_range: Optional[str] = None
    min_citations: int = 0


class ExtractRequest(BaseModel):
    paper_id: str
    context: str = ""
    force: bool = False


class PatentLookupRequest(BaseModel):
    patent_numbers: list[str]


def _serialize_result(r: SourceResult) -> dict:
    """Convert a SourceResult dataclass to a JSON-friendly dict (stripping raw_data)."""
    d = asdict(r)
    d.pop("raw_data", None)
    return d


# ── Routes ────────────────────────────────────────────────
@router.get("/gaps")
def list_gaps():
    return {"gaps": GAPS}


@router.post("/preview")
async def preview_search(req: PreviewRequest):
    """Read-only multi-tier search. Returns ranked SourceResults."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Empty query.")

    def _run():
        try:
            if req.mode == "academic":
                return search_academic(
                    req.query,
                    limit_per_source=req.limit,
                    year_range=req.year_range,
                    min_citations=req.min_citations,
                )
            if req.mode == "patents":
                return search_patents(
                    req.query,
                    limit_per_source=req.limit,
                    year_range=req.year_range,
                )
            return search_all(
                req.query,
                limit_per_source=req.limit,
                year_range=req.year_range,
                min_citations=req.min_citations,
            )
        except Exception as e:
            print(f"[research/preview] {e}", file=sys.stderr)
            raise

    try:
        results = await asyncio.to_thread(_run)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "count": len(results),
        "results": [_serialize_result(r) for r in results],
    }


@router.post("/lookup-patents")
async def lookup_patents(req: PatentLookupRequest):
    """Direct lookup of specific patent numbers. Read-only."""
    results = await asyncio.to_thread(lookup_known_patents, req.patent_numbers)
    return {
        "count": len(results),
        "results": [_serialize_result(r) for r in results],
    }


@router.post("/extract")
async def extract(req: ExtractRequest):
    """Stream the extraction pipeline as SSE events.

    Stages: metadata → already-extracted check → pdf-download → epistemic-filter
            → store-nodes → done.

    MUTATES the Knowledge Base. Caller must have presented a confirmation
    gate to the user before invoking this endpoint.
    """
    paper_id = req.paper_id.strip()
    if not paper_id:
        raise HTTPException(status_code=400, detail="Missing paper_id.")

    def _sse(event: str, data: dict):
        return {"event": event, "data": json.dumps(data)}

    async def event_stream():
        try:
            venture_id = await asyncio.to_thread(get_venture_id)
        except Exception as e:
            yield _sse("error", {"message": f"KB unavailable: {e}"})
            return

        # Stage 1: metadata
        yield _sse("stage", {"name": "metadata", "message": "Fetching paper metadata…"})
        metadata = await asyncio.to_thread(get_paper_metadata, paper_id)
        source_url = metadata.get("url") or paper_id
        yield _sse(
            "metadata",
            {
                "title": metadata.get("title"),
                "authors": metadata.get("authors", [])[:8],
                "year": metadata.get("year"),
                "url": source_url,
            },
        )

        # Stage 2: already-extracted check
        if not req.force:
            already = await asyncio.to_thread(
                check_already_extracted, venture_id, source_url
            )
            if already:
                yield _sse(
                    "skipped",
                    {
                        "message": "Paper already extracted. Pass force=true to re-extract.",
                        "url": source_url,
                    },
                )
                yield _sse("done", {"stop_reason": "already_extracted"})
                return

        # Stage 3: PDF download
        yield _sse("stage", {"name": "download", "message": "Downloading PDF…"})
        pdf_path = await asyncio.to_thread(download_pdf, paper_id)
        if not pdf_path:
            await asyncio.to_thread(
                log_extraction,
                venture_id,
                source_url,
                status="failed",
                error_message="PDF download failed",
            )
            yield _sse("error", {"message": "PDF download failed."})
            return
        yield _sse("downloaded", {"path": str(pdf_path)})

        # Stage 4: Epistemic Filter
        yield _sse(
            "stage",
            {
                "name": "epistemic_filter",
                "message": "Running Epistemic Filter (30–60s)…",
            },
        )
        response = await asyncio.to_thread(
            extract_from_pdf, str(pdf_path), req.context
        )

        if not response.success:
            await asyncio.to_thread(
                log_extraction,
                venture_id,
                source_url,
                status="failed",
                error_message=response.error,
                cost_input_tokens=response.input_tokens,
                cost_output_tokens=response.output_tokens,
            )
            yield _sse(
                "error",
                {"message": f"Extraction failed: {response.error}"},
            )
            return

        if not response.parsed:
            await asyncio.to_thread(
                log_extraction,
                venture_id,
                source_url,
                status="failed",
                error_message="JSON parse failed",
                cost_input_tokens=response.input_tokens,
                cost_output_tokens=response.output_tokens,
            )
            yield _sse(
                "error",
                {"message": "Could not parse JSON response from the model."},
            )
            return

        nodes_data = response.parsed.get("nodes", [])
        source_summary = response.parsed.get("source_summary", "")
        source_type = response.parsed.get("source_type", "academic_paper")

        yield _sse(
            "extracted",
            {
                "node_count": len(nodes_data),
                "summary": source_summary,
                "model": response.model,
                "duration_ms": response.duration_ms,
                "cost_usd": round(response.cost_estimate, 4),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                # Preview of each node (label + summary) so the UI can render
                # what's about to be stored
                "nodes_preview": [
                    {
                        "epistemic_label": n.get("epistemic_label"),
                        "summary": n.get("summary") or n.get("content", "")[:120],
                        "domain": n.get("domain"),
                        "confidence": n.get("confidence"),
                    }
                    for n in nodes_data
                ],
            },
        )

        # Stage 5: Store
        yield _sse("stage", {"name": "store", "message": "Storing nodes in KB…"})
        stored = 0
        errors: list[str] = []

        def _store_one(node_data: dict):
            node = store_node(
                venture_id=venture_id,
                epistemic_label=node_data.get(
                    "epistemic_label", "cognitive_framework"
                ),
                content=node_data.get("content", ""),
                summary=node_data.get("summary"),
                confidence=node_data.get("confidence", 50),
                decay_rate=node_data.get("decay_rate", 365),
                domain=node_data.get("domain"),
                tags=node_data.get("tags", []),
                created_by="extraction_engine",
            )
            if node:
                store_provenance(
                    node_id=node["id"],
                    source_type=source_type,
                    source_url=source_url,
                    source_title=metadata.get("title"),
                    source_authors=metadata.get("authors", []),
                    source_doi=metadata.get("arxiv_id"),
                    source_year=metadata.get("year"),
                    credibility_tier="tier1_academic",
                )
            return node

        for i, node_data in enumerate(nodes_data, 1):
            try:
                node = await asyncio.to_thread(_store_one, node_data)
                if node:
                    stored += 1
                    yield _sse(
                        "stored",
                        {
                            "index": i,
                            "total": len(nodes_data),
                            "node_id": node.get("id"),
                            "summary": node_data.get("summary")
                            or node_data.get("content", "")[:120],
                        },
                    )
            except Exception as e:
                errors.append(str(e))

        # Log
        await asyncio.to_thread(
            log_extraction,
            venture_id,
            source_url,
            source_type=source_type,
            status="completed",
            nodes_created=stored,
            cost_input_tokens=response.input_tokens,
            cost_output_tokens=response.output_tokens,
            processing_time_ms=response.duration_ms,
        )

        yield _sse(
            "done",
            {
                "stop_reason": "completed",
                "stored": stored,
                "errors": errors,
                "cost_usd": round(response.cost_estimate, 4),
                "duration_seconds": round(response.duration_ms / 1000, 1),
            },
        )

    return EventSourceResponse(event_stream())
