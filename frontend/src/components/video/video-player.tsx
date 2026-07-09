"use client";

import { StepBack, StepForward } from "lucide-react";
import { useRef, useState } from "react";

import { PhaseTimeline } from "@/components/video/phase-timeline";
import { apiUrl } from "@/lib/api";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
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
        <SegmentedToggle
          label="Video view"
          variant="tab"
          value={view}
          onChange={setView}
          itemClassName="capitalize"
          options={[
            { value: "annotated", label: "annotated", disabled: !urls.annotated },
            { value: "original", label: "original" },
          ]}
        />
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
          <SegmentedToggle
            label="Playback speed"
            variant="pressed"
            size="sm"
            className="ml-1"
            value={speed}
            onChange={setPlaybackSpeed}
            options={SPEEDS.map((value) => ({ value, label: `${value}×` }))}
          />
        </div>
      </div>

      <video
        ref={videoRef}
        key={src}
        src={apiUrl(src)}
        controls
        playsInline
        preload="metadata"
        className="mx-auto max-h-[60vh] w-auto max-w-full rounded-xl border border-border bg-black"
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
