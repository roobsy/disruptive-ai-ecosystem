# CLAUDE.md — Autonomous Disruptive Intelligence Ecosystem

## Project Overview

This is an **Autonomous Disruptive Intelligence Ecosystem** — an AI-powered research and strategic analysis platform. It autonomously discovers, extracts, labels, and stores knowledge from academic papers, patents, and web sources, then reasons across that knowledge to drive venture strategy.

The system is designed as a **venture-agnostic platform** — currently applied to a Vision Correction Display venture, but architectured to serve multiple ventures (Partners PropTech, Sparked, Homega Living) as separate tenants.

## Architecture (from the Conceptual Design Document v2.1)

### Hierarchy
- **Tier 0 — Master Brain**: Global orchestrator, cross-domain reasoning, strategic reviews, gap detection
- **Tier 1 — Domain Agents**: Specialized agents (Optics, Ophthalmology, etc.) with deep domain knowledge
- **Tier 2 — Helper Agents**: Research Agent, Extraction Agent (task-specific workers)

### Core Concepts
- **Prime Directive**: The supreme venture-specific goal. Current: "Identify and validate a commercially viable, patent-clear method for correcting refractive vision errors through display technology."
- **Knowledge Base (KB)**: Supabase PostgreSQL database storing epistemically labeled knowledge nodes
- **Epistemic Labels**: Every knowledge node is classified as Axiomatic Fact, Experimental Result, or Cognitive Framework
- **Confidence Scoring**: 0-100 with conviction decay (half-life)
- **Knowledge Lifecycle**: Discovery → Under Evaluation → Validated → Contested → Superseded → Ruled Out

### Data Acquisition Architecture (4 Tiers)
- **Tier 1 — Academic APIs**: Semantic Scholar, OpenAlex, CrossRef, PubMed, Unpaywall, ArXiv
- **Tier 2 — Patent APIs**: Google Patents (lookup), PatentsView (awaiting USPTO ODP key), EPO (optional)
- **Tier 3 — Semi-Structured**: IEEE Xplore (key pending activation), SPIE (web scraping)
- **Tier 4 — Web Scraper**: Rate-limited, robots.txt-respecting fallback

### Research Loop
Master Brain identifies gaps → Research Agent generates search queries → Source Router discovers papers across all tiers → Claude ranks by relevance → Epistemic Filter extracts and labels knowledge → KB stores nodes with provenance

## File Structure

```
ecosystem/
├── agents/
│   ├── __init__.py
│   ├── master_brain.py      # Tier 0 orchestrator
│   ├── domain_agent.py      # Base DomainAgent + OpticsAgent
│   └── research_agent.py    # Autonomous paper/patent discovery & extraction
├── core/
│   ├── __init__.py
│   ├── kb.py                # Supabase CRUD operations (Knowledge Base)
│   ├── epistemic_filter.py  # Claude-based extraction + epistemic labeling
│   └── model_router.py      # Standardized Claude API interface
├── extraction/
│   ├── __init__.py
│   ├── source_interface.py  # SourceResult contract for all sources
│   ├── source_router.py     # Multi-tier orchestrator with dedup + enrichment
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── semantic_scholar.py  # 200M+ papers, API key authenticated
│   │   ├── openalex.py          # 250M+ works, free unlimited
│   │   ├── crossref.py          # 130M+ DOI works
│   │   ├── pubmed.py            # 36M+ biomedical citations
│   │   ├── unpaywall.py         # Open access PDF finder
│   │   ├── arxiv.py             # Preprint download
│   │   ├── patents_view.py      # USPTO search (awaiting key)
│   │   ├── epo.py               # European patents (optional key)
│   │   ├── google_patents.py    # Direct patent lookup by number
│   │   ├── ieee.py              # IEEE Xplore (key pending activation)
│   │   ├── spie.py              # SPIE web scraping
│   │   └── web_scraper.py       # Tier 4 fallback
│   └── parsers/
│       ├── __init__.py
│       └── document_processor.py  # PDF/HTML/LaTeX extraction + validation
├── scripts/
│   ├── __init__.py
│   ├── master_brain.py      # Interactive Master Brain CLI
│   ├── ask_agent.py         # Interactive Domain Agent CLI
│   ├── research.py          # Autonomous research CLI
│   ├── extract_paper.py     # Single paper extraction
│   └── batch_extract.py     # Batch paper extraction
├── data/
│   └── papers/              # Downloaded PDFs
├── .env                     # API keys (never commit)
├── .env.example             # Template for API keys
└── requirements.txt         # Python dependencies
```

