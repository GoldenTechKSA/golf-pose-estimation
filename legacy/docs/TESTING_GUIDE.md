# Testing Guide for RTMPose Implementation

This guide walks through all testing steps from basic component tests to full training.

## Phase 1: Component Testing (No Data Required - 5 minutes)

### Test 1: Run Comprehensive Component Tests

This tests all core functionality with synthetic data:

```bash
python test_components.py
```

**What it tests:**
- ✅ Data transformations (resize, flip, normalize)
- ✅ SimCC target generation (1D Gaussian distributions)
- ✅ Loss functions (KL divergence)
- ✅ Model architecture (forward pass, shapes)
- ✅ Integration (mini training loop)

**Expected output:**
```
================================================================================
RTMPose Component Tests
================================================================================
...
Testing Transforms...
✓ All transform tests passed!

Testing Loss Functions...
✓ All loss tests passed!

Testing RTMPose Model...
✓ All model tests passed!

Testing Visualization...
✓ All visualization tests passed!

Testing Integration...
✓ Integration test passed!

ALL TESTS PASSED! ✓
```

**Outputs created:**
- `test_outputs/simcc_target.png` - Visualization of 1D Gaussian
- `test_outputs/keypoints_visualization.png` - Skeleton drawing
- `test_outputs/simcc_predictions.png` - Prediction vs target distributions

### Test 2: Test Model Directly

```bash
python models/rtmpose.py
```

**Expected output:**
```
Testing RTMPose model...
Loading ResNet50 without pretrained weights...

Model created successfully!
Total parameters: 25,XXX,XXX
Trainable parameters: 25,XXX,XXX

Input shape: torch.Size([2, 3, 256, 192])
Output pred_x shape: torch.Size([2, 17, 192])
Output pred_y shape: torch.Size([2, 17, 256])
Predicted keypoints shape: torch.Size([2, 17, 3])

✓ Model test passed!
```

---

## Phase 2: Dataset Testing (Requires COCO Data - 10 minutes)

### Step 1: Download COCO Validation Set

```bash
./download_coco.sh
# Select 'n' for training images (just download validation for testing)
```

This downloads:
- Annotations: 241 MB
- Validation images: 1 GB

### Step 2: Test Dataset Loader

```bash
python -c "
from utils.dataset import get_val_loader
print('Loading validation dataset...')
loader = get_val_loader(batch_size=2)
print(f'Dataset size: {len(loader.dataset)}')
print('Loading one batch...')
batch = next(iter(loader))
print(f'✓ Batch loaded successfully!')
print(f'  Image shape: {batch[\"image\"].shape}')
print(f'  Target_x shape: {batch[\"target_x\"].shape}')
print(f'  Target_y shape: {batch[\"target_y\"].shape}')
print(f'  Keypoints shape: {batch[\"keypoints\"].shape}')
"
```

**Expected output:**
```
Loading validation dataset...
Loading annotations from data/coco/annotations/person_keypoints_val2017.json...
Filtering annotations with valid keypoints...
Loaded XXXX annotations with valid keypoints
Dataset size: XXXX
Loading one batch...
✓ Batch loaded successfully!
  Image shape: torch.Size([2, 3, 256, 192])
  Target_x shape: torch.Size([2, 17, 192])
  Target_y shape: torch.Size([2, 17, 256])
  Keypoints shape: torch.Size([2, 17, 3])
```

### Step 3: Visualize Training Data

```bash
python -c "
from utils.dataset import get_val_loader
from utils.visualization import visualize_batch
loader = get_val_loader(batch_size=4)
batch = next(iter(loader))
visualize_batch(batch, num_samples=4, save_path='test_outputs/batch_viz.png')
print('✓ Saved batch visualization to test_outputs/batch_viz.png')
"
```

This creates a visualization of actual COCO data with keypoints.

---

## Phase 3: Small-Scale Training Test (5-10 minutes)

