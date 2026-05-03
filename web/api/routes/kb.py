"""Knowledge Base endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.kb import get_stats, get_nodes, get_venture_id, get_supabase

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


@router.get("/node/{node_id}")
def node_detail(node_id: str):
    """Return a single node with its full content and any linked provenance."""
    vid = _venture_id()
    sb = get_supabase()
    try:
        node_q = (
            sb.table("knowledge_nodes")
            .select("*")
            .eq("id", node_id)
            .eq("venture_id", vid)
            .execute()
        )
        if not node_q.data:
            raise HTTPException(status_code=404, detail="Node not found.")
        node = node_q.data[0]

        prov_q = (
            sb.table("provenance")
            .select("*")
            .eq("node_id", node_id)
            .execute()
        )
        provenance = prov_q.data or []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"node": node, "provenance": provenance}
