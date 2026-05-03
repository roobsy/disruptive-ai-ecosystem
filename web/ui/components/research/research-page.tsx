"use client";

import { useEffect, useState } from "react";
import { api, Gap, SourceResult } from "@/lib/api";
import { GapBoard } from "./gap-board";
import { SearchResults } from "./search-results";
import { ExtractFlow } from "./extract-flow";
import { Search, Sparkles, Telescope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Mode = "academic" | "patents" | "all";

export function ResearchPage() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [selectedGap, setSelectedGap] = useState<Gap | null>(null);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("academic");
  const [limit, setLimit] = useState(8);
  const [results, setResults] = useState<SourceResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractCandidate, setExtractCandidate] = useState<SourceResult | null>(null);

  useEffect(() => {
    api.gaps().then((r) => setGaps(r.gaps)).catch(() => {});
  }, []);

  function selectGap(g: Gap) {
    setSelectedGap(g);
    setMode(g.suggested_mode);
    if (g.suggested_queries.length > 0) {
      setQuery(g.suggested_queries[0]);
    }
  }

  async function runSearch(overrideQuery?: string) {
    const q = (overrideQuery ?? query).trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const r = await api.preview({ query: q, mode, limit });
      setResults(r.results);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink flex items-center gap-2">
            <Telescope className="h-5 w-5 text-accent" />
            Research
          </h1>
          <p className="text-sm text-ink-muted mt-0.5">
            Discover papers and patents across all four tiers. Extraction is
            gated — nothing enters the KB without your explicit confirmation.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4 items-start">
        {/* Left: gap board */}
        <GapBoard
          gaps={gaps}
          selectedId={selectedGap?.id ?? null}
          onSelect={selectGap}
        />

        {/* Right: search + results */}
        <div className="space-y-3">
          {/* Search bar */}
          <div className="rounded-xl border border-ink-line bg-bg-elevated shadow-soft p-3 space-y-2.5">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ink-subtle" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") runSearch();
                  }}
                  placeholder="Search papers / patents (e.g. 'PSF deconvolution display')"
                  className="w-full pl-8 pr-3 py-2 text-sm rounded-lg border border-ink-line bg-bg-subtle/40 placeholder:text-ink-subtle focus:outline-none focus:border-accent-ring focus:bg-bg-elevated transition-colors"
                />
              </div>
              <Button
                variant="primary"
                onClick={() => runSearch()}
                disabled={loading || !query.trim()}
              >
                {loading ? "Searching…" : "Preview"}
              </Button>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              <ModePicker value={mode} onChange={setMode} />
              <div className="flex items-center gap-2 text-xs text-ink-muted">
                <label>Limit per source:</label>
                <select
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="text-xs rounded-md border border-ink-line bg-bg-elevated px-1.5 py-0.5 focus:outline-none focus:border-accent-ring"
                >
                  {[5, 8, 12, 20].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
              {selectedGap && selectedGap.suggested_queries.length > 1 && (
                <div className="flex items-center gap-1 flex-wrap">
                  <span className="text-[10px] uppercase tracking-wider text-ink-subtle">
                    Suggested:
                  </span>
                  {selectedGap.suggested_queries.map((q) => (
                    <button
                      key={q}
                      onClick={() => {
                        setQuery(q);
                        runSearch(q);
                      }}
                      className="text-[11px] rounded-full border border-ink-line bg-bg-subtle/40 px-2 py-0.5 text-ink-muted hover:text-ink hover:border-accent-ring/50 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3">
              {error}
            </div>
          )}

          {results.length > 0 && (
            <div className="text-[11px] text-ink-subtle">
              {results.length} unique results · click <span className="text-ink">Extract</span> on an ArXiv paper to insert it into the KB
            </div>
          )}

          <SearchResults
            results={results}
            loading={loading}
            onExtract={(r) => setExtractCandidate(r)}
          />

          {!loading && results.length === 0 && !error && (
            <div className="rounded-xl border border-dashed border-ink-line bg-bg-elevated/40 p-8 text-center text-sm text-ink-subtle">
              <Sparkles className="h-5 w-5 text-accent mx-auto mb-2" />
              Pick a gap on the left or type a query above.
            </div>
          )}
        </div>
      </div>

      <ExtractFlow
        candidate={extractCandidate}
        onClose={() => setExtractCandidate(null)}
      />
    </div>
  );
}

function ModePicker({ value, onChange }: { value: Mode; onChange: (m: Mode) => void }) {
  const opts: { value: Mode; label: string; hint: string }[] = [
    { value: "academic", label: "Academic", hint: "Tier 1 — fast" },
    { value: "patents", label: "Patents", hint: "Tier 2" },
    { value: "all", label: "All tiers", hint: "Slowest" },
  ];
  return (
    <div className="inline-flex rounded-lg border border-ink-line bg-bg-elevated p-0.5">
      {opts.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "text-xs px-2.5 py-1 rounded-md transition-colors",
            value === o.value
              ? "bg-ink text-bg-elevated"
              : "text-ink-muted hover:text-ink"
          )}
          title={o.hint}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
