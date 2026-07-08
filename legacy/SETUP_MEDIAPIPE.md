# MediaPipe Golf Swing Analyzer - Complete Setup

**No training, no COCO dataset, no weight downloads needed!**

MediaPipe is Google's production-ready pose estimation solution with built-in pretrained models.

## Quick Start (5 Minutes)

### Step 1: Install MediaPipe

```bash
cd /Users/lukesarausad/Desktop/golf_pose_rtm
pip install mediapipe
```

### Step 2: Verify Installation

```bash
python -c "import mediapipe as mp; print('✓ MediaPipe installed successfully!')"
```

### Step 3: Analyze a Golf Video

```bash
# Use your own golf video
python analyze_golf_mediapipe.py --video your_golf_swing.mp4

# Output: your_golf_swing_analyzed.mp4
```

That's it! You're done.

---

## What You Get

MediaPipe provides **33 keypoints** (vs 17 in COCO):

**Upper Body:**
- Face: nose, eyes, ears, mouth
- Arms: shoulders, elbows, wrists
- Hands: thumb, index, pinky

**Lower Body:**
- Torso: hips
- Legs: knees, ankles, heels, toes

**For Golf Analysis:**
- Shoulder rotation
- Hip rotation
- Arm angles (both left and right)
- Knee flex
- Weight shift (ankle/heel positions)

---

## Example Usage

### Basic Analysis

```bash
python analyze_golf_mediapipe.py --video golf_swing.mp4
```

Creates `golf_swing_analyzed.mp4` with:
- Skeleton overlay (green dots, red lines)
- Biomechanics metrics (text overlay)

### Just Skeleton (No Metrics)

```bash
python analyze_golf_mediapipe.py --video golf_swing.mp4 --no-metrics
```

### Custom Output Path

```bash
python analyze_golf_mediapipe.py \
  --video golf_swing.mp4 \
  --output results/analyzed.mp4
```

---

## Understanding the Output

### Metrics Displayed:

1. **Right Arm Angle**: Shoulder-Elbow-Wrist angle
   - ~180° = straight arm (address)
   - ~90° = bent arm (backswing)

2. **Left Arm Angle**: Same for left arm

3. **Right Knee Angle**: Hip-Knee-Ankle angle
   - Tracks knee flex through swing

4. **Left Knee Angle**: Same for left knee

5. **Shoulder Rotation**: Tilt of shoulder line
   - Positive/negative indicates rotation direction

6. **Hip Rotation**: Tilt of hip line
   - Shows hip turn through swing

---

## Creating Test Videos

### Option 1: Record Yourself

```bash
# Use your phone to record a golf swing
# Transfer video to computer
python analyze_golf_mediapipe.py --video my_swing.mp4
```

### Option 2: Download from YouTube

```bash
# Install youtube-dl (if needed)
pip install yt-dlp

# Download a golf instruction video
yt-dlp "https://youtube.com/watch?v=VIDEO_ID" -o golf_sample.mp4

# Analyze it
python analyze_golf_mediapipe.py --video golf_sample.mp4
```

### Option 3: Use Webcam (Live Analysis)

Create `live_golf_analysis.py`:

```python
import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)  # Webcam

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Process
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)

    # Draw
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow('Live Golf Analysis', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

Run: `python live_golf_analysis.py`

---

## Project Ideas

### 1. Swing Phase Detection

Track wrist position over time to detect:
- Address
- Backswing
- Top of swing
- Downswing
- Impact
- Follow-through

```python
# Pseudo-code
wrist_positions = []
for frame in video:
    wrist_y = landmarks[RIGHT_WRIST].y
    wrist_positions.append(wrist_y)

