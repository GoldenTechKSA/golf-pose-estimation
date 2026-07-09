"use client";

import { Check, CircleDashed, Loader2, XCircle } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { STAGE_LABELS, STAGE_SEQUENCE } from "@/lib/phases";
import type { ProgressMessage } from "@/lib/types";

export function ProcessingView({ progress }: { progress: ProgressMessage | null }) {
  const stage = progress?.stage ?? "queued";
  const pct = progress?.progress ?? 0;
  const failed = progress?.status === "failed";
  const currentIndex = STAGE_SEQUENCE.indexOf(stage);

  if (failed) {
    return (
      <Card className="mx-auto max-w-lg">
        <CardContent padding="standalone" className="flex flex-col items-center gap-4 text-center">
          <XCircle className="h-10 w-10 text-danger" aria-hidden />
          <div>
            <h2 className="text-lg font-semibold">Analysis failed</h2>
            <p className="mt-1 text-sm text-secondary">
              {progress?.message ||
                "Something went wrong while processing this video."}
            </p>
          </div>
          <Link href="/upload">
            <Button variant="secondary">Try another video</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-lg">
      <CardContent padding="standalone" className="flex flex-col gap-6">
        <div className="text-center">
          <h2 className="text-lg font-semibold">Analyzing your swing</h2>
          <p className="mt-1 text-sm text-secondary">
            {progress?.message || "Waiting for the analysis worker…"}
          </p>
        </div>
        <Progress value={pct} />
        <ol className="flex flex-col gap-3">
          {STAGE_SEQUENCE.map((step, i) => {
            const isDone = currentIndex > i || pct >= 100;
            const isActive = currentIndex === i;
            return (
              <li key={step} className="flex items-center gap-3 text-sm">
                {isDone ? (
                  <Check className="h-4 w-4 text-good-text" aria-hidden />
                ) : isActive ? (
                  <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
                ) : (
                  <CircleDashed className="h-4 w-4 text-muted" aria-hidden />
                )}
                <span className={isActive ? "font-medium" : isDone ? "" : "text-muted"}>
                  {STAGE_LABELS[step] ?? step}
                </span>
              </li>
            );
          })}
        </ol>
        <p className="text-center text-xs text-muted">
          Longer or higher-resolution videos take longer — this usually
          finishes within a minute.
        </p>
      </CardContent>
    </Card>
  );
}
