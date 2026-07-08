"use client";

import { StepBack, StepForward } from "lucide-react";
import { useRef, useState } from "react";

import { PhaseTimeline } from "@/components/video/phase-timeline";
import { apiUrl } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { PhaseSegment, SwingDetail } from "@/lib/types";

const SPEEDS = [0.25, 0.5, 1] as const;

export function VideoPlayer({
  swing,
  phases,
}: {
  swing: SwingDetail;
  phases: PhaseSegment[] | null;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [view, setView] = useState<"annotated" | "original">("annotated");
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [currentTime, setCurrentTime] = useState(0);

  const urls = swing.video_urls;
  if (!urls) return null;
  const src = view === "annotated" && urls.annotated ? urls.annotated : urls.original;
  const frameStep = swing.fps ? 1 / swing.fps : 1 / 30;

  const seek = (time: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = time;
    setCurrentTime(time);
  };

  const stepFrame = (direction: 1 | -1) => {
    const video = videoRef.current;
    if (!video) return;
    video.pause();
    seek(Math.max(0, video.currentTime + direction * frameStep));
  };

  const setPlaybackSpeed = (value: (typeof SPEEDS)[number]) => {
    setSpeed(value);
    if (videoRef.current) videoRef.current.playbackRate = value;
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div role="tablist" aria-label="Video view" className="flex rounded-lg border border-border p-0.5">
          {(["annotated", "original"] as const).map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={view === tab}
              disabled={tab === "annotated" && !urls.annotated}
              onClick={() => setView(tab)}
              className={cn(
                "rounded-md px-3 py-1 text-sm capitalize transition-colors disabled:opacity-40",
                view === tab
                  ? "bg-surface-2 font-medium"
                  : "text-secondary hover:text-foreground",
              )}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Step back one frame"
            onClick={() => stepFrame(-1)}
            className="rounded-md p-1.5 text-secondary hover:bg-surface-2 hover:text-foreground"
          >
            <StepBack className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="Step forward one frame"
            onClick={() => stepFrame(1)}
            className="rounded-md p-1.5 text-secondary hover:bg-surface-2 hover:text-foreground"
          >
            <StepForward className="h-4 w-4" />
          </button>
          <div className="ml-1 flex rounded-lg border border-border p-0.5">
            {SPEEDS.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={speed === value}
                onClick={() => setPlaybackSpeed(value)}
                className={cn(
                  "rounded-md px-2 py-0.5 text-xs transition-colors",
                  speed === value
                    ? "bg-surface-2 font-medium"
                    : "text-secondary hover:text-foreground",
                )}
              >
                {value}×
              </button>
            ))}
          </div>
        </div>
      </div>

      <video
        ref={videoRef}
        key={src}
        src={apiUrl(src)}
        controls
        playsInline
        preload="metadata"
        className="w-full rounded-xl border border-border bg-black"
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => {
          e.currentTarget.playbackRate = speed;
        }}
      />

      {phases && swing.duration != null && (
        <PhaseTimeline
          phases={phases}
          duration={swing.duration}
          currentTime={currentTime}
          onSeek={(time) => {
            seek(time);
            videoRef.current?.play().catch(() => undefined);
          }}
        />
      )}
    </div>
  );
}
