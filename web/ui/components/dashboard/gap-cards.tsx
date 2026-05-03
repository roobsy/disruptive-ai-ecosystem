import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const GAPS = [
  {
    id: "GAP1",
    title: "Patent landscape",
    severity: "Showstopper",
    status: "Partially filled",
    note: "Need actual patent data once PatentsView/ODP key arrives.",
  },
  {
    id: "GAP2",
    title: "Ophthalmology",
    severity: "Showstopper",
    status: "Filled (150 nodes)",
    note: "Coverage achieved.",
    done: true,
  },
  {
    id: "GAP3",
    title: "Psychophysics / Perception",
    severity: "Showstopper",
    status: "Partially filled",
    note: "50+ nodes added; deeper coverage needed.",
  },
  {
    id: "GAP4",
    title: "Quantitative limits of pre-distortion",
    severity: "Critical",
    status: "Not researched",
    note: "Open question.",
  },
  {
    id: "GAP5",
    title: "Real-time processing architecture",
    severity: "Critical",
    status: "Not researched",
    note: "Open question.",
  },
  {
    id: "GAP6",
    title: "Regulatory classification",
    severity: "Strategic",
    status: "Not researched",
    note: "Open question.",
  },
];

export function GapCards() {
  return (
    <Card>
      <CardHeader
        title="Research Gaps"
        subtitle="From the latest Master Brain strategic review"
      />
      <CardBody>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {GAPS.map((g) => (
            <div
              key={g.id}
              className="rounded-lg border border-ink-line p-3 hover:border-accent-ring/50 hover:shadow-soft transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono text-ink-subtle">{g.id}</div>
                <Badge
                  tone={
                    g.severity === "Showstopper"
                      ? "framework"
                      : g.severity === "Critical"
                        ? "experimental"
                        : "neutral"
                  }
                >
                  {g.severity}
                </Badge>
              </div>
              <div className="mt-1.5 text-sm font-medium text-ink">
                {g.title}
              </div>
              <div className="mt-1 text-[11px] text-ink-muted">
                <span className={g.done ? "text-emerald-600" : ""}>
                  {g.status}
                </span>
                {" — "}
                {g.note}
              </div>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}
