"""
Inference script for RTMPose on golf videos
Processes videos frame-by-frame and visualizes keypoints
"""
import os
import argparse
import numpy as np
import cv2
import torch
from typing import List, Tuple, Optional

import config
from models import create_rtmpose, load_checkpoint
from utils.transforms import normalize_image, simcc_to_keypoints, resize_with_keypoints
from utils.visualization import draw_keypoints


class OneEuroFilter:
    """
    One Euro Filter for smoothing keypoint predictions across frames
    Reduces jitter while maintaining responsiveness
    """

    def __init__(self, min_cutoff=1.0, beta=0.007):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.dx_prev = None
        self.x_prev = None
        self.t_prev = None

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        """
        Apply filter to input value

        Args:
            x: current value (e.g., keypoint coordinates)
            t: current timestamp

        Returns:
            filtered value
        """
        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = np.zeros_like(x)
            self.t_prev = t
            return x

        # Calculate time difference
        dt = t - self.t_prev
        if dt <= 0:
            return self.x_prev

        # Calculate derivative
        dx = (x - self.x_prev) / dt

        # Smooth derivative
        alpha_d = self._alpha(1.0)
        dx_hat = self._exponential_smoothing(dx, self.dx_prev, alpha_d)

        # Calculate cutoff frequency
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)

        # Smooth value
        alpha = self._alpha(cutoff)
        x_hat = self._exponential_smoothing(x, self.x_prev, alpha)

        # Update state
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat

    def _alpha(self, cutoff: float) -> float:
        """Calculate smoothing factor"""
        tau = 1.0 / (2 * np.pi * cutoff)
        return 1.0 / (1.0 + tau)

    def _exponential_smoothing(self, x: np.ndarray, x_prev: np.ndarray, alpha: float) -> np.ndarray:
        """Apply exponential smoothing"""
        return alpha * x + (1 - alpha) * x_prev