Test the full training pipeline with minimal epochs:

### Quick Training Test (2 epochs, small batch)

```bash
python train.py \
  --epochs 2 \
  --batch-size 8 \
  --device cpu
```

**What to look for:**
1. ✅ Model loads with pretrained weights
2. ✅ Data loads without errors
3. ✅ Loss decreases over batches
4. ✅ PCK metric is calculated
5. ✅ Checkpoints are saved

**Expected output:**
```
Using device: cpu

Creating data loaders...
Loading annotations from data/coco/annotations/person_keypoints_train2017.json...
Loaded XXXX annotations with valid keypoints
Training samples: XXXX
Validation samples: XXXX

Creating model...
Loading ResNet50 with ImageNet pretrained weights...
Total parameters: 25,XXX,XXX
Trainable parameters: 25,XXX,XXX

Starting training from epoch 0 to 2...
================================================================================

Epoch [1] Batch [50/XXXX] Loss: X.XXXX PCK: X.XXXX ...
...
Epoch [1] Training Summary:
  Loss: X.XXXX
  PCK: X.XXXX
  Time: XXs

Epoch [1] Validation Summary:
  Loss: X.XXXX
  PCK: X.XXXX
  Time: XXs

Saved checkpoint to checkpoints/checkpoint_epoch_1.pth
...
Training completed!
```

**Outputs created:**
- `checkpoints/checkpoint_epoch_1.pth`
- `checkpoints/checkpoint_epoch_2.pth`
- `checkpoints/best_model.pth`
- `visualizations/epoch_1_val.png` (validation predictions)

### Verify Loss Decreases

Check that the loss goes down:

```bash
grep "Training Summary" -A 2 | grep "Loss"
```

You should see the loss decreasing from epoch 1 to epoch 2.

---

## Phase 4: Overfitting Test (Good Diagnostic - 10 minutes)

A healthy implementation should be able to overfit on a tiny dataset:

```bash
# Create a small subset (first 100 samples)
python -c "
import json
with open('data/coco/annotations/person_keypoints_train2017.json', 'r') as f:
    data = json.load(f)
# Keep only first 100 annotations
data['annotations'] = [a for a in data['annotations'] if 'keypoints' in a][:100]
with open('data/coco/annotations/person_keypoints_train2017_tiny.json', 'w') as f:
    json.dump(data, f)
print('Created tiny dataset with 100 samples')
"

# Modify config temporarily
python -c "
# Train on tiny dataset for many epochs
import sys
sys.path.insert(0, '.')
import config
config.COCO_TRAIN_ANN = 'data/coco/annotations/person_keypoints_train2017_tiny.json'

from train import main
import sys
sys.argv = ['train.py', '--epochs', '20', '--batch-size', '16']
main()
"
```

**Expected behavior:**
- Training loss should drop to near 0
- Training PCK should reach >90%
- This proves the model can learn!

---

## Phase 5: GPU Training Test (If Available)

If you have a GPU:

```bash
# Check GPU availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

# Run training on GPU
python train.py \
  --epochs 5 \
  --batch-size 32 \
  --device cuda
```

**Speed comparison:**
- CPU: ~10-15 minutes per epoch
- GPU: ~2-3 minutes per epoch (on modern GPU)

---

## Phase 6: Inference Testing (Requires Trained Model)

### Test with Dummy Video

First, create a test video or use a golf swing video:

```bash
# Option 1: Create dummy video with OpenCV
python -c "
import cv2
import numpy as np

# Create a dummy video (person moving)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('test_video.mp4', fourcc, 30, (640, 480))

for i in range(90):  # 3 seconds at 30fps
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    # Draw a simple stick figure that moves
    cv2.circle(frame, (320 + i*2, 240), 20, (255, 255, 255), -1)  # head
    out.write(frame)

out.release()
print('Created test_video.mp4')
"

# Run inference
python inference.py \
  --video test_video.mp4 \
  --checkpoint checkpoints/best_model.pth \
  --output test_output.mp4
```

