"""
FastAPI backend for the Disruptive AI Ecosystem web UI.

Wraps the existing core/ and agents/ modules without modifying them.
Run from the project root:
    uvicorn web.api.main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path

# Ensure project root is on path so `from core.kb import ...` works
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web.api.routes import kb as kb_routes
from web.api.routes import chat as chat_routes
from web.api.routes import meta as meta_routes
from web.api.routes import research as research_routes


app = FastAPI(
    title="Disruptive AI Ecosystem API",
    description="Web API for the autonomous research ecosystem.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_routes.router, prefix="/api", tags=["meta"])
app.include_router(kb_routes.router, prefix="/api/kb", tags=["kb"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["chat"])
app.include_router(research_routes.router, prefix="/api/research", tags=["research"])


@app.get("/")
def root():
    return {"status": "ok", "service": "disruptive-ai-ecosystem"}
