"use client";

import { useState } from "react";

import { KinematicSequencePanel } from "@/components/analysis/kinematic-sequence";
import { AngleChart } from "@/components/charts/angle-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import type { PhaseSegment, SwingMetrics } from "@/lib/types";

type View = "angles" | "sequence";

/**
 * Secondary detail. These were two always-open cards stacked down the page;
 * they answer different questions about the same swing, so they share one
 * surface and the reader picks.
 */
export function SwingDetail({
  metrics,
  phases,
}: {
  metrics: SwingMetrics;
  phases: PhaseSegment[] | null;
}) {
  const [view, setView] = useState<View>("angles");

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Swing detail</CardTitle>
        <SegmentedToggle
          label="Swing detail view"
          variant="tab"
          value={view}
          onChange={setView}
          options={[
            { value: "angles", label: "Angles" },
            { value: "sequence", label: "Kinematic sequence" },
          ]}
        />
      </CardHeader>
      <CardContent>
        {view === "angles"
          ? phases && <AngleChart metrics={metrics} phases={phases} />
          : (
            <KinematicSequencePanel
              sequence={metrics.kinematic_sequence}
              fps={metrics.fps}
            />
          )}
      </CardContent>
    </Card>
  );
}
