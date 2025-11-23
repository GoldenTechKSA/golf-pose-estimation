# Golf Swing Analyzer - Technical Documentation

## Project Overview

A computer vision-based golf swing analyzer using Google's MediaPipe Pose estimation. The system processes golf swing videos to detect body pose, automatically identify swing phases, calculate biomechanical metrics, and provide real-time coaching feedback.

## Architecture

```
golf_pose_rtm/
├── analyze_golf_mediapipe.py    # Main entry point
├── swing_phase_detector.py      # Phase detection logic
├── golf_swing_analyzer.py       # Feedback and data export
├── input/                        # Input videos
├── outputs/                      # Output videos + CSV
├── requirements.txt
└── DOCUMENTATION.md
```

## Core Components

### 1. MediaPipeGolfAnalyzer (analyze_golf_mediapipe.py)

The main class that orchestrates video processing, pose detection, and visualization.

**Initialization:**
```python
class MediaPipeGolfAnalyzer:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,      # Maximum accuracy
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.phase_detector = SwingPhaseDetector()
        self.swing_analyzer = GolfSwingAnalyzer()
```

**Key Methods:**

- `calculate_angle(a, b, c)`: Calculates the angle at point `b` formed by points `a-b-c` using arctangent. Returns degrees (0-180).

- `analyze_pose(landmarks)`: Extracts 6 biomechanical metrics from MediaPipe landmarks:
  - Right/Left Arm Angle (shoulder-elbow-wrist)
  - Right/Left Knee Angle (hip-knee-ankle)
  - Shoulder Rotation (slope of shoulder line)
  - Hip Rotation (slope of hip line)

- `process_video(video_path, output_path, show_metrics)`: Main processing loop that:
  1. Reads video frame by frame
  2. Detects pose with MediaPipe
  3. Calculates metrics
  4. Detects swing phase
  5. Generates feedback
  6. Draws overlays
  7. Exports data to CSV

### 2. SwingPhaseDetector (swing_phase_detector.py)

Detects 5 golf swing phases based on wrist position and velocity.

**Phases:**
1. **Address**: Low velocity, wrists at low position
2. **Backswing**: Wrists moving upward (negative y-velocity)
3. **Top**: High position, velocity near zero
4. **Downswing**: Wrists moving downward rapidly (positive y-velocity)
5. **Follow-through**: After downswing, wrists moving upward again

**Key Parameters:**
```python
LOW_VELOCITY = 5.0    # Threshold for "slow" movement
HIGH_VELOCITY = 15.0  # Threshold for "fast" movement
window_size = 5       # Frames to track for velocity calculation
```

**Algorithm:**
```python
def update(self, left_wrist, right_wrist, frame_number):
    # Average both wrists
    wrist_pos = (left_wrist + right_wrist) / 2

    # Calculate velocity from position change
    velocity = current_pos - previous_pos
    vertical_velocity = velocity[1]  # y-component

    # Detect phase based on velocity patterns
    return self._detect_phase(wrist_pos, vel_magnitude, vertical_velocity)
```

**Coordinate System Notes:**
- Image coordinates: (0,0) is top-left
- y increases downward
- Upward motion = negative y-velocity
- Downward motion = positive y-velocity

### 3. GolfSwingAnalyzer (golf_swing_analyzer.py)

Provides phase-specific coaching feedback and handles data export.

**Phase-Specific Analysis:**

**Address Phase:**
- Shoulder alignment (rotation < 15°)
- Knee flex (angles < 170°)
- Arm extension

**Backswing Phase:**
- Shoulder rotation (> 40° good, > 60° excellent)
- Hip-shoulder separation (hip < shoulder × 0.7)
- Right arm bend (80-120°)

**Top Phase:**
- Shoulder coil (60-90°, > 80° excellent)
- Left arm straight (> 150°)
- Hip restriction (40-60°)

**Downswing Phase:**
- Hips leading shoulders
- Weight transfer to front foot

**Follow-through Phase:**
- Hip rotation through target (< -30°)
- Arm extension (> 150°)
- Balance on front foot (left knee < 140°)

**Data Export:**
```python
def export_swing_data(self, output_path):
    # Creates CSV with columns:
    # phase, frame_number, right_arm_angle, left_arm_angle,
    # right_knee_angle, left_knee_angle, shoulder_rotation, hip_rotation
```

## MediaPipe Landmark Indices

```python
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
```

## Video Processing Pipeline

