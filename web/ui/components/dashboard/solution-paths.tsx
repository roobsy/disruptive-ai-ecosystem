import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const PATHS = [
  { id: "A", title: "Software PSF deconvolution", note: "Pure software, limited to ±2–4D" },
  { id: "B", title: "Light field / microlens hybrid", note: "Rabbit Eyes approach" },
  { id: "C", title: "Tunable optics layer on display", note: "Active hardware element" },
  { id: "D", title: "Hybrid computational + optical", note: "Master Brain recommended", recommended: true },
  { id: "E", title: "Personalized subpixel rendering", note: "Per-user calibration" },
];

export function SolutionPaths() {
  return (
    <Card>
      <CardHeader
        title="Solution Paths"
        subtitle="Candidate architectures under consideration"
      />
      <CardBody>
        <div className="space-y-2">
          {PATHS.map((p) => (
            <div
              key={p.id}
              className="flex items-center gap-3 rounded-lg border border-ink-line bg-bg-elevated px-3 py-2.5 hover:border-accent-ring/40 transition-colors"
            >
              <div className="h-8 w-8 rounded-md bg-bg-subtle grid place-items-center font-mono text-sm font-semibold text-ink-muted">
                {p.id}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-ink truncate">
                  {p.title}
                </div>
                <div className="text-[11px] text-ink-subtle truncate">
                  {p.note}
                </div>
              </div>
              {p.recommended && <Badge tone="accent">Recommended</Badge>}
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}
