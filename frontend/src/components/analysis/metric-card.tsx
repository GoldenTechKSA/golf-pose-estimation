import { CircleCheck, TriangleAlert } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn, formatRange, unitIsTight } from "@/lib/utils";
import type { MetricEntry } from "@/lib/types";

/**
 * Stat tile per the dataviz spec: big tabular figure (the tiles grid into
 * columns, so digits must not change width), muted context, and a status that
 * is icon + label (never color alone).
 */
export function MetricCard({ metric }: { metric: MetricEntry }) {
  const { label, value, unit, ideal_range, assessment, description } = metric;
  return (
    // The tile grid is for scanning numbers and status. The explanatory sentence
    // stays reachable on hover rather than competing with the value on every tile.
    <Card title={description}>
      <CardContent padding="compact" className="flex h-full flex-col gap-1.5">
        <p className="text-xs font-medium text-secondary">{label}</p>
        <p className="tabular font-display text-2xl font-semibold tracking-tight">
          {value == null ? "—" : value}
          {value != null && unit && (
            <span
              className={cn(
                "text-sm font-normal text-muted",
                unitIsTight(unit) ? "" : "ml-1",
              )}
            >
              {unit}
            </span>
          )}
        </p>
        <div className="flex items-center gap-2 text-xs">
          {assessment === "good" && (
            <span className="flex items-center gap-1 font-medium text-good-text">
              <CircleCheck className="h-3.5 w-3.5" aria-hidden /> Good
            </span>
          )}
          {assessment === "watch" && (
            <span className="flex items-center gap-1 font-medium text-watch">
              <TriangleAlert className="h-3.5 w-3.5" aria-hidden /> Worth a look
            </span>
          )}
          {ideal_range && (
            <span className="tabular text-muted">
              typical {formatRange(ideal_range, unit)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
