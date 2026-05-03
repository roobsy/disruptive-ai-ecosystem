"use client";

import { Search, X } from "lucide-react";
import { cn, titleCase } from "@/lib/utils";

export type Filters = {
  search: string;
  domain: string;
  epistemic_label: string;
  lifecycle_state: string;
  min_confidence: number;
  limit: number;
};

export const DEFAULT_FILTERS: Filters = {
  search: "",
  domain: "",
  epistemic_label: "",
  lifecycle_state: "",
  min_confidence: 0,
  limit: 100,
};

const LABELS = ["axiomatic_fact", "experimental_result", "cognitive_framework"];
const STATES = [
  "discovery",
  "under_evaluation",
  "validated",
  "contested",
  "superseded",
  "ruled_out",
];

export function NodeFilters({
  filters,
  onChange,
  domains,
  total,
  matching,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  domains: string[];
  total: number;
  matching: number;
}) {
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) =>
    onChange({ ...filters, [k]: v });

  const hasFilters =
    filters.search ||
    filters.domain ||
    filters.epistemic_label ||
    filters.lifecycle_state ||
    filters.min_confidence > 0;

  return (
    <div className="rounded-xl border border-ink-line bg-bg-elevated shadow-soft">
      <div className="px-4 pt-3 pb-3 flex items-center gap-3 border-b border-ink-line">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ink-subtle" />
          <input
            value={filters.search}
            onChange={(e) => set("search", e.target.value)}
            placeholder="Search summary, content, tags…"
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-ink-line bg-bg-subtle/40 placeholder:text-ink-subtle focus:outline-none focus:border-accent-ring focus:bg-bg-elevated transition-colors"
          />
        </div>
        <div className="text-xs text-ink-muted tabular-nums">
          <span className="text-ink font-medium">{matching.toLocaleString()}</span>
          <span className="text-ink-subtle"> / {total.toLocaleString()} nodes</span>
        </div>
        {hasFilters && (
          <button
            onClick={() => onChange(DEFAULT_FILTERS)}
            className="text-[11px] text-ink-subtle hover:text-ink inline-flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}
      </div>

      <div className="px-4 py-3 grid grid-cols-2 md:grid-cols-5 gap-2.5">
        <Select
          label="Epistemic label"
          value={filters.epistemic_label}
          onChange={(v) => set("epistemic_label", v)}
          options={LABELS}
        />
        <Select
          label="Lifecycle"
          value={filters.lifecycle_state}
          onChange={(v) => set("lifecycle_state", v)}
          options={STATES}
        />
        <Select
          label="Domain"
          value={filters.domain}
          onChange={(v) => set("domain", v)}
          options={domains}
        />
        <div>
          <label className="text-[10px] uppercase tracking-wider text-ink-subtle">
            Min confidence: {filters.min_confidence}
          </label>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={filters.min_confidence}
            onChange={(e) => set("min_confidence", Number(e.target.value))}
            className="w-full accent-accent mt-1"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-ink-subtle">
            Page size
          </label>
          <select
            value={filters.limit}
            onChange={(e) => set("limit", Number(e.target.value))}
            className="mt-1 w-full text-sm rounded-lg border border-ink-line bg-bg-elevated px-2 py-1 focus:outline-none focus:border-accent-ring"
          >
            {[50, 100, 200, 500].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="text-[10px] uppercase tracking-wider text-ink-subtle">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "mt-1 w-full text-sm rounded-lg border bg-bg-elevated px-2 py-1 focus:outline-none focus:border-accent-ring",
          value ? "border-accent-ring/60" : "border-ink-line"
        )}
      >
        <option value="">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {titleCase(opt)}
          </option>
        ))}
      </select>
    </div>
  );
}
