"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PHASE_LABELS, phaseColor } from "@/lib/phases";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import type { PhaseSegment, SwingMetrics } from "@/lib/types";

/**
 * Angle-over-time chart with the detected phases as tinted background
 * regions. Follows the dataviz mark spec: 2px lines, no per-point dots
 * (>=8px active marker on hover), hairline grid, recessive axes, legend +
 * crosshair tooltip; series identity is carried by the legend text and the
 * tooltip labels, not color alone.
 */

interface SeriesDef {
  key: string;
  label: string;
  color: string; // CSS var — validated categorical slots, light/dark aware
}

const CHART_MODES: Record<string, { title: string; series: SeriesDef[] }> = {
  rotation: {
    title: "Rotation",
    series: [
      { key: "shoulder_angle", label: "Shoulder line", color: "var(--series-1)" },
      { key: "hip_angle", label: "Hip line", color: "var(--series-2)" },
      { key: "x_factor", label: "X-Factor", color: "var(--series-3)" },
    ],
  },
  posture: {
    title: "Posture",
    series: [
      { key: "spine_angle", label: "Spine tilt", color: "var(--series-1)" },
    ],
  },
  extension: {
    title: "Arm & knees",
    series: [
      { key: "lead_arm", label: "Lead arm", color: "var(--series-1)" },
      { key: "lead_knee_flex", label: "Lead knee", color: "var(--series-2)" },
      { key: "trail_knee_flex", label: "Trail knee", color: "var(--series-3)" },
    ],
  },
};

interface Point {
  t: number;
  phase: string;
  [key: string]: number | string | null;
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | null; stroke?: string }>;
  label?: number;
}) {
  if (!active || !payload?.length) return null;
  const phase = (payload[0] as { payload?: Point }).payload?.phase;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-md">
      <p className="font-medium">
        {typeof label === "number" ? `${label.toFixed(2)}s` : label}
        {phase && (
          <span className="ml-2 text-muted">
            {PHASE_LABELS[phase as keyof typeof PHASE_LABELS] ?? phase}
          </span>
        )}
      </p>
      <div className="mt-1 flex flex-col gap-0.5">
        {payload.map((entry) => (
          <p key={entry.name} className="flex items-center gap-1.5 text-secondary">
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: entry.stroke }}
              aria-hidden
            />
            {entry.name}:{" "}
            <span className="font-medium text-foreground">
              {entry.value == null ? "—" : `${Number(entry.value).toFixed(1)}°`}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
}

export function AngleChart({
  metrics,
  phases,
}: {
  metrics: SwingMetrics;
  phases: PhaseSegment[];
}) {
  const [mode, setMode] = useState<keyof typeof CHART_MODES>("rotation");
  const { series } = CHART_MODES[mode];
  const fps = metrics.fps || 30;

  const data = useMemo<Point[]>(() => {
    const length = Math.max(
      ...series.map((s) => metrics.series[s.key]?.length ?? 0),
    );
    const labels: string[] = [];
    for (const phase of phases) {
      for (let f = phase.start_frame; f <= phase.end_frame; f++) {
        labels[f] = phase.name;
      }
    }
    return Array.from({ length }, (_, f) => {
      const point: Point = { t: Number((f / fps).toFixed(3)), phase: labels[f] ?? "" };
      for (const s of series) {
        point[s.key] = metrics.series[s.key]?.[f] ?? null;
      }
      return point;
    });
  }, [metrics, phases, series, fps]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <SegmentedToggle
          label="Chart mode"
          variant="tab"
          value={mode}
          onChange={setMode}
          options={Object.entries(CHART_MODES).map(([key, def]) => ({
            value: key as keyof typeof CHART_MODES,
            label: def.title,
          }))}
        />
        <div className="flex flex-wrap gap-x-3 gap-y-1" aria-label="Series legend">
          {series.map((s) => (
            <span key={s.key} className="flex items-center gap-1.5 text-xs text-secondary">
              <span
                className="h-0.5 w-4 rounded"
                style={{ background: s.color }}
                aria-hidden
              />
              {s.label}
            </span>
          ))}
        </div>
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
            <CartesianGrid stroke="var(--border)" strokeWidth={1} vertical={false} />
            {phases.map((phase) => (
              <ReferenceArea
                key={phase.name}
                x1={phase.start_time}
                x2={phase.end_time}
                fill={phaseColor(phase.name)}
                fillOpacity={0.08}
                stroke="none"
              />
            ))}
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(t: number) => `${t.toFixed(1)}s`}
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              axisLine={{ stroke: "var(--border)" }}
              tickLine={false}
            />
            <YAxis
              unit="°"
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={48}
            />
            <Tooltip
              content={<ChartTooltip />}
              cursor={{ stroke: "var(--muted)", strokeDasharray: "3 3" }}
            />
            {series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
                // A null here means the backend judged the angle unmeasurable on
                // that frame. Bridging the gap would draw a line through data we
                // said we don't have.
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
}
