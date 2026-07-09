"use client";

import { useParams } from "next/navigation";
import { useEffect } from "react";

import { CoachingPanel } from "@/components/analysis/coaching-panel";
import { KeyMetrics } from "@/components/analysis/key-metrics";
import { ProcessingView } from "@/components/analysis/processing-view";
import { SwingDetail } from "@/components/analysis/swing-detail";
import { SwingSummary } from "@/components/analysis/swing-summary";
import { VideoPlayer } from "@/components/video/video-player";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useSwing } from "@/hooks/use-swing";
import { useSwingProgress } from "@/hooks/use-swing-progress";
import { formatDate, formatDuration } from "@/lib/utils";

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? null;
  const { swing, error, loading, refetch } = useSwing(id);

  const inFlight =
    swing != null && (swing.status === "queued" || swing.status === "processing");
  const { progress, done } = useSwingProgress(inFlight ? id : null);

  // When the live progress stream reports a terminal state, pull the full
  // analysis payload (phases, metrics, coaching, video urls).
  useEffect(() => {
    if (done) void refetch();
  }, [done, refetch]);

  if (loading) {
    return (
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 sm:px-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !swing) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center text-secondary">
        {error ?? "Swing not found."}
      </div>
    );
  }

  if (swing.status === "queued" || swing.status === "processing") {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <ProcessingView
          progress={
            progress ?? {
              swing_id: swing.id,
              status: swing.status,
              stage: swing.stage,
              progress: swing.progress,
              message: "",
            }
          }
        />
      </div>
    );
  }

  if (swing.status === "failed") {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <ProcessingView
          progress={{
            swing_id: swing.id,
            status: "failed",
            stage: swing.stage,
            progress: swing.progress,
            message: swing.error ?? "",
          }}
        />
      </div>
    );
  }

  const metrics = swing.metrics;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Swing analysis</h1>
          <p className="mt-0.5 text-sm text-secondary">
            {swing.original_filename} · {formatDate(swing.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge>{swing.handedness}-handed</Badge>
          <Badge>{formatDuration(swing.duration)}</Badge>
        </div>
      </header>

      {/* Primary read, before anything that needs interpreting. */}
      {metrics && <SwingSummary metrics={metrics} coaching={swing.coaching} />}

      {metrics?.warnings?.map((warning) => (
        <p key={warning} className="text-sm text-watch">
          {warning}
        </p>
      ))}

      {/* Video and the key metrics share a row on large screens so both are
          visible without scrolling; they stack on narrow viewports. */}
      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        <VideoPlayer swing={swing} phases={swing.phases} />

        {metrics && <KeyMetrics metrics={metrics} />}
      </div>

      {metrics && <SwingDetail metrics={metrics} phases={swing.phases} />}

      <section aria-labelledby="coaching-heading">
        <h2 id="coaching-heading" className="mb-3 text-lg font-semibold">
          Coaching feedback
        </h2>
        <CoachingPanel coaching={swing.coaching} />
      </section>

      {/* Tertiary: methodology and caveats, for the reader who goes looking. */}
      {metrics && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer text-secondary hover:text-foreground">
            Analysis details
          </summary>
          <p className="mt-2 leading-relaxed">{metrics.notes.join(" ")}</p>
          {swing.pose_model && (
            <p className="mt-1">
              Pose model: {swing.pose_model.replace(".pt", "")}
              {swing.fps ? ` · ${Math.round(swing.fps)} fps` : ""}
            </p>
          )}
        </details>
      )}
    </div>
  );
}
