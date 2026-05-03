// Backend client. All requests proxy through Next's /api/backend/* rewrite
// to FastAPI on :8000.

export type KBStats = {
  total: number;
  by_label?: Record<string, number>;
  by_state?: Record<string, number>;
  by_domain?: Record<string, number>;
  avg_confidence?: number;
};

export type KBNode = {
  id: string;
  summary: string;
  content?: string;
  epistemic_label: string;
  domain: string | null;
  confidence: number;
  lifecycle_state: string;
  tags?: string[];
  decay_rate?: number;
  created_by?: string;
  created_at?: string;
  metadata?: Record<string, unknown>;
};

export type Provenance = {
  id: string;
  node_id: string;
  source_type: string;
  source_url: string | null;
  source_title: string | null;
  source_authors: string[] | null;
  source_doi: string | null;
  source_year: number | null;
  credibility_tier: string | null;
  extraction_agent: string | null;
};

export type Gap = {
  id: string;
  title: string;
  severity: "showstopper" | "critical" | "strategic";
  status: "filled" | "partially_filled" | "open";
  description: string;
  suggested_queries: string[];
  suggested_mode: "academic" | "patents" | "all";
};

export type SourceResult = {
  source_type: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  url: string;
  pdf_url: string;
  doi: string;
  arxiv_id: string;
  patent_number: string;
  citation_count: number;
  credibility_tier: string;
  has_open_access: boolean;
  source_api: string;
};

export type Health = {
  status: string;
  supabase_configured: boolean;
  anthropic_configured: boolean;
  active_venture: string;
};

export type Venture = {
  name: string;
  prime_directive: string;
};

const base = "/api/backend";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${base}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

export const api = {
  health: () => get<Health>("/health"),
  venture: () => get<Venture>("/venture"),
  stats: () => get<KBStats>("/kb/stats"),
  nodes: (params: Record<string, string | number> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== "" && v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return get<{ nodes: KBNode[]; count: number }>(
      `/kb/nodes${qs ? "?" + qs : ""}`
    );
  },
  node: (id: string) =>
    get<{ node: KBNode; provenance: Provenance[] }>(`/kb/node/${id}`),

  // Research
  gaps: () => get<{ gaps: Gap[] }>("/research/gaps"),
  preview: async (body: {
    query: string;
    mode?: "academic" | "patents" | "all";
    limit?: number;
    year_range?: string;
    min_citations?: number;
  }) => {
    const r = await fetch(`${base}/research/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`/research/preview → ${r.status}`);
    return r.json() as Promise<{ count: number; results: SourceResult[] }>;
  },
};
