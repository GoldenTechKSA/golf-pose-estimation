"""
Visualization utilities for RTMPose
Functions to draw keypoints, skeleton, and analyze predictions
"""
import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch
from typing import List, Tuple, Optional
import config


def draw_keypoints(
    image: np.ndarray,
    keypoints: np.ndarray,
    skeleton_pairs: Optional[List[Tuple[int, int]]] = None,
    confidence_threshold: float = 0.3,
    keypoint_color: Tuple[int, int, int] = (0, 255, 0),
    skeleton_color: Tuple[int, int, int] = (255, 0, 0),
    radius: int = 3,
    thickness: int = 2
) -> np.ndarray:
    """
    Draw keypoints and skeleton on image

    Args:
        image: numpy array of shape (H, W, 3) in RGB format
        keypoints: numpy array of shape (num_keypoints, 3) - [x, y, confidence/visibility]
        skeleton_pairs: list of (idx1, idx2) tuples defining connections
        confidence_threshold: minimum confidence to draw keypoint
        keypoint_color: RGB color for keypoints
        skeleton_color: RGB color for skeleton lines
        radius: radius of keypoint circles
        thickness: thickness of skeleton lines

    Returns:
        annotated_image: numpy array of shape (H, W, 3) with drawn keypoints
    """
    # Make a copy to avoid modifying original
    img = image.copy()

    # Use default skeleton if not provided
    if skeleton_pairs is None:
        skeleton_pairs = config.SKELETON_PAIRS

    # Draw skeleton connections first (so they appear behind keypoints)
    for idx1, idx2 in skeleton_pairs:
        if idx1 >= len(keypoints) or idx2 >= len(keypoints):
            continue

        x1, y1, conf1 = keypoints[idx1]
        x2, y2, conf2 = keypoints[idx2]

        # Only draw if both keypoints are visible
        if conf1 >= confidence_threshold and conf2 >= confidence_threshold:
            pt1 = (int(x1), int(y1))
            pt2 = (int(x2), int(y2))
            cv2.line(img, pt1, pt2, skeleton_color, thickness)

    # Draw keypoints
    for i, (x, y, conf) in enumerate(keypoints):
        if conf >= confidence_threshold:
            center = (int(x), int(y))
            cv2.circle(img, center, radius, keypoint_color, -1)  # -1 fills the circle

            # Optionally add keypoint index as text
            # cv2.putText(img, str(i), center, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    return img