class VideoProcessor:
    """
    Process videos with RTMPose model
    """

    def __init__(
        self,
        model: torch.nn.Module,
        device: str = 'cpu',
        use_smoothing: bool = True
    ):
        self.model = model
        self.device = device
        self.use_smoothing = use_smoothing
        self.model.eval()

        # Initialize filters for each keypoint (x, y coordinates)
        if use_smoothing:
            self.filters = [OneEuroFilter() for _ in range(config.NUM_KEYPOINTS * 2)]

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        conf_threshold: float = 0.3
    ) -> np.ndarray:
        """
        Process a single frame

        Args:
            frame: numpy array of shape (H, W, 3) in BGR format
            timestamp: current timestamp in seconds
            conf_threshold: confidence threshold for visualization

        Returns:
            keypoints: numpy array of shape (num_keypoints, 3) - [x, y, confidence]
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get original size
        orig_height, orig_width = frame_rgb.shape[:2]

        # Resize to model input size
        frame_resized = cv2.resize(
            frame_rgb,
            (config.INPUT_WIDTH, config.INPUT_HEIGHT),
            interpolation=cv2.INTER_LINEAR
        )

        # Normalize and convert to tensor
        frame_tensor = normalize_image(frame_resized)
        frame_tensor = frame_tensor.unsqueeze(0).to(self.device)  # Add batch dimension

        # Run inference
        with torch.no_grad():
            pred_x, pred_y = self.model(frame_tensor)

            # Apply softmax to get distributions
            pred_x = torch.softmax(pred_x, dim=-1)
            pred_y = torch.softmax(pred_y, dim=-1)

            # Convert to keypoints
            keypoints = simcc_to_keypoints(
                pred_x[0].cpu().numpy(),
                pred_y[0].cpu().numpy(),
                threshold=conf_threshold
            )

        # Apply temporal smoothing
        if self.use_smoothing:
            smoothed_coords = []
            for i in range(config.NUM_KEYPOINTS):
                if keypoints[i, 2] > conf_threshold:  # Only smooth visible keypoints
                    # Smooth x coordinate
                    x_smooth = self.filters[i * 2](keypoints[i, 0:1], timestamp)[0]
                    # Smooth y coordinate
                    y_smooth = self.filters[i * 2 + 1](keypoints[i, 1:2], timestamp)[0]
                    smoothed_coords.append([x_smooth, y_smooth, keypoints[i, 2]])
                else:
                    smoothed_coords.append(keypoints[i])
            keypoints = np.array(smoothed_coords, dtype=np.float32)

        # Scale keypoints back to original frame size
        keypoints[:, 0] *= (orig_width / config.INPUT_WIDTH)
        keypoints[:, 1] *= (orig_height / config.INPUT_HEIGHT)

        return keypoints

    def process_video(
        self,
        input_path: str,
        output_path: str,
        conf_threshold: float = 0.3,
        show_progress: bool = True
    ):
        """
        Process entire video

        Args:
            input_path: path to input video
            output_path: path to save output video
            conf_threshold: confidence threshold for visualization
            show_progress: whether to show progress
        """
        # Open video
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Video properties:")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  Total frames: {total_frames}")

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Process frames
        frame_idx = 0
        start_time = cv2.getTickCount()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Calculate timestamp
            timestamp = frame_idx / fps

            # Process frame
            keypoints = self.process_frame(frame, timestamp, conf_threshold)

            # Convert to RGB for drawing
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Draw keypoints
            frame_annotated = draw_keypoints(frame_rgb, keypoints, confidence_threshold=conf_threshold)

            # Convert back to BGR for video writing
            frame_annotated = cv2.cvtColor(frame_annotated, cv2.COLOR_RGB2BGR)

            # Write frame
            out.write(frame_annotated)

            # Show progress
            if show_progress and (frame_idx + 1) % 30 == 0:
                elapsed = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
                fps_processed = (frame_idx + 1) / elapsed
                progress = (frame_idx + 1) / total_frames * 100
                print(f"Progress: {frame_idx + 1}/{total_frames} ({progress:.1f}%) "
                      f"- {fps_processed:.1f} FPS")

            frame_idx += 1

        # Cleanup
        cap.release()
        out.release()

        # Final stats
        elapsed = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
        avg_fps = total_frames / elapsed
        print(f"\nProcessing completed!")
        print(f"  Total time: {elapsed:.1f}s")
        print(f"  Average FPS: {avg_fps:.1f}")
        print(f"  Output saved to: {output_path}")


def analyze_swing_phases(
    keypoints_sequence: List[np.ndarray],
    fps: int
) -> dict:
    """
    Analyze golf swing phases from keypoint sequence

    Args:
        keypoints_sequence: list of keypoint arrays (num_keypoints, 3)
        fps: video frame rate

    Returns:
        dict containing swing phase analysis
    """
    # Simple heuristic-based phase detection
    # In a real implementation, this would be more sophisticated

    # Track right wrist position (index 10) over time
    wrist_positions = []
    for kpts in keypoints_sequence:
        if kpts[10, 2] > 0.3:  # If wrist is visible
            wrist_positions.append(kpts[10, :2])  # x, y coordinates

    if len(wrist_positions) < 10:
        return {"error": "Not enough visible frames for analysis"}

    wrist_positions = np.array(wrist_positions)

    # Calculate velocities
    velocities = np.diff(wrist_positions, axis=0)
    speeds = np.linalg.norm(velocities, axis=1)

    # Find key events
    max_speed_idx = np.argmax(speeds)
    impact_frame = max_speed_idx

    # Estimate phases
    analysis = {
        "total_frames": len(keypoints_sequence),
        "duration_sec": len(keypoints_sequence) / fps,
        "impact_frame": int(impact_frame),
        "max_speed": float(speeds[max_speed_idx]),
        "phases": {
            "address": 0,
            "backswing": int(impact_frame * 0.3),
            "downswing": int(impact_frame * 0.7),
            "impact": int(impact_frame),
            "follow_through": int(impact_frame + 10)
        }
    }

    return analysis


def main():
    parser = argparse.ArgumentParser(description='RTMPose inference on videos')
    parser.add_argument('--video', type=str, required=True,
                        help='path to input video')
    parser.add_argument('--output', type=str, default=None,
                        help='path to output video (default: input_name_output.mp4)')
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='path to model checkpoint')
    parser.add_argument('--device', type=str, default=config.DEVICE,
                        help='device to use (cuda/cpu)')
    parser.add_argument('--conf-threshold', type=float, default=0.3,
                        help='confidence threshold for keypoints')
    parser.add_argument('--no-smoothing', action='store_true',
                        help='disable temporal smoothing')

    args = parser.parse_args()

    # Set default output path
    if args.output is None:
        base_name = os.path.splitext(args.video)[0]
        args.output = f"{base_name}_output.mp4"

    # Load model
    print(f"Loading model from {args.checkpoint}...")
    model = create_rtmpose(pretrained=False)
    model, epoch, best_pck = load_checkpoint(model, args.checkpoint, device=args.device)
    model = model.to(args.device)

    # Create processor
    processor = VideoProcessor(
        model=model,
        device=args.device,
        use_smoothing=not args.no_smoothing
    )

    # Process video
    print(f"\nProcessing video: {args.video}")
    processor.process_video(
        input_path=args.video,
        output_path=args.output,
        conf_threshold=args.conf_threshold
    )


if __name__ == '__main__':
    main()
