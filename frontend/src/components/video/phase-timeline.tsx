"use client";

import { PHASE_LABELS, phaseColor } from "@/lib/phases";
import type { PhaseSegment } from "@/lib/types";

/**
 * Clickable phase scrubber: one proportional segment per detected phase,
 * with a playhead tracking the video. Labels ride with the colors (identity
 * is never color-alone).
 */
export function PhaseTimeline({
  phases,
  duration,
  currentTime,
  onSeek,
}: {
  phases: PhaseSegment[];
  duration: number;
  currentTime: number;
  onSeek: (time: number) => void;
}) {
  if (!phases.length || duration <= 0) return null;
  const playheadPct = Math.min(100, (currentTime / duration) * 100);

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <div className="flex h-3 w-full gap-px overflow-hidden rounded-full">
          {phases.map((phase) => (
            <button
              key={phase.name}
              type="button"
              title={`${PHASE_LABELS[phase.name]} (${phase.start_time.toFixed(2)}s – ${phase.end_time.toFixed(2)}s)`}
              aria-label={`Jump to ${PHASE_LABELS[phase.name]}`}
              onClick={() => onSeek(phase.start_time)}
              className="h-full cursor-pointer transition-opacity hover:opacity-80"
              style={{
                width: `${((phase.end_time - phase.start_time) / duration) * 100}%`,
                background: phaseColor(phase.name),
              }}
            />
          ))}
        </div>
        <div
          aria-hidden
          className="pointer-events-none absolute -top-0.5 h-4 w-0.5 rounded bg-foreground"
          style={{ left: `${playheadPct}%` }}
        />
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {phases.map((phase) => (
          <button
            key={phase.name}
            type="button"
            onClick={() => onSeek(phase.start_time)}
            className="flex cursor-pointer items-center gap-1.5 text-xs text-secondary hover:text-foreground"
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: phaseColor(phase.name) }}
              aria-hidden
            />
            {PHASE_LABELS[phase.name]}
          </button>
        ))}
      </div>
    </div>
  );
}