```
Input Video
    ↓
Read Frame (BGR)
    ↓
Convert to RGB
    ↓
MediaPipe Pose Detection
    ↓
Extract 33 Landmarks
    ↓
Calculate 6 Biomechanics Metrics
    ↓
Detect Swing Phase (via wrist velocity)
    ↓
Generate Phase-Specific Feedback
    ↓
Draw Overlays:
  - Skeleton (green points, red lines)
  - Phase label (top center, yellow)
  - Metrics (left side, green)
  - Feedback (right side, green/orange)
    ↓
Write Frame to Output Video
    ↓
Store Frame Data for CSV
    ↓
Repeat until video ends
    ↓
Export CSV + Print Summary
```

## Usage

### Basic Usage
```bash
python analyze_golf_mediapipe.py --video golftrain-luke.mp4
```

### With Custom Output
```bash
python analyze_golf_mediapipe.py --video input/swing.mp4 --output outputs/analyzed.mp4
```

### Disable Metrics Overlay
```bash
python analyze_golf_mediapipe.py --video swing.mp4 --no-metrics
```

### Input Path Resolution
The script automatically checks:
1. Exact path provided
2. If not found, looks in `input/` folder

## Output Files

### Analyzed Video
- Location: `outputs/{video_name}_analyzed.mp4`
- Contains: Skeleton overlay, phase label, metrics, feedback

### CSV Data
- Location: `outputs/swing_analysis.csv`
- Format:
```csv
phase,frame_number,right_arm_angle,left_arm_angle,right_knee_angle,left_knee_angle,shoulder_rotation,hip_rotation
Address,0,154.2,173.1,154.3,178.8,-15.6,-10.8
Backswing,15,155.9,173.1,140.5,175.6,-11.1,-10.9
...
```

### Console Summary
```
SWING ANALYSIS SUMMARY
============================================================

Address:
----------------------------------------
  right_arm_angle: 154.2 (min: 152.4, max: 155.6)
  left_arm_angle: 173.1 (min: 169.6, max: 176.7)
  ...

Backswing:
----------------------------------------
  ...
```

## Visualization Details

### Colors (BGR format)
- Skeleton points: Green (0, 255, 0)
- Skeleton lines: Red (0, 0, 255)
- Phase label: Yellow (255, 255, 0)
- Metrics text: Green (0, 255, 0)
- Positive feedback: Green (0, 255, 0)
- Warning feedback: Orange (0, 165, 255)
- Feedback title: Cyan (0, 255, 255)

### Text Positioning
- Phase label: Top center, font size 1.2
- Metrics: Left side starting at y=80, font size 0.5
- Feedback: Right side (width - 350), font size 0.45

## Dependencies

```
mediapipe>=0.10.0    # Pose estimation
opencv-python>=4.8.0 # Video processing
numpy>=1.22.0,<2.0.0 # Numerical operations
pandas>=2.0.0        # CSV export
```

## Performance

- Processing speed: ~15-30 FPS on modern CPU (model_complexity=2)
- Memory usage: Minimal (frame-by-frame processing)
- Supported formats: MP4, AVI, MOV

## Limitations

1. **Single person**: Only analyzes one golfer per video
2. **Side view recommended**: Best accuracy with camera perpendicular to swing plane
3. **Lighting sensitive**: Poor lighting reduces pose detection accuracy
4. **Fast motion blur**: Very fast swings may have reduced accuracy during impact
5. **Phase detection tuning**: Velocity thresholds may need adjustment for different video framerates

## Tuning Phase Detection

If phases aren't detected correctly, adjust in `swing_phase_detector.py`:

```python
LOW_VELOCITY = 5.0   # Increase if staying in Address too long
HIGH_VELOCITY = 15.0 # Decrease if missing Downswing detection
window_size = 5      # Increase for smoother velocity, decrease for faster response
```

## Extending the System

### Adding New Metrics
1. Add calculation in `analyze_pose()` method
2. Update feedback rules in `GolfSwingAnalyzer`
3. Add column to CSV export in `add_frame_data()`

### Adding New Phases
1. Update phase list in `SwingPhaseDetector`
2. Add detection logic in `_detect_phase()`
3. Add analysis method in `GolfSwingAnalyzer` (e.g., `_analyze_newphase()`)

### Customizing Feedback
Edit the `_analyze_*` methods in `GolfSwingAnalyzer` to change:
- Threshold values
- Feedback messages
- Number of feedback items

## Troubleshooting

### Video won't open
- Check file path and extension
- Ensure video is in `input/` folder or provide full path

### Poor phase detection
- Adjust velocity thresholds
- Ensure good lighting
- Use side-view camera angle

### Low pose accuracy
- Increase `model_complexity` (max 2)
- Increase confidence thresholds
- Improve video quality/lighting

### CSV not generated
- Check `outputs/` folder exists
- Ensure pandas is installed
- Check for write permissions

## References

- MediaPipe Pose: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
- Golf biomechanics: Based on standard PGA teaching principles
- OpenCV VideoWriter: https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
