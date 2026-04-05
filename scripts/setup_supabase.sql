-- ============================================================
-- AUTONOMOUS DISRUPTIVE INTELLIGENCE ECOSYSTEM
-- KB (Knowledge Base) Schema — Phase 0
-- ============================================================
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================

-- Enable pgvector extension (for future semantic search)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- VENTURES: Multi-tenant container
-- ============================================================
CREATE TABLE ventures (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    prime_directive TEXT,           -- The venture's North Star
    status          TEXT DEFAULT 'active',
    config          JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- KNOWLEDGE NODES: The core of the KB (knowledge base)
-- ============================================================
CREATE TABLE knowledge_nodes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venture_id      UUID REFERENCES ventures(id) ON DELETE CASCADE,

    -- Epistemic classification
    epistemic_label TEXT NOT NULL CHECK (epistemic_label IN (
        'axiomatic_fact',
        'experimental_result',
        'cognitive_framework',
        'experience_data'
    )),

    -- Lifecycle management
    lifecycle_state TEXT NOT NULL DEFAULT 'discovery' CHECK (lifecycle_state IN (
        'discovery',
        'under_evaluation',
        'under_validation',
        'hypothetical',
        'validated',
        'contested',
        'superseded',
        'ruled_out'
    )),

    -- Confidence and decay
    confidence      REAL DEFAULT 50.0 CHECK (confidence >= 0 AND confidence <= 100),
    decay_rate      REAL DEFAULT 365.0,     -- Half-life in days
    last_decay_at   TIMESTAMPTZ DEFAULT NOW(),

    -- Content
    content         TEXT NOT NULL,           -- The actual claim or fact
    summary         TEXT,                    -- One-line summary
    domain          TEXT,                    -- e.g., 'optics', 'materials', 'patents'
    tags            TEXT[] DEFAULT '{}',

    -- Vector embedding (populated in Phase 1)
    embedding       vector(1536),

    -- Relationships (Neo4j preparation)
    depends_on      UUID[] DEFAULT '{}',
    source_id       UUID,                   -- FK to provenance (set after provenance insert)

    -- Audit trail
    created_by      TEXT DEFAULT 'manual',   -- Agent ID or 'manual'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    validated_at    TIMESTAMPTZ,

    -- Flexible metadata
    metadata        JSONB DEFAULT '{}'
);

-- Index for common queries
CREATE INDEX idx_nodes_venture ON knowledge_nodes(venture_id);
CREATE INDEX idx_nodes_label ON knowledge_nodes(epistemic_label);
CREATE INDEX idx_nodes_state ON knowledge_nodes(lifecycle_state);
CREATE INDEX idx_nodes_domain ON knowledge_nodes(domain);
CREATE INDEX idx_nodes_confidence ON knowledge_nodes(confidence DESC);

-- ============================================================
-- PROVENANCE: Source tracking for every knowledge node
-- ============================================================
CREATE TABLE provenance (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id         UUID REFERENCES knowledge_nodes(id) ON DELETE CASCADE,

    -- Source identification
    source_type     TEXT NOT NULL CHECK (source_type IN (
        'academic_paper',
        'patent',
        'website',
        'experience',
        'sandbox_result',
        'agent_synthesis'
    )),
    source_url      TEXT,
    source_title    TEXT,
    source_authors  TEXT[] DEFAULT '{}',
    source_doi      TEXT,
    source_year     INT,

    -- Quality tracking
    credibility_tier TEXT CHECK (credibility_tier IN (
        'tier1_academic',
        'tier2_patent',
        'tier3_semi_structured',
        'tier4_scraped',
        'tier_experience',
        'tier_sandbox'
    )),

    extraction_date TIMESTAMPTZ DEFAULT NOW(),
    extraction_agent TEXT,                   -- Which agent extracted this

    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_provenance_node ON provenance(node_id);
CREATE INDEX idx_provenance_doi ON provenance(source_doi);

-- Add FK from knowledge_nodes to provenance
ALTER TABLE knowledge_nodes
    ADD CONSTRAINT fk_source
    FOREIGN KEY (source_id) REFERENCES provenance(id);

-- ============================================================
-- EXTRACTION LOG: Track what has been processed
-- ============================================================
CREATE TABLE extraction_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venture_id      UUID REFERENCES ventures(id) ON DELETE CASCADE,
    source_url      TEXT NOT NULL,
    source_type     TEXT,
    status          TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'processing', 'completed', 'failed'
    )),
    nodes_created   INT DEFAULT 0,
    error_message   TEXT,
    cost_input_tokens  INT DEFAULT 0,
    cost_output_tokens INT DEFAULT 0,
    processing_time_ms INT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_extraction_url ON extraction_log(source_url);
CREATE UNIQUE INDEX idx_extraction_unique ON extraction_log(venture_id, source_url);

-- ============================================================
-- AGENT STATE: Agent definitions and performance tracking
-- ============================================================
CREATE TABLE agent_state (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venture_id      UUID REFERENCES ventures(id) ON DELETE CASCADE,
    agent_id        TEXT NOT NULL,            -- e.g., 'master_brain', 'optics'
    agent_tier      INT DEFAULT 1 CHECK (agent_tier IN (0, 1, 2)),
    parent_agent    TEXT,                     -- For Tier 2: which Tier 1 manages them
    display_name    TEXT,
    domain_scope    TEXT,
    system_prompt   TEXT,
    status          TEXT DEFAULT 'active',
    okr_config      JSONB DEFAULT '{}',
    kpi_data        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(venture_id, agent_id)
);

-- ============================================================
-- SEED DATA: Create the first venture
-- ============================================================
INSERT INTO ventures (name, prime_directive, config)
VALUES (
    'Vision Correction Display',
    'Identify and validate a commercially viable, patent-clear method for correcting refractive vision errors through display technology — achieving impeccable results in optical accuracy, user experience, and manufacturability.',
    '{"domains": ["optics", "materials", "display_tech", "ophthalmology", "patents", "manufacturing"]}'::jsonb
);

-- ============================================================
-- HELPER FUNCTION: Apply confidence decay
-- ============================================================
CREATE OR REPLACE FUNCTION apply_confidence_decay()
RETURNS void AS $$
BEGIN
    UPDATE knowledge_nodes
    SET
        confidence = GREATEST(
            1.0,
            confidence * POWER(0.5, EXTRACT(EPOCH FROM (NOW() - last_decay_at)) / (decay_rate * 86400))
        ),
        last_decay_at = NOW(),
        updated_at = NOW()
    WHERE lifecycle_state = 'validated'
      AND decay_rate > 0
      AND last_decay_at < NOW() - INTERVAL '1 day';
END;
$$ LANGUAGE plpgsql;

-- Schedule this via n8n or pg_cron in Phase 2
