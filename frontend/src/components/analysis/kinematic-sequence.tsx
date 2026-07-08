import { ArrowRight, CircleCheck, TriangleAlert } from "lucide-react";

import type { KinematicSequence as Sequence } from "@/lib/types";

const SEGMENT_LABELS: Record<string, string> = {
  hips: "Hips",
  torso: "Torso",
  arms: "Arms",
};

export function KinematicSequencePanel({
  sequence,
  fps,
}: {
  sequence: Sequence;
  fps: number;
}) {
  if (!sequence.available) {
    return (
      <p className="text-sm text-secondary">
        Kinematic sequence unavailable: {sequence.reason ?? "downswing too short"}.
      </p>
    );
  }

  const order = sequence.order ?? [];
  const peaks = sequence.peak_frames ?? {};
  const good = sequence.proximal_to_distal;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {order.map((segment, i) => (
          <span key={segment} className="flex items-center gap-2">
            <span className="rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-sm font-medium">
              {SEGMENT_LABELS[segment] ?? segment}
              <span className="ml-2 text-xs font-normal text-muted">
                {peaks[segment] != null ? `${(peaks[segment] / fps).toFixed(2)}s` : ""}
              </span>
            </span>
            {i < order.length - 1 && (
              <ArrowRight className="h-4 w-4 text-muted" aria-hidden />
            )}
          </span>
        ))}
      </div>
      {good ? (
        <p className="flex items-center gap-1.5 text-sm font-medium text-good-text">
          <CircleCheck className="h-4 w-4" aria-hidden />
          Efficient proximal-to-distal sequence — energy flows from the ground up.
        </p>
      ) : (
        <p className="flex items-center gap-1.5 text-sm font-medium text-watch">
          <TriangleAlert className="h-4 w-4" aria-hidden />
          Out of order — an efficient downswing fires hips, then torso, then arms.
        </p>
      )}
    </div>
  );
}
