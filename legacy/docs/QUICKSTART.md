# RTMPose Golf Swing Analysis - Quick Start Guide

This guide will get you up and running with the RTMPose implementation in 10 minutes.

## Prerequisites

- Python 3.8 or higher
- 4GB+ RAM
- Optional: NVIDIA GPU with CUDA for faster training

## Step 1: Installation (2 minutes)

```bash
# Clone or navigate to the project directory
cd golf_pose_rtm

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Verify Installation (1 minute)

Test that everything is working:

```bash
python test_components.py
```

You should see:
```
================================================================================
RTMPose Component Tests
================================================================================
...
ALL TESTS PASSED! ✓
```

Test outputs will be saved to `test_outputs/` directory.

## Step 3: Download Data (5-30 minutes depending on connection)

**Option A: Quick Start (1 GB - Validation only)**

```bash
./download_coco.sh
# When prompted for training images, select 'n' (no)
```

**Option B: Full Dataset (20 GB - For full training)**

```bash
./download_coco.sh
# When prompted for training images, select 'y' (yes)
```

After download, your data structure should look like:
```
data/coco/
├── annotations/
│   ├── person_keypoints_train2017.json
│   └── person_keypoints_val2017.json
├── val2017/          # 5K images
└── train2017/        # 118K images (optional for now)
```

## Step 4: Test Data Loading (1 minute)

Verify the dataset is loaded correctly:

```bash
python -c "
from utils.dataset import get_val_loader
loader = get_val_loader(batch_size=2)
batch = next(iter(loader))
print('Batch loaded successfully!')
print(f\"Image shape: {batch['image'].shape}\")
print(f\"Target_x shape: {batch['target_x'].shape}\")
print(f\"Target_y shape: {batch['target_y'].shape}\")
"
```

Expected output:
```
Loading annotations from data/coco/annotations/person_keypoints_val2017.json...
Filtering annotations with valid keypoints...
Loaded XXXX annotations with valid keypoints
Batch loaded successfully!
Image shape: torch.Size([2, 3, 256, 192])
Target_x shape: torch.Size([2, 17, 192])
Target_y shape: torch.Size([2, 17, 256])
```

## Step 5: Small-Scale Training Test (5 minutes)

Test training on a small subset to verify everything works:

```bash
# Train for just 2 epochs to verify the pipeline works
python train.py --epochs 2 --batch-size 8
```

You should see:
- Model loading with ResNet50
- Training progress with decreasing loss
- Validation metrics (PCK)
- Checkpoints saved to `checkpoints/`

If this completes successfully, you're ready for full training!

## Next Steps

### Full Training

Once you've verified the quick test works:

```bash
# Full training with default settings
python train.py --epochs 100 --batch-size 32 --device cuda

# Monitor with tensorboard (if installed)
tensorboard --logdir runs/
```

### Inference on Videos

After training (or using a pretrained checkpoint):

```bash
# Download a golf swing video and run inference
python inference.py \
  --video path/to/golf_swing.mp4 \
  --checkpoint checkpoints/best_model.pth \
  --output output/analyzed_swing.mp4
```

## Common Issues

### Issue: "CUDA out of memory"

**Solution:** Reduce batch size
```bash
python train.py --batch-size 16  # or even 8
```

### Issue: "FileNotFoundError: Image not found"

**Solution:** Verify COCO dataset paths
```bash
ls data/coco/val2017/ | head -5  # Should show image files
ls data/coco/annotations/  # Should show JSON files
```

### Issue: "ModuleNotFoundError"

**Solution:** Ensure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Slow training on CPU

**Solution:** This is expected. Options:
1. Use GPU if available: `--device cuda`
2. Reduce batch size: `--batch-size 8`
3. Train for fewer epochs initially: `--epochs 10`
4. Use Google Colab with free GPU

## File Organization

After setup, your directory should look like:

```
golf_pose_rtm/
├── checkpoints/              # Created during training
│   ├── best_model.pth
│   └── checkpoint_epoch_*.pth
├── data/
│   └── coco/                # Downloaded dataset
├── test_outputs/            # Created by test script
│   ├── simcc_target.png
│   └── keypoints_visualization.png
├── visualizations/          # Created during training
│   └── epoch_*_val.png
├── models/
├── utils/
└── [all .py files]
```

## Expected Performance

With default settings on COCO validation set:

| Epochs | Expected PCK@0.05 | Training Time (GPU) |
|--------|-------------------|---------------------|
| 10     | ~40%              | ~30 minutes         |
| 25     | ~50%              | ~1.5 hours          |
| 50     | ~60%              | ~3 hours            |
| 100    | ~65%+             | ~6 hours            |

## Quick Reference Commands

```bash
# Test installation
python test_components.py

# Test model only
python models/rtmpose.py

# Quick training test
python train.py --epochs 2 --batch-size 8

# Full training
python train.py --epochs 100

# Resume training
python train.py --resume checkpoints/best_model.pth

# Inference
python inference.py --video VIDEO.mp4 --checkpoint checkpoints/best_model.pth

# Check configuration
cat config.py
```

## Getting Help

1. Check the main [README.md](README.md) for detailed documentation
2. Review error messages carefully - they often indicate the issue
3. Verify all steps in this guide were completed
4. Check the troubleshooting section in README.md

## What's Next?

After completing the quick start:

1. **Week 1**: Complete small-scale training and verify model works
2. **Week 2**: Full training on COCO dataset
3. **Week 3**: Apply to golf videos and implement swing analysis
4. **Week 4**: Experiments, evaluation, and final report

Happy coding!
