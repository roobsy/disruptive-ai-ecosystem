"use client";

import { useEffect, useState } from "react";
import { api, Health, Venture } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Activity } from "lucide-react";

export function Topbar() {
  const [health, setHealth] = useState<Health | null>(null);
  const [venture, setVenture] = useState<Venture | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api.venture().then(setVenture).catch(() => {});
  }, []);

  return (
    <header className="h-14 shrink-0 border-b border-ink-line bg-bg-elevated/60 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-ink-subtle">
            Active Venture
          </div>
          <div className="text-sm font-medium leading-tight">
            {venture?.name || "—"}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge tone={health?.supabase_configured ? "accent" : "neutral"}>
          <Activity className="h-2.5 w-2.5" />
          KB {health?.supabase_configured ? "Connected" : "Offline"}
        </Badge>
        <Badge tone={health?.anthropic_configured ? "axiomatic" : "neutral"}>
          Claude {health?.anthropic_configured ? "Online" : "Offline"}
        </Badge>
      </div>
    </header>
  );
}