# Find peaks/valleys
backswing_peak = max(wrist_positions[:len//2])
impact_point = detect_impact(wrist_positions)
```

### 2. Pro vs Amateur Comparison

```bash
# Analyze both
python analyze_golf_mediapipe.py --video pro_swing.mp4
python analyze_golf_mediapipe.py --video amateur_swing.mp4

# Then create side-by-side comparison
# Or plot metrics over time
```

### 3. Swing Metrics Over Time

Extract metrics to CSV:

```python
import pandas as pd

metrics_over_time = []
for frame_idx, metrics in enumerate(all_metrics):
    metrics['frame'] = frame_idx
    metrics['time'] = frame_idx / fps
    metrics_over_time.append(metrics)

df = pd.DataFrame(metrics_over_time)
df.to_csv('swing_analysis.csv')

# Plot
import matplotlib.pyplot as plt
plt.plot(df['time'], df['shoulder_rotation'])
plt.xlabel('Time (s)')
plt.ylabel('Shoulder Rotation (degrees)')
plt.title('Shoulder Rotation During Swing')
plt.savefig('shoulder_rotation.png')
```

### 4. Club Speed Estimation

Track wrist velocity:

```python
wrist_positions = []  # (x, y) for each frame

# Calculate velocity
velocities = []
for i in range(1, len(wrist_positions)):
    dx = wrist_positions[i][0] - wrist_positions[i-1][0]
    dy = wrist_positions[i][1] - wrist_positions[i-1][1]
    velocity = np.sqrt(dx**2 + dy**2) * fps  # pixels/second
    velocities.append(velocity)

max_velocity = max(velocities)
# Convert to approximate club speed using calibration
```

---

## Advantages of MediaPipe for Your Project

### ✅ Technical Benefits:

1. **Production-Ready**: Used in real apps (not just research)
2. **Optimized**: Runs fast even on CPU
3. **Robust**: Handles occlusions, motion blur
4. **More Keypoints**: 33 vs 17 (better biomechanics)

### ✅ For Your Report:

You can still discuss:
- **Computer Vision Concepts**: Pose estimation, transfer learning
- **MediaPipe Architecture**: Lightweight CNN models
- **Real-time Processing**: Optimization techniques
- **Application Domain**: Golf-specific adaptations

### ✅ Time Savings:

- No COCO download (saves 20GB, hours)
- No training (saves days)
- No GPU needed
- No debugging weight loading
- **Focus on golf analysis** (the interesting part!)

---

## For Your CSE 455 Project

### Report Structure:

**1. Introduction**
- Pose estimation for sports analysis
- Why golf? (clear phases, measurable biomechanics)

**2. Background**
- Pose estimation approaches (heatmaps vs. regression)
- MediaPipe architecture (briefly)
- Transfer learning (trained on diverse data → golf)

**3. Methodology**
- MediaPipe Pose model
- Golf-specific biomechanics calculations
- Swing phase detection algorithm
- Metrics extraction

**4. Implementation**
- Video processing pipeline
- Angle calculations
- Visualization

**5. Experiments**
- Multiple golf videos analyzed
- Pro vs amateur comparison
- Metrics validation (compare to golf literature)

**6. Results**
- Detected keypoints visualization
- Biomechanics over time plots
- Swing phase labels
- Quantitative comparisons

**7. Discussion**
- What works well
- Limitations (side view better than front, etc.)
- Future work (3D pose, real-time coaching)

**8. Conclusion**
- Successfully applied CV to golf analysis
- Extracted meaningful biomechanics
- Practical tool for swing improvement

---

## Troubleshooting

### "mediapipe not found"

```bash
pip install mediapipe
# If that fails:
pip install --upgrade pip
pip install mediapipe
```

### "No landmarks detected"

- Check video quality (clear, good lighting)
- Person should be clearly visible
- Try different camera angle (side view best for golf)

### Slow processing

```bash
# MediaPipe is already optimized for CPU
# But you can reduce model complexity:
# Edit analyze_golf_mediapipe.py line 23:
model_complexity=1  # Instead of 2 (0=fastest, 2=best)
```

### Wrong angles

- Angles depend on camera angle
- For golf, use **side view** (perpendicular to swing plane)
- Front view works but angles are less meaningful

---

## Complete Workflow Example

```bash
# 1. Install
pip install mediapipe

# 2. Get golf videos
# Record yourself or download samples

# 3. Analyze
python analyze_golf_mediapipe.py --video swing1.mp4
python analyze_golf_mediapipe.py --video swing2.mp4
python analyze_golf_mediapipe.py --video swing3.mp4

# 4. Watch analyzed videos
open swing1_analyzed.mp4

# 5. For project: extract metrics, create plots, compare swings
```

---

## You're Ready!

MediaPipe gives you everything needed for a successful project:
- ✅ Accurate pose detection
- ✅ Easy to use
- ✅ Fast processing
- ✅ Extensible for golf analysis

**Next:** Start analyzing golf videos and building your project!

```bash
python analyze_golf_mediapipe.py --video your_first_golf_video.mp4
```

Good luck! 🏌️‍♂️
