"use client";

import { useEffect, useRef, useState } from "react";

import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { apiUrl } from "@/lib/api";
import type { Overlay } from "@/lib/types";

const CONFIDENCE_FLOOR = 0.3;
const REFERENCE_COLOR = "rgba(42, 120, 214, 0.9)"; // --accent
const JOINT_COLOR = "rgba(42, 120, 214, 0.55)";

type Anchor = "address" | "body";

/**
 * Draws a reference golfer's skeleton over the user's video, warped in time so
 * both swings hit top and impact together, and scaled so the two bodies are the
 * same size.
 *
 * Two anchoring modes, and the difference is the whole point:
 *
 *  - `address` fixes the alignment once, at the end of the setup. Each golfer
 *    then keeps their own movement through the swing, so sway and early
 *    extension show up as the skeletons drifting apart. This is what a coach
 *    wants to see.
 *  - `body` re-anchors on the hips every frame, cancelling translation to
 *    isolate limb shape alone.
 */
export function SkeletonOverlay({
  swingId,
  overlay,
}: {
  swingId: string;
  overlay: Overlay;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [anchor, setAnchor] = useState<Anchor>("address");
  const [visible, setVisible] = useState(true);

  // Redraw on every animation frame while mounted: `timeupdate` fires far too
  // coarsely (~4Hz) to track a 30fps swing, and seeking must repaint too.
  useEffect(() => {
    let raf = 0;
    const draw = () => {
      raf = requestAnimationFrame(draw);
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || !video.videoWidth) return;

      const rect = video.getBoundingClientRect();
      if (canvas.width !== rect.width || canvas.height !== rect.height) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!visible) return;

      const { user, reference, frame_map, scale, anchor_frame } = overlay;
      const frame = Math.min(
        user.n_frames - 1,
        Math.max(0, Math.round(video.currentTime * user.fps)),
      );
      const refFrame = frame_map[frame];
      if (refFrame == null) return;

      // Which frame's hips we align on decides whether translation survives.
      const userAnchor = anchor === "address" ? anchor_frame : frame;
      const refAnchor = anchor === "address" ? frame_map[anchor_frame] : refFrame;
      const [ucx, ucy] = user.hip_centers[userAnchor] ?? [0, 0];
      const [rcx, rcy] = reference.hip_centers[refAnchor] ?? [0, 0];

      // Source pixels -> displayed pixels.
      const sx = canvas.width / user.width;
      const sy = canvas.height / user.height;

      const project = (px: number, py: number): [number, number] => [
        (ucx + scale * (px - rcx)) * sx,
        (ucy + scale * (py - rcy)) * sy,
      ];

      const joints = reference.keypoints[refFrame];
      if (!joints) return;

      ctx.lineWidth = 3;
      ctx.strokeStyle = REFERENCE_COLOR;
      ctx.lineCap = "round";
      for (const [a, b] of overlay.edges) {
        const ja = joints[a];
        const jb = joints[b];
        if (!ja || !jb || ja[2] < CONFIDENCE_FLOOR || jb[2] < CONFIDENCE_FLOOR) continue;
        const [x1, y1] = project(ja[0], ja[1]);
        const [x2, y2] = project(jb[0], jb[1]);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      ctx.fillStyle = JOINT_COLOR;
      for (const joint of joints) {
        if (joint[2] < CONFIDENCE_FLOOR) continue;
        const [x, y] = project(joint[0], joint[1]);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [overlay, anchor, visible]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <SegmentedToggle
          label="Overlay"
          variant="pressed"
          size="sm"
          value={visible ? "on" : "off"}
          onChange={(v) => setVisible(v === "on")}
          options={[
            { value: "on", label: "Overlay on" },
            { value: "off", label: "Off" },
          ]}
        />
        <SegmentedToggle
          label="Alignment"
          variant="tab"
          size="sm"
          value={anchor}
          onChange={setAnchor}
          options={[
            { value: "address", label: "Anchored at address" },
            { value: "body", label: "Body-locked" },
          ]}
        />
      </div>

      {/* w-fit so the frame hugs the video rather than the card. */}
      <div className="relative mx-auto w-fit overflow-hidden rounded-xl border border-border">
        <video
          ref={videoRef}
          src={apiUrl(`/api/v1/swings/${swingId}/video/source`)}
          className="block max-h-[70vh] w-auto"
          controls
          playsInline
          preload="metadata"
        />
        <canvas
          ref={canvasRef}
          aria-hidden
          className="pointer-events-none absolute left-0 top-0"
        />
      </div>

      <p className="text-xs text-muted">
        {overlay.reference_name}, warped so both swings reach the top and impact
        together, and scaled to your body.{" "}
        {overlay.mirrored && "Mirrored to match your handedness. "}
        {anchor === "address"
          ? "Aligned once at address, so drift between the skeletons is real movement."
          : "Re-aligned on the hips every frame, which hides sway and shows limb shape only."}
      </p>
    </div>
  );
}
