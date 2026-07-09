"use client";

import { CircleCheck, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { SkeletonOverlay } from "@/components/video/skeleton-overlay";
import { getComparison, getOverlay, listReferences } from "@/lib/api";
import { cn, unitIsTight } from "@/lib/utils";
import type {
  Comparison,
  ComparisonMetric,
  Overlay,
  ReferenceSummary,
} from "@/lib/types";

/**
 * Symbol units ride along with the number ("31.4°"); word units would blow the
 * column apart, so they move into the row label instead.
 */
function value(v: number, unit: string) {
  return unitIsTight(unit) ? `${v}${unit}` : `${v}`;
}

/** A signed gap, colored by whether the golfer sits on the good side of it. */
function Difference({ metric }: { metric: ComparisonMetric }) {
  const { difference, unit, lower_is_better } = metric;
  if (difference === 0) return <span className="tabular text-muted">match</span>;

  // The sign says which way to move. Which way is *virtuous* depends on the
  // metric — less head movement is better, more lead-arm extension is better.
  const better = lower_is_better ? difference < 0 : difference > 0;
  return (
    <span className={cn("tabular font-medium", better ? "text-good-text" : "text-watch")}>
      {difference > 0 ? "+" : ""}
      {value(difference, unit)}
    </span>
  );
}

function Row({ metric }: { metric: ComparisonMetric }) {
  const wordUnit = !unitIsTight(metric.unit) && metric.unit ? metric.unit : null;
  return (
    <div className="grid grid-cols-[1fr_5rem_5rem_5rem] items-center gap-3 border-t border-border py-2 text-sm first:border-t-0">
      <span className="flex flex-wrap items-center gap-1.5">
        {metric.label}
        {wordUnit && <span className="text-xs text-muted">({wordUnit})</span>}
        {metric.view_independent && (
          <span
            className="rounded bg-surface-2 px-1 py-0.5 text-[10px] text-muted"
            title="Timing, not geometry — comparable from any camera angle."
          >
            any view
          </span>
        )}
      </span>
      <span className="tabular text-right">{value(metric.user_value, metric.unit)}</span>
      <span className="tabular text-right text-secondary">
        {value(metric.reference_value, metric.unit)}
      </span>
      <span className="text-right">
        <Difference metric={metric} />
      </span>
    </div>
  );
}

/** Four metrics skipped for the same reason should say the reason once. */
function groupByReason(skipped: { key: string; label: string; reason: string }[]) {
  const groups = new Map<string, string[]>();
  for (const s of skipped) {
    groups.set(s.reason, [...(groups.get(s.reason) ?? []), s.label]);
  }
  return [...groups.entries()];
}

type Tab = "numbers" | "overlay";

export function ComparePanel({ swingId }: { swingId: string }) {
  const [references, setReferences] = useState<ReferenceSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [overlay, setOverlay] = useState<Overlay | null>(null);
  const [overlayFailed, setOverlayFailed] = useState(false);
  const [tab, setTab] = useState<Tab>("numbers");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listReferences()
      .then((refs) => {
        if (cancelled) return;
        setReferences(refs);
        setSelected((current) => current ?? refs[0]?.id ?? null);
      })
      .catch(() => !cancelled && setError("Couldn't load reference swings."));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setComparison(null);
    setOverlay(null);
    setOverlayFailed(false);

    getComparison(swingId, selected)
      .then((c) => !cancelled && setComparison(c))
      .catch(() => !cancelled && setError("Couldn't compare against that reference."));

    // The overlay is a separate, heavier payload. Failing to build it (a swing
    // with no phase anchors, say) must not take the numbers down with it.
    getOverlay(swingId, selected)
      .then((o) => !cancelled && setOverlay(o))
      .catch(() => !cancelled && setOverlayFailed(true));

    return () => {
      cancelled = true;
    };
  }, [swingId, selected]);

  if (error) return null; // comparison is an enhancement; never break the page
  if (references.length === 0) return null;

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
        <CardTitle>Compare against a reference</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          {references.length > 1 && selected && (
            <SegmentedToggle
              label="Reference swing"
              variant="tab"
              size="sm"
              value={selected}
              onChange={setSelected}
              options={references.map((r) => ({ value: r.id, label: r.display_name }))}
            />
          )}
          {overlay && (
            <SegmentedToggle
              label="Comparison view"
              variant="tab"
              value={tab}
              onChange={setTab}
              options={[
                { value: "numbers", label: "Numbers" },
                { value: "overlay", label: "Overlay" },
              ]}
            />
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {tab === "overlay" && overlay && (
          <SkeletonOverlay swingId={swingId} overlay={overlay} />
        )}

        {tab === "numbers" && !comparison && (
          <p className="text-sm text-muted">Comparing…</p>
        )}
        {tab === "numbers" && overlayFailed && (
          <p className="text-xs text-muted">
            The skeleton overlay isn&apos;t available for this pair of swings.
          </p>
        )}

        {tab === "numbers" && comparison && !comparison.camera.compatible && (
          <p className="flex items-start gap-2 rounded-lg bg-surface-2 p-3 text-sm text-secondary">
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-watch" aria-hidden />
            <span>{comparison.camera.reason}</span>
          </p>
        )}

        {tab === "numbers" && comparison && comparison.metrics.length > 0 && (
          <div>
            <div className="grid grid-cols-[1fr_5rem_5rem_5rem] gap-3 pb-1 text-xs font-medium text-muted">
              <span>Metric</span>
              <span className="text-right">You</span>
              <span className="text-right">Reference</span>
              <span className="text-right">Gap</span>
            </div>
            {comparison.metrics.map((m) => (
              <Row key={m.key} metric={m} />
            ))}
          </div>
        )}

        {tab === "numbers" && comparison && comparison.metrics.length === 0 && comparison.camera.compatible && (
          <p className="text-sm text-muted">
            Nothing in these two swings can be compared.
          </p>
        )}

        {tab === "numbers" && comparison && (
          <div className="flex flex-col gap-1 text-xs text-muted">
            {comparison.rotation_note && (
              <p className="flex items-start gap-1.5">
                <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                {comparison.rotation_note}
              </p>
            )}
            {comparison.skipped.length > 0 && (
              <details>
                <summary className="cursor-pointer text-secondary hover:text-foreground">
                  {comparison.skipped.length} metric
                  {comparison.skipped.length === 1 ? "" : "s"} not compared
                </summary>
                <ul className="mt-1 flex flex-col gap-1.5 pl-1">
                  {groupByReason(comparison.skipped).map(([reason, labels]) => (
                    <li key={reason}>
                      <span className="text-secondary">{labels.join(", ")}</span> — {reason}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <p className="mt-1">
              Reference: {comparison.reference.display_name} ·{" "}
              {comparison.reference.source}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
