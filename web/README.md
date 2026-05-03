# Web UI — Disruptive AI Ecosystem

A vertical slice: **Dashboard + Chat** with a chat-on-top model where Claude
can call backend tools (KB stats, KB queries) live.

```
web/
├── api/          FastAPI backend wrapping core/ and agents/
└── ui/           Next.js 15 + Tailwind frontend
```

## Stack

- **Backend**: FastAPI, Anthropic SDK with tool use, SSE streaming
- **Frontend**: Next.js 15, React 19, Tailwind CSS, lucide-react
- **Palette**: off-white `#FAFAF9`, ink `#1A1A1A`, soft indigo accent `#6366F1`

## Prerequisites

- Working `.env` at the project root with `ANTHROPIC_API_KEY`, `SUPABASE_URL`,
  `SUPABASE_KEY`, `ACTIVE_VENTURE`. Reuses your existing setup.
- Python 3.11+ and Node.js 20+.

## Run the backend

From the project root:

```bash
# Install backend deps into your existing venv
pip install -r web/api/requirements.txt

# Start the API on :8000
uvicorn web.api.main:app --reload --port 8000
```

Health check: `http://localhost:8000/api/health`

## Run the frontend

In another terminal:

```bash
cd web/ui
npm install
npm run dev
```

Open `http://localhost:3000`. The UI proxies `/api/backend/*` to the FastAPI
server, so no extra config is needed.

## What's wired

**Dashboard**
- Live KB stats (total nodes, average confidence, domain count, solution paths)
- Epistemic composition bar (axiomatic / experimental / framework)
- Domain coverage list with on-mission vs off-mission flagging
- Research gaps (GAP1–GAP6) and solution paths (A–E)

**Chat panel** (right rail)
- Streams tokens via SSE
- Renders Claude tool calls as collapsible cards (input + output)
- Tools available to the model:
  - `kb_stats` → `core.kb.get_stats`
  - `kb_query` → `core.kb.get_nodes` (filterable)

Add a tool by editing `web/api/tools.py` — append a schema to `TOOL_SCHEMAS`
and a handler to `TOOL_HANDLERS`. The chat picks it up immediately.

## Next surfaces (not yet built)

Knowledge Base browser, Research runner with live extraction stream, Master
Brain (review / assess), Domain Agents chat, Sources health, Settings.
Each maps to one nav item in the sidebar.
