/**
 * Types mirroring the FastAPI response models in backend/app/models/schemas.py.
 * Keep the two in sync when the API contract changes.
 */

export type SwingStatus = "queued" | "processing" | "completed" | "failed";

export type PhaseName =
  | "address"
  | "backswing"
  | "top"
  | "downswing"
  | "impact"
  | "follow_through"
  | "finish";

export interface PhaseSegment {
  name: PhaseName;
  start_frame: number;
  end_frame: number;
  start_time: number;
  end_time: number;
}

export interface ProgressMessage {
  swing_id: string;
  status: SwingStatus;
  stage: string;
  progress: number;
  message: string;
}

export interface VideoUrls {
  original: string;
  annotated: string | null;
  thumbnail: string | null;
}

export interface SwingSummary {
  id: string;
  created_at: string;
  original_filename: string;
  handedness: "right" | "left";
  status: SwingStatus;
  stage: string;
  progress: number;
  error: string | null;
  duration: number | null;
  fps: number | null;
  pose_model: string | null;
}

export interface MetricEntry {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  ideal_range: [number, number] | null;
  lower_is_better: boolean;
  assessment: "good" | "watch" | null;
  description: string;
}

export interface KinematicSequence {
  available: boolean;
  reason?: string;
  order?: string[];
  peak_frames?: Record<string, number>;
  proximal_to_distal?: boolean;
}

export interface SwingMetrics {
  summary: MetricEntry[];
  series: Record<string, (number | null)[]>;
  kinematic_sequence: KinematicSequence;
  events: Record<string, number>;
  fps: number;
  handedness: string;
  notes: string[];
  warnings?: string[];
}

export interface CoachingImprovement {
  issue: string;
  why_it_matters: string;
  drill: string;
}

export interface CoachingStrength {
  title: string;
  detail: string;
}

export interface CoachingReport {
  model: string;
  overall_assessment: string;
  strengths: CoachingStrength[];
  improvements: CoachingImprovement[];
  injury_risk_notes: string[];
  limitations_note: string;
}

export interface SwingDetail extends SwingSummary {
  width: number | null;
  height: number | null;
  n_frames: number | null;
  video_urls: VideoUrls | null;
  phases: PhaseSegment[] | null;
  metrics: SwingMetrics | null;
  coaching: CoachingReport | null;
}
