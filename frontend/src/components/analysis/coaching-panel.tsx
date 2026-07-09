import { CircleCheck, Dumbbell, HeartPulse, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatRange, unitIsTight } from "@/lib/utils";
import type { CoachingMetricContext, CoachingReport } from "@/lib/types";

/**
 * The evidence behind an improvement: the golfer's own number, the range it
 * should sit in, and how far outside it landed. None of this was written by the
 * model — the backend attached it from the metric it computed.
 */
function MetricChip({ context }: { context: CoachingMetricContext }) {
  const { label, value, unit, ideal_range, delta, assessment } = context;
  if (value == null) return null;

  const tight = unitIsTight(unit);
  const sign = delta != null && delta > 0 ? "+" : "";
  const tone = assessment === "good" ? "text-good-text" : "text-watch";

  return (
    <p className="tabular flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
      <span className="font-medium text-secondary">{label}</span>
      <span className="text-foreground">
        {value}
        {tight ? unit : ` ${unit}`}
      </span>
      {ideal_range && <span>ideal {formatRange(ideal_range, unit)}</span>}
      {delta != null && delta !== 0 && (
        <span className={cn("font-medium", tone)}>
          Δ {sign}
          {delta}
          {tight ? unit : ` ${unit}`}
        </span>
      )}
    </p>
  );
}

export function CoachingPanel({ coaching }: { coaching: CoachingReport | null }) {
  if (!coaching) {
    return (
      <Card>
        <CardContent padding="standalone" className="text-sm text-secondary">
          <p className="font-medium text-foreground">AI coaching not configured</p>
          <p className="mt-1">
            Set <code className="rounded bg-surface-2 px-1 py-0.5">ANTHROPIC_API_KEY</code>{" "}
            on the backend to get personalized coaching feedback generated from
            these metrics.
          </p>
        </CardContent>
      </Card>
    );
  }

  // One surface, not four nested ones. The single most important improvement is
  // already surfaced in the hero, so this is the expanded read.
  return (
    <div className="flex flex-col gap-3">
      <Card>
        <CardHeader className="flex-row items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" aria-hidden />
          <CardTitle>Coach&apos;s read</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <p className="text-sm leading-relaxed">{coaching.overall_assessment}</p>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="flex flex-col gap-3">
              <h3 className="text-sm font-semibold">What you&apos;re doing well</h3>
              {coaching.strengths.map((strength) => (
                <div key={strength.title} className="flex gap-2.5">
                  <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-good-text" aria-hidden />
                  <div>
                    <p className="text-sm font-medium">{strength.title}</p>
                    <p className="text-sm text-secondary">{strength.detail}</p>
                  </div>
                </div>
              ))}
            </section>

            <section className="flex flex-col gap-5">
              <h3 className="text-sm font-semibold">Where to focus</h3>
              {coaching.improvements.map((item) => (
                <div key={item.issue} className="flex flex-col gap-1.5">
                  <p className="text-sm font-medium">{item.issue}</p>
                  {item.metric_context && <MetricChip context={item.metric_context} />}
                  <p className="text-sm text-secondary">{item.why_it_matters}</p>

                  {(item.drills ?? []).map((drill) => (
                    <div
                      key={drill.id}
                      className="mt-1 flex gap-2 rounded-lg bg-surface-2 p-2.5 text-sm"
                    >
                      <Dumbbell className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                      <div>
                        <p className="font-medium">{drill.name}</p>
                        <p className="text-secondary">{drill.fixes}</p>
                        <p className="mt-1">{drill.how_to}</p>
                      </div>
                    </div>
                  ))}

                  {/* Analyses stored before the drill library carry free text. */}
                  {!item.drills?.length && item.drill && (
                    <p className="mt-1 flex gap-2 rounded-lg bg-surface-2 p-2.5 text-sm">
                      <Dumbbell className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                      <span>
                        <span className="font-medium">Drill: </span>
                        {item.drill}
                      </span>
                    </p>
                  )}
                </div>
              ))}
            </section>
          </div>

          {coaching.injury_risk_notes.length > 0 && (
            <section className="flex flex-col gap-2 border-t border-border pt-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold">
                <HeartPulse className="h-4 w-4 text-danger" aria-hidden />
                Body-friendly notes
              </h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-secondary">
                {coaching.injury_risk_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </section>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted">
        {coaching.limitations_note} — generated by {coaching.model}.
      </p>
    </div>
  );
}