## CRITICAL Conventions

### File Naming
- **The KB module is `core/kb.py` (LOWERCASE)**. Windows keeps normalizing this. All imports MUST use `from core.kb import ...`. NEVER use `core.KB` or `core.knowledge_spine`.
- When creating new files that import the KB, always use: `from core.kb import get_nodes, get_venture_id, get_stats, store_node, store_provenance, log_extraction, check_already_extracted`

### Terminology
- Use **"Knowledge Base"** or **"KB"** everywhere. Never "knowledge spine" or "spine".
- The database stores **"nodes"** (knowledge_nodes table), not "entries" or "records".
- Use **"Epistemic Filter"** for the Claude-based extraction system.
- Use **"Source Router"** for the multi-tier search orchestrator.

### Model Usage
- **Sonnet** (`claude-sonnet-4-6`): 90% of operations — extraction, labeling, query generation, ranking
- **Opus** (`claude-opus-4-6`): 10% — Master Brain strategic reviews, idea assessments, complex reasoning
- Route via `model_router.py` with `complexity="standard"` (Sonnet) or `complexity="complex"` (Opus)
- NEVER call the Anthropic API directly — always go through `model_router.execute()`

### API Keys & Rate Limits
- **Anthropic**: `ANTHROPIC_API_KEY` — main Claude API
- **Supabase**: `SUPABASE_URL` + `SUPABASE_KEY` — KB storage
- **Semantic Scholar**: `SEMANTIC_SCHOLAR_API_KEY` — 1 request/second, header: `x-api-key`
- **IEEE Xplore**: `IEEE_API_KEY` — 10 calls/sec, 200/day, param: `apikey` (pending activation)
- **PatentsView**: `PATENTSVIEW_API_KEY` — registration suspended, migrating to USPTO ODP
- **EPO**: `EPO_CONSUMER_KEY` + `EPO_CONSUMER_SECRET` — optional, OAuth2

### Error Handling Patterns
- All source API clients return empty lists on error (never raise)
- Source Router deduplicates across all sources by DOI, ArXiv ID, patent number, and fuzzy title
- PDF downloads are validated with `%PDF` header check before processing
- Invalid downloads (HTML landing pages) are automatically cleaned up
- Research Agent falls back from full PDF → abstract extraction when PDFs aren't available
- Ranking falls back to top-N by citation count if Claude's JSON response can't be parsed

## Current State (as of April 5, 2026)

### Knowledge Base
- **481 total nodes** across 19 domains
- Key venture-relevant domains: Ophthalmology (150), Computer Science (79), Display Technology (54), Video Quality Assessment (30), Optics (24), Neuroscience (13)
- Off-mission domains to clean: particle_physics_instrumentation (29), lattice_field_theory (13), quantum_field_theory (12)
- Epistemic breakdown: 118 Axiomatic Facts, 167 Experimental Results, 196 Cognitive Frameworks
- Average confidence: 75.5

### Research Gaps (from Master Brain Strategic Review)
- **GAP1** (SHOWSTOPPER): Patent landscape — partially filled with academic papers, need actual patent data once PatentsView/ODP key arrives
- **GAP2** (SHOWSTOPPER): Ophthalmology — FILLED (150 nodes now)
- **GAP3** (SHOWSTOPPER): Psychophysics/perception — partially filled (50+ new nodes)
- **GAP4** (CRITICAL): Quantitative limits of pre-distortion — not yet researched
- **GAP5** (CRITICAL): Real-time processing architecture — not yet researched
- **GAP6** (STRATEGIC): Regulatory classification — not yet researched

