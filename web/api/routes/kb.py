"""Knowledge Base endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.kb import get_stats, get_nodes, get_venture_id

router = APIRouter()


class NodeFilter(BaseModel):
    domain: Optional[str] = None
    epistemic_label: Optional[str] = None
    lifecycle_state: Optional[str] = None
    min_confidence: float = 0
    limit: int = 50


def _venture_id() -> str:
    try:
        return get_venture_id()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"KB not available: {e}")


@router.get("/stats")
def stats():
    vid = _venture_id()
    try:
        s = get_stats(vid)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return s


@router.get("/nodes")
def list_nodes(
    domain: Optional[str] = None,
    epistemic_label: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    min_confidence: float = 0,
    limit: int = Query(50, ge=1, le=500),
):
    vid = _venture_id()
    try:
        nodes = get_nodes(
            vid,
            domain=domain,
            epistemic_label=epistemic_label,
            lifecycle_state=lifecycle_state,
            min_confidence=min_confidence,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"nodes": nodes, "count": len(nodes)}
