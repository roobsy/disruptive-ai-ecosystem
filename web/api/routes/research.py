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
from core.kb import get_venture_id

from web.api.extraction_pipeline import ExtractSource, run_extraction

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
    source: ExtractSource
    context: str = ""
    force: bool = False
    require_pdf: bool = False  # if True, skip the abstract-text fallback


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
    """Stream the unified extraction pipeline as SSE events.

    Routes to the right strategy based on what identifiers the source has:
        ArXiv ID → arxiv PDF
        Direct pdf_url → fetch directly
        DOI → Unpaywall lookup → OA PDF
        Patent number → Google Patents PDF
        Otherwise → abstract-text fallback (unless require_pdf is True)

    MUTATES the Knowledge Base. Caller must have presented a confirmation
    gate to the user before invoking this endpoint.
    """
    def _sse(event: str, data: dict):
        return {"event": event, "data": json.dumps(data)}

    async def event_stream():
        try:
            venture_id = await asyncio.to_thread(get_venture_id)
        except Exception as e:
            yield _sse("error", {"message": f"KB unavailable: {e}"})
            return

        try:
            async for event_name, payload in run_extraction(
                source=req.source,
                context=req.context,
                force=req.force,
                require_pdf=req.require_pdf,
                venture_id=venture_id,
            ):
                yield _sse(event_name, payload)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[research/extract] pipeline error:\n{tb}", file=sys.stderr)
            yield _sse("error", {"message": f"{type(e).__name__}: {e}"})

    return EventSourceResponse(event_stream())
