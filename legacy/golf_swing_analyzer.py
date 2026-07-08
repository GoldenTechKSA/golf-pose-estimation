#!/usr/bin/env python3
"""
Golf Swing Analyzer
Provides phase-specific biomechanics feedback and exports analysis data.
"""
import pandas as pd
from typing import List, Dict, Optional


class GolfSwingAnalyzer:
    """
    Analyzes golf swing metrics and provides coaching feedback by phase.

    Stores metrics for each phase separately and provides phase-specific
    feedback based on biomechanics guidelines.
    """

    def __init__(self):
        """Initialize the analyzer with empty metric storage."""
        # Store all frame data for export
        self.frame_data: List[Dict] = []

        # Store metrics by phase for summary statistics
        self.phase_metrics: Dict[str, List[Dict]] = {
            "Address": [],
            "Backswing": [],
            "Top": [],
            "Downswing": [],
            "Follow-through": []
        }

    def analyze_phase(self, phase: str, metrics: dict) -> List[str]:
        """
        Analyze metrics for current phase and return feedback.

        Args:
            phase: Current swing phase name
            metrics: Dictionary with biomechanics metrics

        Returns:
            List of feedback strings with symbols
        """
        if not metrics:
            return []

        # Store metrics for this phase
        if phase in self.phase_metrics:
            self.phase_metrics[phase].append(metrics.copy())

        # Get phase-specific feedback
        if phase == "Address":
            return self._analyze_address(metrics)
        elif phase == "Backswing":
            return self._analyze_backswing(metrics)
        elif phase == "Top":
            return self._analyze_top(metrics)
        elif phase == "Downswing":
            return self._analyze_downswing(metrics)
        elif phase == "Follow-through":
            return self._analyze_followthrough(metrics)

        return []

    def _analyze_address(self, metrics: dict) -> List[str]:
        """
        Analyze Address phase metrics.

        Checks:
        - Shoulder level (rotation < 15 deg)
        - Knee flex (angles < 170 deg)
        - Posture
        """
        feedback = []

        shoulder_rotation = abs(metrics.get('shoulder_rotation', 0))
        right_knee = metrics.get('right_knee_angle', 180)
        left_knee = metrics.get('left_knee_angle', 180)

        # Check shoulder level
        if shoulder_rotation < 15:
            feedback.append("Good shoulder alignment")
        else:
            feedback.append("Level your shoulders")

        # Check knee flex
        avg_knee = (right_knee + left_knee) / 2
        if avg_knee < 170:
            feedback.append("Good knee flex")
        else:
            feedback.append("Bend knees slightly more")

        # Check posture via arm angles
        right_arm = metrics.get('right_arm_angle', 180)
        left_arm = metrics.get('left_arm_angle', 180)
        if right_arm > 140 and left_arm > 140:
            feedback.append("Arms nicely extended")

        return feedback

    def _analyze_backswing(self, metrics: dict) -> List[str]:
        """
        Analyze Backswing phase metrics.

        Checks:
        - Shoulder rotation (> 40 deg, excellent if > 60 deg)
        - Hip rotation (should be less than shoulders)
        - Right arm bend (80-120 deg)
        """
        feedback = []

        shoulder_rotation = abs(metrics.get('shoulder_rotation', 0))
        hip_rotation = abs(metrics.get('hip_rotation', 0))
        right_arm = metrics.get('right_arm_angle', 180)

        # Check shoulder rotation
        if shoulder_rotation > 60:
            feedback.append("Excellent shoulder turn")
        elif shoulder_rotation > 40:
            feedback.append("Good shoulder turn")
        else:
            feedback.append("Rotate shoulders more")

        # Check hip-shoulder separation (X-factor)
        if hip_rotation < shoulder_rotation * 0.7:
            feedback.append("Good hip resistance")
        else:
            feedback.append("Resist hip turn more")

        # Check right arm bend
        if 80 <= right_arm <= 120:
            feedback.append("Good right arm position")
        elif right_arm > 120:
            feedback.append("Bend right elbow more")

        return feedback

    def _analyze_top(self, metrics: dict) -> List[str]:
        """
        Analyze Top of swing metrics.

        Checks:
        - Shoulder rotation (60-90 deg, excellent if > 80 deg)
        - Left arm straight (> 150 deg)
        - Hip rotation (40-60 deg for separation)
        """
        feedback = []

        shoulder_rotation = abs(metrics.get('shoulder_rotation', 0))
        hip_rotation = abs(metrics.get('hip_rotation', 0))
        left_arm = metrics.get('left_arm_angle', 180)

        # Check shoulder rotation at top
        if shoulder_rotation > 80:
            feedback.append("Excellent coil at top")
        elif shoulder_rotation > 60:
            feedback.append("Good shoulder turn")
        else:
            feedback.append("Turn shoulders more")

        # Check left arm straight
        if left_arm > 150:
            feedback.append("Left arm nicely straight")
        else:
            feedback.append("Keep left arm straighter")

        # Check hip rotation for separation
        if 40 <= hip_rotation <= 60:
            feedback.append("Great hip-shoulder separation")
        elif hip_rotation < 40:
            feedback.append("Good hip restriction")
        else:
            feedback.append("Restrict hip turn more")

        return feedback

    def _analyze_downswing(self, metrics: dict) -> List[str]:
        """
        Analyze Downswing phase metrics.

        Checks:
        - Hips leading shoulders
        - Weight shift (left knee < right knee)
        """
        feedback = []

        shoulder_rotation = abs(metrics.get('shoulder_rotation', 0))
        hip_rotation = abs(metrics.get('hip_rotation', 0))
        right_knee = metrics.get('right_knee_angle', 180)
        left_knee = metrics.get('left_knee_angle', 180)

        # Check hips leading shoulders
        if hip_rotation > shoulder_rotation:
            feedback.append("Good hip lead")
        else:
            feedback.append("Fire hips first")

        # Check weight shift
        if left_knee < right_knee:
            feedback.append("Good weight transfer")
        else:
            feedback.append("Shift weight to front foot")

        # Check maintaining angles
        if left_knee < 160:
            feedback.append("Good front knee flex")

        return feedback

    def _analyze_followthrough(self, metrics: dict) -> List[str]:
        """
        Analyze Follow-through phase metrics.

        Checks:
        - Full hip rotation (negative/reversed)
        - Both arms extended (> 150 deg)
        - Weight on front foot (left knee < 140 deg)
        """
        feedback = []

        hip_rotation = metrics.get('hip_rotation', 0)
        right_arm = metrics.get('right_arm_angle', 180)
        left_arm = metrics.get('left_arm_angle', 180)
        left_knee = metrics.get('left_knee_angle', 180)

        # Check hip rotation (should be negative/reversed through target)
        if hip_rotation < -30:
            feedback.append("Great hip rotation through")
        elif hip_rotation < 0:
            feedback.append("Good hip release")
        else:
            feedback.append("Rotate hips through more")

        # Check arm extension
        if right_arm > 150 and left_arm > 150:
            feedback.append("Full arm extension")
        else:
            feedback.append("Extend arms through ball")

        # Check weight on front foot
        if left_knee < 140:
            feedback.append("Good balance on front foot")
        else:
            feedback.append("Finish with weight forward")

        return feedback

    def add_frame_data(self, frame_number: int, phase: str, metrics: dict):
        """
        Store frame data for CSV export.

        Args:
            frame_number: Current frame number
            phase: Current phase name
            metrics: Dictionary with all metrics
        """
        frame_entry = {
            'frame_number': frame_number,
            'phase': phase,
            'right_arm_angle': metrics.get('right_arm_angle', 0),
            'left_arm_angle': metrics.get('left_arm_angle', 0),
            'right_knee_angle': metrics.get('right_knee_angle', 0),
            'left_knee_angle': metrics.get('left_knee_angle', 0),
            'shoulder_rotation': metrics.get('shoulder_rotation', 0),
            'hip_rotation': metrics.get('hip_rotation', 0)
        }
        self.frame_data.append(frame_entry)

    def get_phase_summary(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Get summary statistics for each metric by phase.

        Returns:
            Nested dict: phase -> metric -> {mean, min, max}
        """
        summary = {}

        for phase, metrics_list in self.phase_metrics.items():
            if not metrics_list:
                continue

            summary[phase] = {}

            # Get all metric names from first entry
            metric_names = [
                'right_arm_angle', 'left_arm_angle',
                'right_knee_angle', 'left_knee_angle',
                'shoulder_rotation', 'hip_rotation'
            ]

            for metric in metric_names:
                values = [m.get(metric, 0) for m in metrics_list if metric in m]
                if values:
                    summary[phase][metric] = {
                        'mean': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values)
                    }

        return summary

    def export_swing_data(self, output_path: str = "swing_analysis.csv"):
        """
        Export summary statistics per phase to CSV.

        Args:
            output_path: Path for output CSV file
        """
        summary = self.get_phase_summary()

        if not summary:
            print("No data to export")
            return

        # Build rows for CSV - one row per phase with avg metrics
        rows = []
        phase_order = ["Address", "Backswing", "Top", "Downswing", "Follow-through"]

        for phase in phase_order:
            if phase not in summary:
                continue

            phase_data = summary[phase]
            num_frames = len(self.phase_metrics.get(phase, []))

            row = {
                'phase': phase,
                'frames': num_frames,
                'right_arm_angle': round(phase_data.get('right_arm_angle', {}).get('mean', 0), 1),
                'left_arm_angle': round(phase_data.get('left_arm_angle', {}).get('mean', 0), 1),
                'right_knee_angle': round(phase_data.get('right_knee_angle', {}).get('mean', 0), 1),
                'left_knee_angle': round(phase_data.get('left_knee_angle', {}).get('mean', 0), 1),
                'shoulder_rotation': round(phase_data.get('shoulder_rotation', {}).get('mean', 0), 1),
                'hip_rotation': round(phase_data.get('hip_rotation', {}).get('mean', 0), 1)
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # Reorder columns
        columns = [
            'phase', 'frames',
            'right_arm_angle', 'left_arm_angle',
            'right_knee_angle', 'left_knee_angle',
            'shoulder_rotation', 'hip_rotation'
        ]
        df = df[columns]

        df.to_csv(output_path, index=False)
        print(f"Exported summary for {len(rows)} phases to {output_path}")

    def print_summary(self):
        """Print a summary of the swing analysis."""
        summary = self.get_phase_summary()

        print("\n" + "=" * 60)
        print("SWING ANALYSIS SUMMARY")
        print("=" * 60)

        for phase in ["Address", "Backswing", "Top", "Downswing", "Follow-through"]:
            if phase not in summary:
                continue

            print(f"\n{phase}:")
            print("-" * 40)

            phase_data = summary[phase]
            for metric, stats in phase_data.items():
                print(f"  {metric}: {stats['mean']:.1f} (min: {stats['min']:.1f}, max: {stats['max']:.1f})")

        print("\n" + "=" * 60)

    def reset(self):
        """Reset analyzer for new video."""
        self.frame_data = []
        self.phase_metrics = {
            "Address": [],
            "Backswing": [],
            "Top": [],
            "Downswing": [],
            "Follow-through": []
        }
