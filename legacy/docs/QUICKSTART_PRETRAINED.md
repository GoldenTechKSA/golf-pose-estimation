# Quick Start Guide - Using Pretrained Weights

**No COCO dataset needed! Use pretrained model directly.**

This guide gets you analyzing golf swings in **10 minutes** using pretrained RTMPose weights.

## Step 1: Install Dependencies (2 minutes)

```bash
cd /Users/lukesarausad/Desktop/golf_pose_rtm

# Install requirements
pip install -r requirements.txt
```

## Step 2: Download Pretrained Weights (3 minutes)

```bash
# Download pretrained RTMPose model (trained on COCO already!)
python download_pretrained.py --model rtmpose-m
```

This downloads a model that's already trained on 118K images. No training needed!

**Model options:**
- `rtmpose-s`: Small, fast (~50MB)
- `rtmpose-m`: Medium, balanced (~150MB) **← RECOMMENDED**
- `rtmpose-l`: Large, accurate (~300MB)

## Step 3: Get a Golf Video (1 minute)

**Option A: Use your own video**
- Record a golf swing with your phone
- Or download from YouTube

**Option B: Use a sample** (for testing)
```bash
# Create a test video with a person
python -c "
import cv2
import numpy as np

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('test_person.mp4', fourcc, 30, (640, 480))

for i in range(90):  # 3 seconds
    frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)
    out.write(frame)

out.release()
print('Created test_person.mp4')
"
```

## Step 4: Analyze the Video (5 minutes)

```bash
# Analyze your golf swing!
python analyze_golf.py --video your_golf_swing.mp4
```

This will:
- ✓ Detect keypoints (joints) in each frame
- ✓ Draw skeleton overlay
- ✓ Calculate biomechanics (angles, rotation)
- ✓ Save analyzed video

**Output:** `your_golf_swing_analyzed.mp4`

---

## Advanced Usage

### GPU Acceleration (if available)

```bash
python analyze_golf.py \
  --video golf.mp4 \
  --device cuda  # Much faster!
```

### Without Metrics Overlay

```bash
python analyze_golf.py \
  --video golf.mp4 \
  --no-metrics  # Just show skeleton
```

### Using Different Model Sizes

```bash
# Download small model (faster)
python download_pretrained.py --model rtmpose-s

# Use it
python analyze_golf.py \
  --video golf.mp4 \
  --weights pretrained/rtmpose_s_coco.pth
```

---

## What You Get

The analyzed video shows:

1. **Skeleton overlay**: Lines connecting joints
2. **Biomechanics metrics** (overlaid text):
   - Right arm angle
   - Shoulder rotation
   - Hip rotation
   - Right knee flex

All angles in degrees!

---

## Next Steps: Project Extensions

Now that you have basic pose detection working, you can:

### 1. Swing Phase Detection

Detect the phases of a golf swing (address, backswing, downswing, impact, follow-through):

```python
# Add to analyze_golf.py
def detect_swing_phase(keypoints_history):
    # Track wrist position over time
    # Detect peaks/valleys in trajectory
    # Label phases
    pass
```

### 2. Swing Comparison

Compare pro golfer vs amateur:

```bash
python analyze_golf.py --video pro_swing.mp4
python analyze_golf.py --video amateur_swing.mp4

# Then create side-by-side comparison
python compare_swings.py pro_swing_analyzed.mp4 amateur_swing_analyzed.mp4
```

### 3. Biomechanics Dashboard

Extract all metrics to CSV for analysis:

```python
# Save frame-by-frame metrics
import pandas as pd

metrics_df = pd.DataFrame({
    'frame': [...],
    'arm_angle': [...],
    'shoulder_rotation': [...],
    'hip_rotation': [...]
})

metrics_df.to_csv('swing_analysis.csv')
```

### 4. Real-time Analysis

Use webcam for live feedback:

```python
# live_analyze.py
cap = cv2.VideoCapture(0)  # Webcam

while True:
    ret, frame = cap.read()
    keypoints = process_frame(model, frame)
    # Show live skeleton + metrics
```

---

## Troubleshooting

### "Weights not found"

```bash
# Make sure you downloaded them
python download_pretrained.py --model rtmpose-m

# Check they exist
ls pretrained/
```

### "Video not found"

```bash
# Check video path
ls your_golf_swing.mp4

# Use absolute path
python analyze_golf.py --video /full/path/to/video.mp4
```

### Slow processing

```bash
# Use GPU if available
python analyze_golf.py --video golf.mp4 --device cuda

# Or use smaller model
python download_pretrained.py --model rtmpose-s
python analyze_golf.py --video golf.mp4 --weights pretrained/rtmpose_s_coco.pth
```

### Poor keypoint detection

The pretrained model works best when:
- Person is clearly visible
- Good lighting
- Camera is relatively stable
- Person is facing sideways (for golf swing analysis)

If detection is poor, try:
- Better camera angle
- More lighting
- Zoom in on the person

---

## For Your Project Report

Since you're using pretrained weights, focus your report on:

1. **Application to Golf**: How you applied pose estimation to golf analysis
2. **Biomechanics**: What metrics you calculated and why they matter
3. **Swing Analysis**: Phase detection, comparison, insights
4. **Validation**: Compare your metrics to known good swings

You can still mention:
- RTMPose architecture (SimCC innovation)
- Transfer learning (COCO → Golf)
- Why this approach works

---

## Complete Workflow

```bash
# 1. Setup
pip install -r requirements.txt

# 2. Download pretrained model
python download_pretrained.py --model rtmpose-m

# 3. Analyze golf video
python analyze_golf.py --video my_swing.mp4

# 4. View output
open my_swing_analyzed.mp4

# 5. (Optional) Extract metrics for analysis
python extract_metrics.py --video my_swing.mp4 --output metrics.csv
```

---

## Summary

**Time investment:**
- Setup: 5 minutes
- Per video analysis: 1-5 minutes (depending on length)

**No need for:**
- ❌ COCO dataset download (20 GB)
- ❌ Training (hours/days)
- ❌ GPU for training

**What you get:**
- ✅ Professional pose detection
- ✅ Golf-specific biomechanics
- ✅ Visual analysis
- ✅ Extensible for project

Perfect for a 4-week class project!
