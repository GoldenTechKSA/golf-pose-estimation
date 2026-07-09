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
  /** Signed distance to the nearest violated bound, in the metric's unit. 0 when in range. */
  delta: number | null;
  /** |delta| in range-widths, so misses are comparable across metrics. */
  delta_normalized: number | null;
  /** False when this camera angle cannot measure what the metric claims to. */
  reliable: boolean;
  unreliable_reason: string | null;
  description: string;
}

export interface ReferenceSummary {
  id: string;
  display_name: string;
  handedness: string;
  camera_view: CameraView;
  source: string;
  license: string;
  has_video: boolean;
}

export interface ComparisonMetric {
  key: string;
  label: string;
  unit: string;
  user_value: number;
  reference_value: number;
  difference: number;
  ideal_range: [number, number] | null;
  user_assessment: "good" | "watch" | null;
  lower_is_better: boolean;
  /** |difference| in ideal-band widths. Null when the metric has no band. */
  gap_normalized: number | null;
  /** True for metrics that never touch the projection, e.g. tempo. */
  view_independent: boolean;
}

export interface SkippedMetric {
  key: string;
  label: string;
  reason: string;
}

export interface Comparison {
  reference: ReferenceSummary & { frontality: number | null };
  camera: {
    user_view: CameraView;
    reference_view: CameraView;
    compatible: boolean;
    reason: string | null;
  };
  rotation_note: string | null;
  metrics: ComparisonMetric[];
  skipped: SkippedMetric[];
}

/** Everything needed to draw a reference skeleton over a user's video. */
export interface Overlay {
  /** user frame index -> reference frame index. Monotonic. */
  frame_map: number[];
  anchor_frame: number;
  scale: number;
  mirrored: boolean;
  reference_name: string;
  edges: [number, number][];
  user: {
    fps: number;
    n_frames: number;
    width: number;
    height: number;
    hip_centers: [number, number][];
  };
  reference: {
    n_frames: number;
    width: number;
    height: number;
    hip_centers: [number, number][];
    /** (n_frames, 17, 3) of [x, y, confidence] in reference pixel space. */
    keypoints: number[][][];
  };
}

export type CameraView = "face_on" | "oblique" | "down_the_line" | "unknown";

export interface CameraInfo {
  view: CameraView;
  /** Shoulder width over torso length at address. Low means end-on to the camera. */
  frontality: number | null;
  rotation_measurable: boolean;
}

export interface KinematicSequence {
  available: boolean;
  reason?: string;
  order?: string[];
  peak_frames?: Record<string, number>;
  proximal_to_distal?: boolean;
}

export interface SwingMetrics {
  /** Absent on analyses stored before camera-view detection landed. */
  camera?: CameraInfo;
  summary: MetricEntry[];
  series: Record<string, (number | null)[]>;
  kinematic_sequence: KinematicSequence;
  events: Record<string, number>;
  fps: number;
  handedness: string;
  notes: string[];
  warnings?: string[];
}

export interface Drill {
  id: string;
  name: string;
  fixes: string;
  how_to: string;
}

/** The numbers the backend attached — the model wrote none of these. */
export interface CoachingMetricContext {
  label: string;
  value: number | null;
  unit: string;
  ideal_range: [number, number] | null;
  delta: number | null;
  delta_normalized: number | null;
  assessment: "good" | "watch" | null;
  lower_is_better: boolean;
}

export interface CoachingImprovement {
  metric_key: string;
  issue: string;
  why_it_matters: string;
  /** Absent on analyses stored before the drill library landed. */
  metric_context?: CoachingMetricContext;
  drills?: Drill[];
  /** Legacy free-text drill, pre-drill-library. */
  drill?: string;
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
