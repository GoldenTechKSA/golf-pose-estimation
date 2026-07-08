import { CircleCheck, TriangleAlert } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { MetricEntry } from "@/lib/types";

/**
 * Stat tile per the dataviz spec: big proportional figure, muted context,
 * and a status that is icon + label (never color alone).
 */
export function MetricCard({ metric }: { metric: MetricEntry }) {
  const { label, value, unit, ideal_range, assessment, description } = metric;
  return (
    <Card>
      <CardContent className="flex h-full flex-col gap-1.5 p-4">
        <p className="text-xs font-medium text-secondary">{label}</p>
        <p className="text-2xl font-semibold tracking-tight">
          {value == null ? "—" : value}
          {value != null && unit && (
            <span className="ml-1 text-sm font-normal text-muted">{unit}</span>
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
            <span className="text-muted">
              typical {ideal_range[0]}–{ideal_range[1]}
              {unit === ":1" ? "" : unit}
            </span>
          )}
        </div>
        <p className="mt-auto pt-1 text-xs leading-relaxed text-muted">{description}</p>
      </CardContent>
    </Card>
  );
}
