"""
Configuration file for RTMPose Golf Swing Analysis
"""
import torch

# Dataset paths
COCO_ROOT = 'data/coco'
COCO_TRAIN_ANN = 'data/coco/annotations/person_keypoints_train2017.json'
COCO_VAL_ANN = 'data/coco/annotations/person_keypoints_val2017.json'
COCO_TRAIN_IMG = 'data/coco/train2017'
COCO_VAL_IMG = 'data/coco/val2017'

# Model configuration
NUM_KEYPOINTS = 17  # COCO has 17 keypoints
INPUT_SIZE = (256, 192)  # (height, width)
INPUT_HEIGHT = 256
INPUT_WIDTH = 192

# SimCC configuration
SIMCC_SIGMA = 6.0  # Standard deviation for Gaussian smoothing
SIMCC_NORMALIZE = True  # Normalize distributions to sum to 1

# Training configuration
BATCH_SIZE = 32
NUM_EPOCHS = 100
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
LR_MIN = 1e-6  # Minimum learning rate for cosine annealing

# Optimizer
OPTIMIZER = 'Adam'
MOMENTUM = 0.9  # For SGD if used

# Data augmentation
FLIP_PROB = 0.5  # Probability of horizontal flip
RANDOM_ROTATION = 30  # Maximum rotation in degrees
RANDOM_SCALE = 0.25  # Scale factor range [1-scale, 1+scale]

# ImageNet normalization (standard for pretrained models)
IMG_MEAN = [0.485, 0.456, 0.406]
IMG_STD = [0.229, 0.224, 0.225]

# Device configuration
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
NUM_WORKERS = 4  # For DataLoader
PIN_MEMORY = True

# Checkpoint configuration
CHECKPOINT_DIR = 'checkpoints'
SAVE_FREQ = 5  # Save checkpoint every N epochs
RESUME_CHECKPOINT = None  # Path to checkpoint to resume from

# Logging
LOG_INTERVAL = 50  # Log every N batches
USE_TENSORBOARD = False

# Evaluation metrics
PCK_THRESHOLD = 0.05  # Percentage of bbox diagonal for PCK metric

# COCO keypoint indices and names
KEYPOINT_NAMES = [
    'nose',           # 0
    'left_eye',       # 1
    'right_eye',      # 2
    'left_ear',       # 3
    'right_ear',      # 4
    'left_shoulder',  # 5
    'right_shoulder', # 6
    'left_elbow',     # 7
    'right_elbow',    # 8
    'left_wrist',     # 9
    'right_wrist',    # 10
    'left_hip',       # 11
    'right_hip',      # 12
    'left_knee',      # 13
    'right_knee',     # 14
    'left_ankle',     # 15
    'right_ankle',    # 16
]

# Skeleton connections for visualization
SKELETON_PAIRS = [
    (0, 1), (0, 2),      # nose to eyes
    (1, 3), (2, 4),      # eyes to ears
    (0, 5), (0, 6),      # nose to shoulders
    (5, 7), (7, 9),      # left arm
    (6, 8), (8, 10),     # right arm
    (5, 11), (6, 12),    # shoulders to hips
    (11, 13), (13, 15),  # left leg
    (12, 14), (14, 16),  # right leg
    (5, 6), (11, 12),    # shoulder line, hip line
]

# Left-right keypoint pairs for horizontal flipping
FLIP_PAIRS = [
    (1, 2),   # left_eye <-> right_eye
    (3, 4),   # left_ear <-> right_ear
    (5, 6),   # left_shoulder <-> right_shoulder
    (7, 8),   # left_elbow <-> right_elbow
    (9, 10),  # left_wrist <-> right_wrist
    (11, 12), # left_hip <-> right_hip
    (13, 14), # left_knee <-> right_knee
    (15, 16), # left_ankle <-> right_ankle
]

# Visibility flags in COCO
# 0: not labeled
# 1: labeled but not visible (occluded)
# 2: labeled and visible
VISIBILITY_NOT_LABELED = 0
VISIBILITY_OCCLUDED = 1
VISIBILITY_VISIBLE = 2