def draw_keypoints_with_labels(
    image: np.ndarray,
    keypoints: np.ndarray,
    confidence_threshold: float = 0.3
) -> np.ndarray:
    """
    Draw keypoints with name labels

    Args:
        image: numpy array of shape (H, W, 3) in RGB format
        keypoints: numpy array of shape (num_keypoints, 3) - [x, y, confidence]
        confidence_threshold: minimum confidence to draw keypoint

    Returns:
        annotated_image: numpy array with keypoints and labels
    """
    img = draw_keypoints(image, keypoints, confidence_threshold=confidence_threshold)

    # Add labels
    for i, (x, y, conf) in enumerate(keypoints):
        if conf >= confidence_threshold and i < len(config.KEYPOINT_NAMES):
            label = config.KEYPOINT_NAMES[i]
            pos = (int(x) + 5, int(y) - 5)
            cv2.putText(img, label, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    return img


def visualize_simcc_predictions(
    pred_x: np.ndarray,
    pred_y: np.ndarray,
    target_x: Optional[np.ndarray] = None,
    target_y: Optional[np.ndarray] = None,
    keypoint_indices: Optional[List[int]] = None,
    save_path: Optional[str] = None
):
    """
    Visualize SimCC predictions vs targets as line plots

    Args:
        pred_x: numpy array of shape (num_keypoints, W) - predicted x distributions
        pred_y: numpy array of shape (num_keypoints, H) - predicted y distributions
        target_x: numpy array of shape (num_keypoints, W) - target x distributions (optional)
        target_y: numpy array of shape (num_keypoints, H) - target y distributions (optional)
        keypoint_indices: list of keypoint indices to visualize (if None, show first 4)
        save_path: path to save figure (if None, display only)
    """
    if keypoint_indices is None:
        # Default: show first 4 keypoints
        keypoint_indices = [0, 5, 6, 9]  # nose, left_shoulder, right_shoulder, left_wrist

    num_keypoints = len(keypoint_indices)
    fig, axes = plt.subplots(num_keypoints, 2, figsize=(12, 3 * num_keypoints))

    if num_keypoints == 1:
        axes = axes.reshape(1, -1)

    for i, kpt_idx in enumerate(keypoint_indices):
        kpt_name = config.KEYPOINT_NAMES[kpt_idx] if kpt_idx < len(config.KEYPOINT_NAMES) else f"Keypoint {kpt_idx}"

        # Plot x distribution
        axes[i, 0].plot(pred_x[kpt_idx], label='Prediction', linewidth=2)
        if target_x is not None:
            axes[i, 0].plot(target_x[kpt_idx], label='Target', linewidth=2, linestyle='--')
        axes[i, 0].set_title(f'{kpt_name} - X Distribution')
        axes[i, 0].set_xlabel('X Position')
        axes[i, 0].set_ylabel('Probability')
        axes[i, 0].legend()
        axes[i, 0].grid(True, alpha=0.3)

        # Plot y distribution
        axes[i, 1].plot(pred_y[kpt_idx], label='Prediction', linewidth=2)
        if target_y is not None:
            axes[i, 1].plot(target_y[kpt_idx], label='Target', linewidth=2, linestyle='--')
        axes[i, 1].set_title(f'{kpt_name} - Y Distribution')
        axes[i, 1].set_xlabel('Y Position')
        axes[i, 1].set_ylabel('Probability')
        axes[i, 1].legend()
        axes[i, 1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to {save_path}")
    else:
        plt.show()

    plt.close()


def save_prediction_grid(
    images: torch.Tensor,
    predictions: Tuple[torch.Tensor, torch.Tensor],
    targets: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    save_path: str = 'predictions.png',
    num_samples: int = 4,
    denormalize: bool = True
):
    """
    Create a grid of images with predicted and ground truth keypoints

    Args:
        images: tensor of shape (batch, 3, H, W) - input images
        predictions: tuple of (pred_x, pred_y) tensors
        targets: tuple of (target_x, target_y) tensors (optional)
        save_path: path to save the grid image
        num_samples: number of samples to include in grid
        denormalize: whether to denormalize images from ImageNet stats
    """
    from .transforms import denormalize_image, simcc_to_keypoints

    pred_x, pred_y = predictions
    batch_size = min(images.shape[0], num_samples)

    # Convert predictions to keypoints
    pred_x_np = torch.softmax(pred_x, dim=-1).cpu().numpy()
    pred_y_np = torch.softmax(pred_y, dim=-1).cpu().numpy()

    # Create figure
    if targets is not None:
        target_x, target_y = targets
        fig, axes = plt.subplots(batch_size, 3, figsize=(15, 5 * batch_size))
        if batch_size == 1:
            axes = axes.reshape(1, -1)
    else:
        fig, axes = plt.subplots(batch_size, 2, figsize=(10, 5 * batch_size))
        if batch_size == 1:
            axes = axes.reshape(1, -1)

    for i in range(batch_size):
        # Get image
        img = images[i]
        if denormalize:
            img_np = denormalize_image(img)
        else:
            img_np = (img.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

        # Convert predictions to keypoints
        pred_kpts = simcc_to_keypoints(pred_x_np[i], pred_y_np[i])

        # Draw predictions
        img_with_pred = draw_keypoints(img_np, pred_kpts)

        # Show original image
        axes[i, 0].imshow(img_np)
        axes[i, 0].set_title('Original Image')
        axes[i, 0].axis('off')

        # Show predictions
        axes[i, 1].imshow(img_with_pred)
        axes[i, 1].set_title('Predictions')
        axes[i, 1].axis('off')

        # Show targets if available
        if targets is not None:
            target_x_np = target_x[i].cpu().numpy()
            target_y_np = target_y[i].cpu().numpy()
            target_kpts = simcc_to_keypoints(target_x_np, target_y_np)
            img_with_target = draw_keypoints(img_np, target_kpts)
            axes[i, 2].imshow(img_with_target)
            axes[i, 2].set_title('Ground Truth')
            axes[i, 2].axis('off')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved prediction grid to {save_path}")
    plt.close()


def visualize_batch(
    batch: dict,
    num_samples: int = 4,
    save_path: Optional[str] = None
):
    """
    Visualize a batch of training data

    Args:
        batch: batch dict from dataloader
        num_samples: number of samples to show
        save_path: path to save visualization
    """
    from .transforms import denormalize_image, simcc_to_keypoints

    images = batch['image']
    target_x = batch['target_x']
    target_y = batch['target_y']

    batch_size = min(images.shape[0], num_samples)
    fig, axes = plt.subplots(batch_size, 1, figsize=(8, 6 * batch_size))

    if batch_size == 1:
        axes = [axes]

    for i in range(batch_size):
        # Denormalize image
        img = denormalize_image(images[i])

        # Convert SimCC targets to keypoints
        target_x_np = target_x[i].cpu().numpy()
        target_y_np = target_y[i].cpu().numpy()
        keypoints = simcc_to_keypoints(target_x_np, target_y_np)

        # Draw keypoints
        img_with_kpts = draw_keypoints(img, keypoints)

        axes[i].imshow(img_with_kpts)
        axes[i].set_title(f'Sample {i} - Image ID: {batch["image_id"][i].item()}')
        axes[i].axis('off')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved batch visualization to {save_path}")
    else:
        plt.show()

    plt.close()
