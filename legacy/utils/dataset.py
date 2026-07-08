"""
COCO Keypoint Dataset Loader for RTMPose
Loads COCO person keypoint annotations and generates SimCC targets
"""
import os
import json
import numpy as np
import cv2
import torch
from torch.utils.data import Dataset
from typing import Dict, List, Optional, Tuple
import config
from .transforms import (
    resize_with_keypoints,
    random_horizontal_flip,
    normalize_image,
    keypoints_to_simcc_targets
)


class COCOKeypointDataset(Dataset):
    """
    COCO Dataset for pose estimation with SimCC targets

    Args:
        ann_file: path to COCO annotation JSON file
        img_dir: path to COCO image directory
        transform: whether to apply data augmentation (default True for training)
        input_size: tuple of (height, width) for input images
    """

    def __init__(
        self,
        ann_file: str,
        img_dir: str,
        transform: bool = True,
        input_size: Tuple[int, int] = config.INPUT_SIZE
    ):
        self.ann_file = ann_file
        self.img_dir = img_dir
        self.transform = transform
        self.input_size = input_size

        # Load COCO annotations
        print(f"Loading annotations from {ann_file}...")
        with open(ann_file, 'r') as f:
            self.coco_data = json.load(f)

        # Build image id to filename mapping
        self.img_id_to_filename = {
            img['id']: img['file_name']
            for img in self.coco_data['images']
        }

        # Filter annotations to only include those with keypoints
        print("Filtering annotations with valid keypoints...")
        self.annotations = []
        for ann in self.coco_data['annotations']:
            # Check if annotation has keypoints
            if 'keypoints' in ann and ann['keypoints'] is not None:
                keypoints = np.array(ann['keypoints']).reshape(-1, 3)
                # Keep only if at least one keypoint is visible
                if np.any(keypoints[:, 2] == config.VISIBILITY_VISIBLE):
                    self.annotations.append(ann)

        print(f"Loaded {len(self.annotations)} annotations with valid keypoints")

    def __len__(self) -> int:
        return len(self.annotations)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Get a single training sample

        Returns:
            dict containing:
                - image: tensor of shape (3, H, W)
                - target_x: tensor of shape (num_keypoints, W)
                - target_y: tensor of shape (num_keypoints, H)
                - keypoints: original keypoints (num_keypoints, 3)
                - image_id: int
        """
        ann = self.annotations[idx]

        # Get image path and load image
        image_id = ann['image_id']
        filename = self.img_id_to_filename[image_id]
        img_path = os.path.join(self.img_dir, filename)

        # Load image
        image = cv2.imread(img_path)
        if image is None:
            raise FileNotFoundError(f"Image not found: {img_path}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB

        # Parse keypoints [x1, y1, v1, x2, y2, v2, ...] -> (17, 3)
        keypoints = np.array(ann['keypoints'], dtype=np.float32).reshape(config.NUM_KEYPOINTS, 3)

        # Resize image and keypoints
        image, keypoints = resize_with_keypoints(image, keypoints, self.input_size)

        # Apply data augmentation if enabled
        if self.transform:
            image, keypoints = random_horizontal_flip(
                image, keypoints, flip_prob=config.FLIP_PROB
            )

        # Generate SimCC targets
        target_x, target_y = keypoints_to_simcc_targets(
            keypoints,
            self.input_size,
            sigma=config.SIMCC_SIGMA
        )

        # Normalize image and convert to tensor
        image_tensor = normalize_image(image)

        # Convert targets to tensors
        target_x_tensor = torch.from_numpy(target_x)
        target_y_tensor = torch.from_numpy(target_y)
        keypoints_tensor = torch.from_numpy(keypoints)

        return {
            'image': image_tensor,
            'target_x': target_x_tensor,
            'target_y': target_y_tensor,
            'keypoints': keypoints_tensor,
            'image_id': image_id,
        }


def get_train_loader(batch_size: int = config.BATCH_SIZE) -> torch.utils.data.DataLoader:
    """
    Create training data loader

    Args:
        batch_size: batch size for training

    Returns:
        DataLoader for training set
    """
    train_dataset = COCOKeypointDataset(
        ann_file=config.COCO_TRAIN_ANN,
        img_dir=config.COCO_TRAIN_IMG,
        transform=True,
        input_size=config.INPUT_SIZE
    )

    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=config.NUM_WORKERS,
        pin_memory=config.PIN_MEMORY,
        drop_last=True  # Drop last incomplete batch
    )

    return train_loader


def get_val_loader(batch_size: int = config.BATCH_SIZE) -> torch.utils.data.DataLoader:
    """
    Create validation data loader

    Args:
        batch_size: batch size for validation

    Returns:
        DataLoader for validation set
    """
    val_dataset = COCOKeypointDataset(
        ann_file=config.COCO_VAL_ANN,
        img_dir=config.COCO_VAL_IMG,
        transform=False,  # No augmentation for validation
        input_size=config.INPUT_SIZE
    )

    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=config.NUM_WORKERS,
        pin_memory=config.PIN_MEMORY,
        drop_last=False
    )

    return val_loader


def collate_fn(batch: List[Dict]) -> Dict[str, torch.Tensor]:
    """
    Custom collate function for batching samples
    Handles variable number of keypoints if needed

    Args:
        batch: list of sample dicts

    Returns:
        batched dict
    """
    # Stack all tensors
    images = torch.stack([item['image'] for item in batch])
    target_x = torch.stack([item['target_x'] for item in batch])
    target_y = torch.stack([item['target_y'] for item in batch])
    keypoints = torch.stack([item['keypoints'] for item in batch])
    image_ids = torch.tensor([item['image_id'] for item in batch])

    return {
        'image': images,
        'target_x': target_x,
        'target_y': target_y,
        'keypoints': keypoints,
        'image_id': image_ids,
    }
