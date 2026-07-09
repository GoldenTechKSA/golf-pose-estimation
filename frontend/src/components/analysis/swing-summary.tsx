import { Dumbbell, TriangleAlert } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatRange } from "@/lib/utils";
import type { CoachingReport, SwingMetrics } from "@/lib/types";

/**
 * The primary read: what a golfer should take away in one glance, before any
 * chart. Everything here is derived from data that already exists — the
 * per-metric `assessment` the backend computes, and the improvement the
 * coaching model already ranked first. Nothing is invented or scored.
 */
export function SwingSummary({
  metrics,
  coaching,
}: {
  metrics: SwingMetrics;
  coaching: CoachingReport | null;
}) {
  const scored = metrics.summary.filter((m) => m.assessment !== null);
  const watch = scored.filter((m) => m.assessment === "watch");
  const tempo = metrics.summary.find((m) => m.key === "tempo_ratio");
  const topFault = coaching?.improvements[0] ?? null;

  const headline =
    scored.length === 0
      ? "Swing analyzed"
      : watch.length === 0
        ? "Solid fundamentals across the board"
        : watch.length === 1
          ? "Solid fundamentals, one thing to work on"
          : `${watch.length} areas to sharpen`;

  return (
    <Card>
      <CardContent
        padding="standalone"
        className="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-center"
      >
        <div className="flex flex-col gap-2">
          <h2 className="font-display text-xl font-semibold tracking-tight">{headline}</h2>

          {topFault ? (
            <p className="flex items-start gap-2 text-sm text-secondary">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-watch" aria-hidden />
              <span>
                <span className="font-medium text-foreground">Start here: </span>
                {topFault.issue}
              </span>
            </p>
          ) : (
            watch.length === 0 &&
            scored.length > 0 && (
              <p className="text-sm text-secondary">
                Every measured metric landed inside its typical range.
              </p>
            )
          )}

          {topFault && (
            <p className="flex items-start gap-2 text-sm text-secondary">
              <Dumbbell className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
              <span>{topFault.drill}</span>
            </p>
          )}
        </div>

        {tempo?.value != null && (
          <div className="flex flex-col sm:items-end">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">Tempo</p>
            <p className="tabular font-display text-4xl font-semibold tracking-tight">
              {tempo.value}
              <span className="text-lg font-normal text-muted">{tempo.unit}</span>
            </p>
            {tempo.ideal_range && (
              <p className="tabular text-xs text-muted">
                typical {formatRange(tempo.ideal_range, tempo.unit)}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
