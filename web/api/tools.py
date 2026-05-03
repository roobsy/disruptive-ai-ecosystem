"""
Tool definitions for the chat agent.

Each tool exposes a backend capability to Claude. Adding a tool here
makes it instantly invocable from the chat panel.
"""

from typing import Callable
from core.kb import get_stats, get_nodes, get_venture_id


def _venture_id() -> str:
    return get_venture_id()


def tool_kb_stats(_args: dict) -> dict:
    return get_stats(_venture_id())


def tool_kb_query(args: dict) -> dict:
    nodes = get_nodes(
        _venture_id(),
        domain=args.get("domain"),
        epistemic_label=args.get("epistemic_label"),
        lifecycle_state=args.get("lifecycle_state"),
        min_confidence=float(args.get("min_confidence", 0)),
        limit=int(args.get("limit", 10)),
    )
    return {
        "count": len(nodes),
        "nodes": [
            {
                "id": n.get("id"),
                "summary": n.get("summary"),
                "epistemic_label": n.get("epistemic_label"),
                "domain": n.get("domain"),
                "confidence": n.get("confidence"),
                "lifecycle_state": n.get("lifecycle_state"),
            }
            for n in nodes
        ],
    }


def _format_agent_response(resp) -> dict:
    """Convert a core.model_router.AgentResponse into a tool-friendly dict."""
    return {
        "success": resp.success,
        "content": resp.content if resp.success else None,
        "error": resp.error,
        "model": resp.model,
        "duration_ms": resp.duration_ms,
        "duration_seconds": round(resp.duration_ms / 1000, 1),
        "cost_usd": round(resp.cost_estimate, 4),
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
    }


def tool_master_brain_review(_args: dict) -> dict:
    from agents.master_brain import MasterBrain
    mb = MasterBrain()
    return _format_agent_response(mb.strategic_review())


def tool_master_brain_assess(args: dict) -> dict:
    idea = (args.get("idea") or "").strip()
    if not idea:
        return {"success": False, "error": "Missing 'idea' argument."}
    from agents.master_brain import MasterBrain
    mb = MasterBrain()
    return _format_agent_response(mb.assess_idea(idea))


# ── Schemas exposed to Claude ─────────────────────────────
TOOL_SCHEMAS = [
    {
        "name": "kb_stats",
        "description": (
            "Return summary statistics for the Knowledge Base: total node count, "
            "breakdown by epistemic label, lifecycle state, domain, and average confidence. "
            "Use this when the user asks about the overall state of the KB. Fast and free."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "kb_query",
        "description": (
            "Query knowledge nodes with optional filters. Returns up to `limit` nodes "
            "ordered by confidence (descending). Use when the user wants to inspect "
            "specific knowledge — e.g. 'show me high-confidence ophthalmology facts'. "
            "Fast and free."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain filter, e.g. 'ophthalmology', 'optics', 'display_technology'.",
                },
                "epistemic_label": {
                    "type": "string",
                    "enum": ["axiomatic_fact", "experimental_result", "cognitive_framework"],
                },
                "lifecycle_state": {
                    "type": "string",
                    "enum": [
                        "discovery",
                        "under_evaluation",
                        "validated",
                        "contested",
                        "superseded",
                        "ruled_out",
                    ],
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence (0–100).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max nodes to return (default 10, max 50).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "master_brain_review",
        "description": (
            "Run a comprehensive Master Brain strategic review using Opus. Analyzes "
            "the entire KB and returns: per-domain coverage assessment, constraint "
            "map of established physics limits, 3–5 ranked solution hypotheses with "
            "feasibility/patent/competitive analysis, prioritized critical gaps, and "
            "recommended next actions. EXPENSIVE: ~30–90 seconds, ~$0.40–0.60 per "
            "call. Use ONLY when the user explicitly asks for a strategic review or "
            "a comprehensive assessment of the venture. Do NOT call this casually "
            "or to answer narrow questions — use kb_stats and kb_query for those."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "master_brain_assess",
        "description": (
            "Evaluate a specific idea, hypothesis, or solution path against the full "
            "KB using Opus. Returns a structured assessment: thesis (steelman), red "
            "team attack, feasibility, patent risk, verdict, and the single most "
            "important next experiment. EXPENSIVE: ~30–60 seconds, ~$0.30–0.50 per "
            "call. Use when the user proposes a concrete idea or wants something "
            "stress-tested. Do NOT call to answer general questions about the KB."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": (
                        "The idea, hypothesis, or solution path to assess. "
                        "1–3 paragraphs of concrete description."
                    ),
                }
            },
            "required": ["idea"],
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "kb_stats": tool_kb_stats,
    "kb_query": tool_kb_query,
    "master_brain_review": tool_master_brain_review,
    "master_brain_assess": tool_master_brain_assess,
}


def run_tool(name: str, args: dict) -> dict:
    """Execute a tool by name. Returns a JSON-serializable result."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(args or {})
    except Exception as e:
        return {"error": str(e)}
