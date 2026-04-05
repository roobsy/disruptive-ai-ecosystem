"""
KB (Knowledge Base) — Supabase Operations
==========================================
Handles all reads and writes to the knowledge database.
This is the single access point for persistent storage.
"""

import os
from typing import Optional
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ── Client singleton ──────────────────────────────────────
_sb: Optional[Client] = None

def get_supabase() -> Client:
    global _sb
    if _sb is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _sb = create_client(url, key)
    return _sb


# ── Venture operations ────────────────────────────────────
def get_venture_id(venture_name: str = None) -> str:
    """Get the venture ID by name. Defaults to ACTIVE_VENTURE from .env."""
    name = venture_name or os.getenv("ACTIVE_VENTURE", "Vision Correction Display")
    sb = get_supabase()
    result = sb.table("ventures").select("id").eq("name", name).execute()
    if not result.data:
        raise ValueError(f"Venture '{name}' not found. Run setup_supabase.sql first.")
    return result.data[0]["id"]


# ── Knowledge node operations ─────────────────────────────
def store_node(
    venture_id: str,
    epistemic_label: str,
    content: str,
    summary: str = None,
    confidence: float = 50.0,
    decay_rate: float = 365.0,
    domain: str = None,
    tags: list = None,
    lifecycle_state: str = "under_evaluation",
    created_by: str = "extraction_engine",
    metadata: dict = None,
) -> dict:
    """Store a single knowledge node in the KB."""
    sb = get_supabase()
    data = {
        "venture_id": venture_id,
        "epistemic_label": epistemic_label,
        "lifecycle_state": lifecycle_state,
        "confidence": confidence,
        "decay_rate": decay_rate,
        "content": content,
        "summary": summary or content[:100],
        "domain": domain,
        "tags": tags or [],
        "created_by": created_by,
        "metadata": metadata or {},
    }
    result = sb.table("knowledge_nodes").insert(data).execute()
    return result.data[0] if result.data else {}


def store_provenance(
    node_id: str,
    source_type: str,
    source_url: str = None,
    source_title: str = None,
    source_authors: list = None,
    source_doi: str = None,
    source_year: int = None,
    credibility_tier: str = "tier1_academic",
    extraction_agent: str = "extraction_engine",
    metadata: dict = None,
) -> dict:
    """Store provenance information for a knowledge node."""
    sb = get_supabase()
    data = {
        "node_id": node_id,
        "source_type": source_type,
        "source_url": source_url,
        "source_title": source_title,
        "source_authors": source_authors or [],
        "source_doi": source_doi,
        "source_year": source_year,
        "credibility_tier": credibility_tier,
        "extraction_agent": extraction_agent,
        "metadata": metadata or {},
    }
    result = sb.table("provenance").insert(data).execute()

    # Link provenance back to the node
    if result.data:
        prov_id = result.data[0]["id"]
        sb.table("knowledge_nodes").update(
            {"source_id": prov_id}
        ).eq("id", node_id).execute()

    return result.data[0] if result.data else {}


def log_extraction(
    venture_id: str,
    source_url: str,
    source_type: str = "academic_paper",
    status: str = "pending",
    nodes_created: int = 0,
    error_message: str = None,
    cost_input_tokens: int = 0,
    cost_output_tokens: int = 0,
    processing_time_ms: int = 0,
) -> dict:
    """Log an extraction attempt."""
    sb = get_supabase()
    data = {
        "venture_id": venture_id,
        "source_url": source_url,
        "source_type": source_type,
        "status": status,
        "nodes_created": nodes_created,
        "error_message": error_message,
        "cost_input_tokens": cost_input_tokens,
        "cost_output_tokens": cost_output_tokens,
        "processing_time_ms": processing_time_ms,
    }
    if status in ("completed", "failed"):
        data["completed_at"] = datetime.now(timezone.utc).isoformat()

    result = sb.table("extraction_log").upsert(
        data, on_conflict="venture_id,source_url"
    ).execute()
    return result.data[0] if result.data else {}


def check_already_extracted(venture_id: str, source_url: str) -> bool:
    """Check if a URL has already been successfully extracted."""
    sb = get_supabase()
    result = sb.table("extraction_log").select("status").eq(
        "venture_id", venture_id
    ).eq("source_url", source_url).eq("status", "completed").execute()
    return len(result.data) > 0


# ── Query operations ──────────────────────────────────────
def get_nodes(
    venture_id: str,
    domain: str = None,
    epistemic_label: str = None,
    min_confidence: float = 0,
    lifecycle_state: str = None,
    limit: int = 50,
) -> list:
    """Query knowledge nodes with filters."""
    sb = get_supabase()
    query = sb.table("knowledge_nodes").select("*").eq("venture_id", venture_id)

    if domain:
        query = query.eq("domain", domain)
    if epistemic_label:
        query = query.eq("epistemic_label", epistemic_label)
    if lifecycle_state:
        query = query.eq("lifecycle_state", lifecycle_state)
    if min_confidence > 0:
        query = query.gte("confidence", min_confidence)

    query = query.order("confidence", desc=True).limit(limit)
    result = query.execute()
    return result.data


def get_stats(venture_id: str) -> dict:
    """Get summary statistics for the KB."""
    sb = get_supabase()
    nodes = sb.table("knowledge_nodes").select(
        "epistemic_label, lifecycle_state, domain, confidence"
    ).eq("venture_id", venture_id).execute()

    if not nodes.data:
        return {"total": 0}

    data = nodes.data
    stats = {
        "total": len(data),
        "by_label": {},
        "by_state": {},
        "by_domain": {},
        "avg_confidence": sum(n["confidence"] for n in data) / len(data),
    }

    for n in data:
        label = n["epistemic_label"]
        state = n["lifecycle_state"]
        domain = n.get("domain", "unknown")
        stats["by_label"][label] = stats["by_label"].get(label, 0) + 1
        stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
        stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1

    return stats
