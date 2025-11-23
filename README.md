# Golf Pose Estimation with RTMPose

Real-time golf swing analysis using RTMPose for 2D pose estimation.

## Project Overview

This project implements RTMPose (Real-Time Multi-Person Pose Estimation) for golf swing analysis as part of CSE 455 final project at University of Washington.

**Paper**: [RTMPose: Real-Time Multi-Person Pose Estimation based on MMPose](https://arxiv.org/abs/2303.07399)

### Team Members
- Luke Sarausad
- Bassil Rashid

## Features

- **Pose Estimation**: Real-time 2D keypoint detection on golf swing videos
- **SimCC Representation**: Efficient coordinate classification using 1D Gaussian distributions
- **Temporal Smoothing**: One Euro Filter for smooth predictions across video frames
- **Swing Analysis**: Biomechanics calculations (angles, club speed estimates)
- **Visualization**: Skeleton overlay with keypoint confidence

## Project Structure

```
golf_pose_rtm/
├── data/
│   └── coco/              # COCO 2017 dataset
├── models/
│   ├── __init__.py
│   └── rtmpose.py         # RTMPose model (ResNet50 + SimCC head)
├── utils/
│   ├── __init__.py
│   ├── dataset.py         # COCO dataset loader
│   ├── transforms.py      # Data augmentation & SimCC utilities
│   ├── loss.py            # KL divergence loss
│   └── visualization.py   # Drawing and plotting functions
├── config.py              # Configuration parameters
├── train.py               # Training script
├── inference.py           # Video inference script
├── test_components.py     # Unit tests for all components
├── download_coco.sh       # COCO dataset download script
└── requirements.txt       # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

**Requirements:**
- Python 3.8+
- PyTorch 2.0+
- torchvision 0.15+
- OpenCV 4.8+
- NumPy, Matplotlib

### 2. Download COCO Dataset

Use the provided script to download COCO 2017 Keypoint dataset:

```bash
./download_coco.sh
```

This will download:
- Annotations (~241 MB)
- Validation images (~1 GB) - for testing
- Training images (~19 GB) - optional, download when ready to train

**Manual download:**
```bash
cd data/coco

# Annotations
wget http://images.cocodataset.org/annotations/annotations_trainval2017.zip
unzip annotations_trainval2017.zip

# Validation images
wget http://images.cocodataset.org/zips/val2017.zip
unzip val2017.zip

# Training images (optional)
wget http://images.cocodataset.org/zips/train2017.zip
unzip train2017.zip
```

### 3. Run Tests

Verify installation with component tests:

```bash
python test_components.py
```

This tests:
- Data transformations
- SimCC target generation
- Loss functions
- Model architecture
- Training loop integration

## Usage

### Training

**Basic training:**
```bash
python train.py
```

**Custom configuration:**
```bash
python train.py \
  --batch-size 32 \
  --epochs 100 \
  --lr 0.001 \
  --device cuda
```

**Resume from checkpoint:**
```bash
python train.py --resume checkpoints/best_model.pth
```

**Training options:**
- `--batch-size`: Batch size (default: 32)
- `--epochs`: Number of epochs (default: 100)
- `--lr`: Learning rate (default: 0.001)
- `--resume`: Path to checkpoint to resume from
- `--no-pretrained`: Don't use ImageNet pretrained weights
- `--device`: Device to use (cuda/cpu)

**Expected Results:**
- PCK@0.05 > 60% on COCO validation after 50 epochs
- Training on full COCO: ~3 hours per epoch on GPU

### Inference on Videos

**Basic inference:**
```bash
python inference.py \
  --video data/golf/swing.mp4 \
  --checkpoint checkpoints/best_model.pth
```

**Full options:**
```bash
python inference.py \
  --video data/golf/swing.mp4 \
  --output output/swing_analyzed.mp4 \
  --checkpoint checkpoints/best_model.pth \
  --device cuda \
  --conf-threshold 0.3 \
  --no-smoothing  # Disable temporal smoothing
```

**Inference options:**
- `--video`: Input video path (required)
- `--output`: Output video path (default: input_output.mp4)
- `--checkpoint`: Model checkpoint path (required)
- `--device`: Device to use (cuda/cpu)
- `--conf-threshold`: Confidence threshold for visualization (default: 0.3)
- `--no-smoothing`: Disable One Euro Filter smoothing

### Testing Individual Components

**Test model only:**
```bash
python models/rtmpose.py
```

**Test dataset loader:**
```bash
python -c "from utils.dataset import get_val_loader; loader = get_val_loader(batch_size=2); print(next(iter(loader)))"
```

## Implementation Details

### Architecture

**RTMPose Model:**
```
Input Image (3, 256, 192)
    ↓
ResNet50 Backbone (ImageNet pretrained)
    ↓
Global Average Pooling → (2048,)
    ↓
Fully Connected Hidden Layer (512)
    ↓
    ├─→ X Head: FC → (17 × 192) logits
    └─→ Y Head: FC → (17 × 256) logits
```

**SimCC (Simulated Classification Coordinates):**
- Traditional: Predict 2D heatmaps (memory intensive)
- SimCC: Predict 1D distributions for x and y separately
- For each keypoint:
  - X distribution: 192-way classification (which column?)
  - Y distribution: 256-way classification (which row?)
- Target: 1D Gaussian centered at true coordinate
- Loss: KL divergence between predicted and target distributions

**Key Parameters:**
- Input size: 256 × 192 (height × width)
- 17 COCO keypoints: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles
- Gaussian sigma: 6.0 for SimCC targets
- Batch size: 32
- Learning rate: 1e-3 with cosine annealing

### Data Augmentation

- Random horizontal flip (50% probability)
- Resize to 256 × 192
- ImageNet normalization (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

### Loss Function

KL Divergence between predicted and target distributions:

```
Loss = KL(target_x || pred_x) + KL(target_y || pred_y)
```

Weighted by keypoint visibility (ignore occluded/missing keypoints).

### Evaluation Metrics

**PCK (Percentage of Correct Keypoints):**
- Keypoint is "correct" if predicted within threshold distance from ground truth
- Threshold: 5% of bbox diagonal (PCK@0.05)
- Only evaluate visible keypoints

## Configuration

Edit [config.py](config.py) to customize:

```python
# Model
INPUT_SIZE = (256, 192)  # (height, width)
NUM_KEYPOINTS = 17

# Training
BATCH_SIZE = 32
NUM_EPOCHS = 100
LEARNING_RATE = 1e-3

# SimCC
SIMCC_SIGMA = 6.0

# Data augmentation
FLIP_PROB = 0.5
```

## Progress

- [x] Project setup and structure
- [x] Model implementation (ResNet50 + SimCC)
- [x] Dataset loader with COCO support
- [x] Loss function (KL divergence)
- [x] Training pipeline with metrics
- [x] Inference script with video processing
- [x] Temporal smoothing (One Euro Filter)
- [x] Visualization utilities
- [x] Component tests
- [ ] Train on full COCO dataset
- [ ] Golf-specific analysis (swing phases, biomechanics)
- [ ] Results and evaluation
- [ ] Final report

## Development Timeline

**Week 1** (Current):
- [x] Implementation of all core components
- [ ] Testing on small subset
- [ ] Small-scale training (verify loss decreases)

**Week 2**:
- [ ] Full training on COCO dataset
- [ ] Hyperparameter tuning
- [ ] Achieve PCK@0.05 > 60%

**Week 3**:
- [ ] Golf video analysis
- [ ] Swing phase detection
- [ ] Biomechanics calculations

**Week 4**:
- [ ] Experiments and evaluation
- [ ] Final report writing
- [ ] Presentation preparation

## Troubleshooting

**Out of memory:**
- Reduce batch size: `--batch-size 16`
- Use gradient accumulation
- Use CPU: `--device cpu` (slower)

**Loss is NaN:**
- Check learning rate (try 1e-4)
- Verify targets sum to 1
- Enable gradient clipping (already in train.py)

**Slow training:**
- Increase num_workers in config.py
- Use GPU if available
- Use smaller subset for testing

**Dataset not found:**
- Ensure COCO is in `data/coco/`
- Check paths in config.py
- Run `./download_coco.sh`

## References

- [RTMPose Paper (arXiv:2303.07399)](https://arxiv.org/abs/2303.07399)
- [COCO Keypoint Detection](https://cocodataset.org/#keypoints-2017)
- [MMPose Library](https://github.com/open-mmlab/mmpose)
- [One Euro Filter](http://cristal.univ-lille.fr/~casiez/1euro/)

## License

Academic project for CSE 455 - University of Washington

## Contact

For questions or issues, please contact:
- Luke Sarausad
- Bassil Rashid