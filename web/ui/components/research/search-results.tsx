"use client";

import { SourceResult } from "@/lib/api";
import { ExternalLink, Download, FileDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SearchResults({
  results,
  loading,
  onExtract,
}: {
  results: SourceResult[];
  loading: boolean;
  onExtract: (r: SourceResult) => void;
}) {
  if (loading) {
    return (
      <div className="rounded-xl border border-ink-line bg-bg-elevated p-8 text-center text-sm text-ink-subtle">
        Searching across sources… this can take 5–20 seconds.
      </div>
    );
  }

  if (!results.length) {
    return null;
  }

  return (
    <div className="space-y-2">
      {results.map((r, i) => {
        const id = r.arxiv_id || r.patent_number || r.doi || `${r.source_api}-${i}`;
        // Pipeline now supports: arxiv (full PDF), direct pdf_url, DOI via
        // Unpaywall, patent via Google Patents, or abstract-only fallback.
        const canExtract =
          !!r.arxiv_id ||
          !!r.pdf_url ||
          !!r.doi ||
          !!r.patent_number ||
          !!r.abstract;
        const extractHint = r.arxiv_id
          ? "ArXiv full PDF"
          : r.pdf_url
            ? "Direct PDF"
            : r.doi
              ? "Open-access PDF via Unpaywall (or abstract fallback)"
              : r.patent_number
                ? "Google Patents PDF (or abstract fallback)"
                : "Abstract-only extraction";
        return (
          <div
            key={id}
            className="rounded-xl border border-ink-line bg-bg-elevated p-3 hover:border-accent-ring/50 transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                  <span className="text-[10px] font-mono text-ink-subtle">
                    {r.source_api}
                  </span>
                  {r.year && (
                    <span className="text-[10px] font-mono text-ink-subtle">
                      · {r.year}
                    </span>
                  )}
                  {r.citation_count > 0 && (
                    <span className="text-[10px] font-mono text-ink-subtle">
                      · {r.citation_count.toLocaleString()} cites
                    </span>
                  )}
                  {r.has_open_access && (
                    <Badge tone="axiomatic">
                      <Download className="h-2.5 w-2.5" />
                      Open access
                    </Badge>
                  )}
                  {r.arxiv_id && (
                    <span className="text-[10px] font-mono text-accent">
                      arXiv:{r.arxiv_id}
                    </span>
                  )}
                  {r.patent_number && (
                    <span className="text-[10px] font-mono text-accent">
                      {r.patent_number}
                    </span>
                  )}
                </div>
                <div className="text-sm font-medium text-ink leading-snug">
                  {r.title || "(no title)"}
                </div>
                {r.authors && r.authors.length > 0 && (
                  <div className="mt-0.5 text-[11px] text-ink-muted line-clamp-1">
                    {r.authors.slice(0, 5).join(", ")}
                    {r.authors.length > 5 && ` +${r.authors.length - 5}`}
                  </div>
                )}
                {r.abstract && (
                  <div className="mt-1 text-[12px] text-ink-muted line-clamp-2 leading-relaxed">
                    {r.abstract}
                  </div>
                )}
                <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                  {r.url && (
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-ink-muted hover:text-accent inline-flex items-center gap-1"
                    >
                      Source <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  )}
                  {r.pdf_url && (
                    <a
                      href={r.pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-accent hover:underline inline-flex items-center gap-1"
                    >
                      PDF <FileDown className="h-2.5 w-2.5" />
                    </a>
                  )}
                </div>
              </div>
              <div className="shrink-0">
                <Button
                  variant={canExtract ? "primary" : "outline"}
                  size="sm"
                  disabled={!canExtract}
                  onClick={() => canExtract && onExtract(r)}
                  title={
                    canExtract
                      ? `Open the extraction confirmation modal — ${extractHint}`
                      : "No extractable content (no ID, URL, or abstract)"
                  }
                >
                  Extract
                </Button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
