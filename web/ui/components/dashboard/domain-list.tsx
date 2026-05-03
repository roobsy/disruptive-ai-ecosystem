import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { titleCase } from "@/lib/utils";

const VENTURE_RELEVANT = new Set([
  "ophthalmology",
  "computer_science",
  "display_technology",
  "video_quality_assessment",
  "optics",
  "neuroscience",
  "psychophysics",
  "perception",
]);

export function DomainList({ byDomain }: { byDomain: Record<string, number> }) {
  const entries = Object.entries(byDomain).sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] || 1;

  return (
    <Card>
      <CardHeader
        title="Domain Coverage"
        subtitle="Node counts by knowledge domain"
      />
      <CardBody>
        <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
          {entries.map(([domain, count]) => {
            const pct = (count / max) * 100;
            const onMission = VENTURE_RELEVANT.has(domain);
            return (
              <div key={domain}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span
                    className={onMission ? "text-ink" : "text-ink-subtle"}
                  >
                    {titleCase(domain)}
                    {!onMission && (
                      <span className="ml-1.5 text-[10px] uppercase text-ink-subtle">
                        off-mission
                      </span>
                    )}
                  </span>
                  <span className="text-ink-muted tabular-nums">{count}</span>
                </div>
                <div className="h-1.5 rounded-full bg-bg-subtle overflow-hidden">
                  <div
                    className={
                      onMission ? "h-full bg-accent" : "h-full bg-ink-subtle/50"
                    }
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
          {entries.length === 0 && (
            <div className="text-xs text-ink-subtle">No domains yet.</div>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
