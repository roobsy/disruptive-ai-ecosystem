import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { titleCase } from "@/lib/utils";

const COLORS: Record<string, string> = {
  axiomatic_fact: "bg-epistemic-axiomatic",
  experimental_result: "bg-epistemic-experimental",
  cognitive_framework: "bg-epistemic-framework",
};

export function EpistemicBar({
  byLabel,
  total,
}: {
  byLabel: Record<string, number>;
  total: number;
}) {
  const order = ["axiomatic_fact", "experimental_result", "cognitive_framework"];
  return (
    <Card>
      <CardHeader
        title="Epistemic Composition"
        subtitle="How knowledge is classified across the KB"
      />
      <CardBody>
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-bg-subtle">
          {order.map((label) => {
            const v = byLabel[label] || 0;
            const pct = total ? (v / total) * 100 : 0;
            return (
              <div
                key={label}
                className={`${COLORS[label]} transition-all`}
                style={{ width: `${pct}%` }}
                title={`${titleCase(label)}: ${v}`}
              />
            );
          })}
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3">
          {order.map((label) => {
            const v = byLabel[label] || 0;
            const pct = total ? Math.round((v / total) * 100) : 0;
            return (
              <div key={label}>
                <div className="flex items-center gap-1.5 text-[11px] text-ink-muted">
                  <span
                    className={`h-2 w-2 rounded-full ${COLORS[label]}`}
                  />
                  {titleCase(label)}
                </div>
                <div className="mt-1 text-lg font-semibold">{v}</div>
                <div className="text-[11px] text-ink-subtle">{pct}%</div>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}