### Solution Paths (from Master Brain)
- **Path A**: Software PSF deconvolution (pure software, limited to ~±2-4D)
- **Path B**: Light field / microlens hybrid (Rabbit Eyes approach)
- **Path C**: Tunable optics layer on display
- **Path D**: Hybrid computational + optical (Master Brain's recommended path)
- **Path E**: Personalized subpixel rendering
- Key competitor: Rabbit Eyes (Rotterdam), US Patent 12,141,346

### What's Working
- ✅ All Tier 1 academic APIs (Semantic Scholar, OpenAlex, CrossRef, PubMed, Unpaywall, ArXiv)
- ✅ Google Patents direct lookup
- ✅ Web scraper (Tier 4)
- ✅ PDF text extraction (PyMuPDF)
- ✅ PDF validation (header check)
- ✅ DOI-based paper extraction via Unpaywall
- ✅ Abstract fallback extraction when PDFs unavailable
- ✅ Source Router with multi-tier dedup and Unpaywall enrichment
- ✅ Research Agent autonomous loop (query gen → discovery → ranking → extraction)
- ✅ Master Brain strategic reviews and idea assessment
- ✅ Optics Domain Agent
- ✅ Interactive CLIs for Master Brain and Domain Agents

### What's Pending
- ⏳ PatentsView API key (USPTO ODP ID.me verification in progress)
- ⏳ IEEE Xplore API key activation (submitted, awaiting US business hours approval)
- ⏳ EPO registration (optional)
- ❌ KB cleanup (remove off-mission nodes)
- ❌ Master Brain second strategic review (with enriched 481-node KB)
- ❌ Phase 3: Sandbox + Dialectic Engine (LangGraph workflows)
- ❌ Phase 4: Sovereign Dashboard (React) + Notifications
- ❌ Semantic search (vector embeddings in Supabase pgvector)
- ❌ n8n deployment on VPS for scheduled research automation

## Supabase Schema

### Tables
- `ventures` — venture registry (id, name, prime_directive, status)
- `knowledge_nodes` — KB entries (id, venture_id, epistemic_label, content, summary, confidence, decay_rate, domain, tags, lifecycle_state, created_by)
- `provenance` — source tracking per node (node_id, source_type, source_url, source_title, source_authors, source_doi, source_year, credibility_tier, extraction_agent)
- `extraction_log` — extraction history (venture_id, source_url, status, nodes_created, cost tracking)
- `agent_state` — agent state persistence

### Active Venture
- Name: "Vision Correction Display"
- Set via `ACTIVE_VENTURE` in .env

## Development Environment
- **OS**: Windows 11
- **IDE**: Cursor
- **Python**: 3.14 (via uv)
- **Package Manager**: uv (`uv pip install -r requirements.txt`)
- **Virtual Environment**: `ecosystem` venv in project directory
- **Project Path**: `C:\Users\RubenDrong\Google Drive\Ventures\AI\Disruptive_AI_Ecosystem\Docs\Packages\ecosystem_phase0\ecosystem\`

## Common Commands

```bash
# Activate venv (PowerShell)
.\.venv\Scripts\Activate.ps1

# Clear Python caches (do this after file changes)
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# Research commands
python -m scripts.research --priorities           # Show gap priorities
python -m scripts.research --search "query"       # Preview search (no extraction)
python -m scripts.research --patents "query"       # Patent search preview
python -m scripts.research --search-all "query"    # All tiers preview
python -m scripts.research --lookup US12141346     # Direct patent lookup
python -m scripts.research --gap-id GAP2           # Research a specific gap
python -m scripts.research --auto                  # Auto-research all SHOWSTOPPER gaps

# Master Brain
python -m scripts.master_brain                     # Interactive mode
python -m scripts.master_brain --review            # Strategic review
python -m scripts.master_brain --assess "idea"     # Evaluate an idea

# Domain Agent
python -m scripts.ask_agent                        # Interactive optics agent

# Single paper extraction
python -m scripts.extract_paper 2501.01450 --context "Vision correction display"

# Check KB status
python -c "from core.kb import get_stats, get_venture_id; print(get_stats(get_venture_id()))"
```

## Key Design Decisions
1. **Single model provider (Anthropic)** — Sonnet for 90%, Opus for 10%. No multi-model complexity yet.
2. **Supabase over local storage** — PostgreSQL + pgvector expansion path. Free tier sufficient.
3. **APIs first, scraping last** — Ethical data acquisition. Rate limits respected everywhere.
4. **PDF validation before processing** — Prevents wasting API tokens on HTML landing pages.
5. **Abstract fallback** — When PDFs aren't available, extract from abstract text (limited but non-zero value).
6. **Citation-count fallback for ranking** — When Claude's JSON ranking fails, select top papers by citations.
7. **All imports through model_router** — Never call Anthropic API directly from agents.

## Budget
- Target: Under $100/month total
- Claude API: ~$55-85/month (Sonnet ~$0.01-0.06 per extraction, Opus ~$0.40-0.60 per review)
- Supabase: Free tier
- VPS (future): ~$5-10/month for n8n
- All source APIs: Free tiers
