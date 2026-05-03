"""Meta endpoints — venture info, health, environment."""

import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")),
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "active_venture": os.getenv("ACTIVE_VENTURE", "Vision Correction Display"),
    }


@router.get("/venture")
def venture():
    """Return the active venture profile."""
    return {
        "name": os.getenv("ACTIVE_VENTURE", "Vision Correction Display"),
        "prime_directive": (
            "Identify and validate a commercially viable, patent-clear method for "
            "correcting refractive vision errors through display technology."
        ),
    }