### Test with Real Golf Video

```bash
# Download a golf swing video (or use your own)
# Example: youtube-dl or similar

python inference.py \
  --video golf_swing.mp4 \
  --checkpoint checkpoints/best_model.pth \
  --output golf_swing_analyzed.mp4 \
  --conf-threshold 0.3
```

**What to verify:**
- ✅ Video processes without errors
- ✅ Output video has skeleton overlay
- ✅ Keypoints track the person smoothly
- ✅ FPS is displayed during processing

---

## Phase 7: Full Training (Week 2)

Once all tests pass, run full training:

```bash
# Download full training set (19 GB)
cd data/coco
wget http://images.cocodataset.org/zips/train2017.zip
unzip train2017.zip
cd ../..

# Full training
python train.py \
  --epochs 100 \
  --batch-size 32 \
  --device cuda \
  --lr 0.001
```

**Monitor training:**
```bash
# In another terminal, watch the logs
tail -f training.log  # if you redirect output

# Or check checkpoints
ls -lh checkpoints/
```

**Expected timeline:**
- Epoch 0-10: PCK ~30-40%
- Epoch 10-25: PCK ~40-50%
- Epoch 25-50: PCK ~50-60%
- Epoch 50-100: PCK ~60-70%

---

## Troubleshooting Tests

### Test fails with "FileNotFoundError"

```bash
# Check COCO dataset is downloaded
ls data/coco/annotations/
ls data/coco/val2017/ | head

# Verify paths in config.py
cat config.py | grep COCO
```

### Test fails with "CUDA out of memory"

```bash
# Reduce batch size
python train.py --batch-size 16  # or 8, or 4

# Or use CPU
python train.py --device cpu
```

### Loss is NaN

```bash
# Check SimCC targets are valid
python -c "
from utils.dataset import get_val_loader
loader = get_val_loader(batch_size=1)
batch = next(iter(loader))
import torch
print('Target_x sum:', batch['target_x'][0, 0].sum())  # Should be ~1.0
print('Target_x max:', batch['target_x'][0, 0].max())
print('Target_x contains NaN:', torch.isnan(batch['target_x']).any())
"

# Try lower learning rate
python train.py --lr 0.0001
```

### Model doesn't learn (loss doesn't decrease)

```bash
# Verify model can overfit on tiny dataset (see Phase 4)
# Check gradients are flowing
python -c "
import torch
from models import create_rtmpose
model = create_rtmpose(pretrained=False)
x = torch.randn(2, 3, 256, 192)
pred_x, pred_y = model(x)
loss = pred_x.sum() + pred_y.sum()
loss.backward()
# Check some gradients
for name, param in model.named_parameters():
    if param.grad is not None:
        print(f'{name}: grad norm = {param.grad.norm().item():.4f}')
        break
"
```

---

## Test Checklist

Before full training, verify:

- [ ] `python test_components.py` passes
- [ ] `python models/rtmpose.py` runs without errors
- [ ] COCO validation dataset loads successfully
- [ ] Can train for 2 epochs without errors
- [ ] Loss decreases over epochs
- [ ] Checkpoints are saved
- [ ] Visualizations are created
- [ ] Can load checkpoint and resume
- [ ] Inference runs on test video

Once all checked, ready for full training! 🚀

---

## Quick Test Commands Summary

```bash
# 1. Component tests (no data needed)
python test_components.py

# 2. Model test
python models/rtmpose.py

# 3. Download data
./download_coco.sh

# 4. Dataset test
python -c "from utils.dataset import get_val_loader; next(iter(get_val_loader(batch_size=2)))"

# 5. Quick training test
python train.py --epochs 2 --batch-size 8

# 6. Check GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 7. Full training
python train.py --epochs 100 --batch-size 32 --device cuda
```
