"use client";

import { useEffect, useState } from "react";
import { api, KBStats, Venture } from "@/lib/api";
import { StatTile } from "./stat-tile";
import { EpistemicBar } from "./epistemic-bar";
import { DomainList } from "./domain-list";
import { GapCards } from "./gap-cards";
import { SolutionPaths } from "./solution-paths";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import {
  Database,
  Gauge,
  Layers,
  Target,
  ArrowUpRight,
} from "lucide-react";

export function Dashboard() {
  const [stats, setStats] = useState<KBStats | null>(null);
  const [venture, setVenture] = useState<Venture | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setError(String(e)));
    api.venture().then(setVenture).catch(() => {});
  }, []);

  const total = stats?.total ?? 0;
  const conf = stats?.avg_confidence ?? 0;
  const domains = stats?.by_domain ? Object.keys(stats.by_domain).length : 0;

  return (
    <div className="p-6 space-y-6">
      {/* Hero */}
      <Card glass className="overflow-hidden">
        <div className="bg-grain px-6 py-5">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-accent font-semibold">
                Prime Directive
              </div>
              <h1 className="mt-1 text-xl font-semibold text-ink leading-snug max-w-2xl">
                {venture?.prime_directive ||
                  "Loading the active venture's prime directive…"}
              </h1>
              <div className="mt-2 text-xs text-ink-muted">
                Venture: <span className="text-ink">{venture?.name || "—"}</span>
              </div>
            </div>
            <button className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-ink text-bg-elevated px-3 py-2 text-sm font-medium shadow-soft hover:bg-ink/90">
              Run strategic review
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </Card>

      {error && (
        <Card className="border-amber-200 bg-amber-50/60">
          <CardBody className="text-sm text-amber-800">
            Couldn't reach the API ({error}). Make sure
            <code className="mx-1 px-1.5 py-0.5 rounded bg-white/60 border border-amber-200 text-xs">
              uvicorn web.api.main:app --reload --port 8000
            </code>
            is running.
          </CardBody>
        </Card>
      )}

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatTile
          label="Total nodes"
          value={total.toLocaleString()}
          icon={<Database className="h-4 w-4" />}
        />
        <StatTile
          label="Avg confidence"
          value={conf ? conf.toFixed(1) : "—"}
          trend="0–100 scale"
          icon={<Gauge className="h-4 w-4" />}
          accent
        />
        <StatTile
          label="Domains covered"
          value={domains}
          icon={<Layers className="h-4 w-4" />}
        />
        <StatTile
          label="Solution paths"
          value={5}
          trend="Path D recommended"
          icon={<Target className="h-4 w-4" />}
        />
      </div>

      {/* Mid row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <EpistemicBar
            byLabel={stats?.by_label ?? {}}
            total={total}
          />
        </div>
        <DomainList byDomain={stats?.by_domain ?? {}} />
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <GapCards />
        </div>
        <SolutionPaths />
      </div>

      {/* Hint card */}
      <Card glass>
        <CardHeader
          title="Try the chat"
          subtitle="The chat panel can call backend tools directly."
        />
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {[
              "What's the current state of the KB?",
              "Show me the highest-confidence axiomatic facts.",
              "Which domains are off-mission?",
            ].map((s) => (
              <div
                key={s}
                className="rounded-lg border border-ink-line bg-bg-elevated px-3 py-2.5 text-sm text-ink-muted"
              >
                {s}
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
