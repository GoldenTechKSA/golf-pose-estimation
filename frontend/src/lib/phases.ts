import type { PhaseName } from "@/lib/types";

export const PHASE_ORDER: PhaseName[] = [
  "address",
  "backswing",
  "top",
  "downswing",
  "impact",
  "follow_through",
  "finish",
];

export const PHASE_LABELS: Record<PhaseName, string> = {
  address: "Address",
  backswing: "Backswing",
  top: "Top",
  downswing: "Downswing",
  impact: "Impact",
  follow_through: "Follow-through",
  finish: "Finish",
};

/**
 * Phase colors reference the CSS custom properties defined in globals.css so
 * light/dark variants swap automatically. Every use of a phase color is
 * accompanied by its text label — identity is never color-alone.
 */
export function phaseColor(name: PhaseName): string {
  return `var(--phase-${name})`;
}

export const STAGE_LABELS: Record<string, string> = {
  queued: "Waiting in queue",
  preparing: "Preparing video",
  extracting_keypoints: "Extracting keypoints",
  analyzing: "Analyzing swing",
  rendering: "Rendering annotated video",
  coaching: "Generating coaching feedback",
  done: "Done",
};

export const STAGE_SEQUENCE = [
  "preparing",
  "extracting_keypoints",
  "analyzing",
  "rendering",
  "coaching",
];
