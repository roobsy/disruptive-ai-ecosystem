"use client";

import { useEffect, useMemo, useState } from "react";
import { api, KBNode, KBStats } from "@/lib/api";
import { NodeFilters, Filters, DEFAULT_FILTERS } from "./node-filters";
import { NodeTable } from "./node-table";
import { NodeDetail } from "./node-detail";
import { emitChatMessage } from "@/lib/chat-bus";
import { Sparkles } from "lucide-react";

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function KBPage() {
  const [stats, setStats] = useState<KBStats | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [nodes, setNodes] = useState<KBNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Stats are loaded once for the domains dropdown + total count
  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
  }, []);

  // Server-side filterable params (label/state/domain/min_conf/limit) trigger
  // a refetch. The free-text search is applied client-side on the result.
  const debouncedFilters = useDebounced(filters, 200);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .nodes({
        domain: debouncedFilters.domain,
        epistemic_label: debouncedFilters.epistemic_label,
        lifecycle_state: debouncedFilters.lifecycle_state,
        min_confidence: debouncedFilters.min_confidence,
        limit: debouncedFilters.limit,
      })
      .then((r) => setNodes(r.nodes))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [
    debouncedFilters.domain,
    debouncedFilters.epistemic_label,
    debouncedFilters.lifecycle_state,
    debouncedFilters.min_confidence,
    debouncedFilters.limit,
  ]);

  const domains = useMemo(() => {
    return Object.keys(stats?.by_domain ?? {}).sort();
  }, [stats]);

  const filtered = useMemo(() => {
    const q = filters.search.trim().toLowerCase();
    if (!q) return nodes;
    return nodes.filter((n) => {
      const hay = [
        n.summary,
        n.content,
        n.domain,
        ...(n.tags || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [nodes, filters.search]);

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Knowledge Base</h1>
          <p className="text-sm text-ink-muted mt-0.5">
            Browse, filter, and inspect every node the ecosystem has stored.
          </p>
        </div>
        <button
          onClick={() =>
            emitChatMessage(
              "Summarize the current Knowledge Base — top domains, " +
                "epistemic mix, and any obvious gaps."
            )
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-accent-ring/40 bg-accent-soft px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-soft/80 transition-colors"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Ask the chat to summarize
        </button>
      </div>

      <NodeFilters
        filters={filters}
        onChange={setFilters}
        domains={domains}
        total={stats?.total ?? 0}
        matching={filtered.length}
      />

      {error && (
        <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3">
          {error}
        </div>
      )}

      <NodeTable
        nodes={filtered}
        loading={loading}
        onSelect={(n) => setSelectedId(n.id)}
      />

      <NodeDetail
        nodeId={selectedId}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
