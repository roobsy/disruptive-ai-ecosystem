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
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ).toString();
    return get<{ nodes: KBNode[]; count: number }>(
      `/kb/nodes${qs ? "?" + qs : ""}`
    );
  },
};
