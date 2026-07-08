"""
Data transformation functions for RTMPose
Includes resizing, flipping, normalization, and SimCC target generation
"""
import numpy as np
import torch
import cv2
from typing import Tuple, Optional
import config


def resize_with_keypoints(
    image: np.ndarray,
    keypoints: np.ndarray,
    target_size: Tuple[int, int]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resize image and scale keypoint coordinates accordingly

    Args:
        image: numpy array of shape (H, W, 3)
        keypoints: numpy array of shape (num_keypoints, 3) - [x, y, visibility]
        target_size: tuple of (height, width)

    Returns:
        resized_image: numpy array of shape (target_height, target_width, 3)
        scaled_keypoints: numpy array of shape (num_keypoints, 3)
    """
    original_height, original_width = image.shape[:2]
    target_height, target_width = target_size

    # Resize image
    resized_image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

    # Calculate scaling factors
    scale_x = target_width / original_width
    scale_y = target_height / original_height

    # Scale keypoint coordinates
    scaled_keypoints = keypoints.copy()
    scaled_keypoints[:, 0] *= scale_x  # x coordinates
    scaled_keypoints[:, 1] *= scale_y  # y coordinates

    # Mark keypoints outside bounds as not visible
    out_of_bounds = (
        (scaled_keypoints[:, 0] < 0) |
        (scaled_keypoints[:, 0] >= target_width) |
        (scaled_keypoints[:, 1] < 0) |
        (scaled_keypoints[:, 1] >= target_height)
    )
    scaled_keypoints[out_of_bounds, 2] = config.VISIBILITY_NOT_LABELED

    return resized_image, scaled_keypoints


def random_horizontal_flip(
    image: np.ndarray,
    keypoints: np.ndarray,
    flip_prob: float = 0.5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Randomly flip image horizontally and adjust keypoint coordinates
    Also swaps left/right keypoints

    Args:
        image: numpy array of shape (H, W, 3)
        keypoints: numpy array of shape (num_keypoints, 3) - [x, y, visibility]
        flip_prob: probability of flipping

    Returns:
        flipped_image: numpy array of shape (H, W, 3)
        flipped_keypoints: numpy array of shape (num_keypoints, 3)
    """
    if np.random.random() > flip_prob:
        return image, keypoints

    # Flip image
    flipped_image = cv2.flip(image, 1)  # 1 for horizontal flip

    # Flip keypoint x-coordinates
    width = image.shape[1]
    flipped_keypoints = keypoints.copy()
    flipped_keypoints[:, 0] = width - 1 - keypoints[:, 0]

    # Swap left/right keypoints
    for left_idx, right_idx in config.FLIP_PAIRS:
        flipped_keypoints[[left_idx, right_idx]] = flipped_keypoints[[right_idx, left_idx]]

    return flipped_image, flipped_keypoints


def normalize_image(image: np.ndarray) -> torch.Tensor:
    """
    Normalize image using ImageNet statistics and convert to tensor

    Args:
        image: numpy array of shape (H, W, 3) in range [0, 255]

    Returns:
        normalized: torch tensor of shape (3, H, W) in range approximately [-2, 2]
    """
    # Convert to float and normalize to [0, 1]
    image = image.astype(np.float32) / 255.0

    # Apply ImageNet normalization
    mean = np.array(config.IMG_MEAN, dtype=np.float32).reshape(1, 1, 3)
    std = np.array(config.IMG_STD, dtype=np.float32).reshape(1, 1, 3)
    image = (image - mean) / std

    # Convert to tensor and change to (C, H, W)
    image_tensor = torch.from_numpy(image).permute(2, 0, 1)

    return image_tensor


def generate_simcc_target(
    coord: float,
    coord_dim: int,
    sigma: float = 6.0
) -> np.ndarray:
    """
    Generate 1D Gaussian distribution for a single coordinate (SimCC representation)

    Args:
        coord: float, target coordinate (e.g., 96.5 for x-coordinate)
        coord_dim: int, dimension of coordinate space (W for x, H for y)
        sigma: float, standard deviation for Gaussian

    Returns:
        target: numpy array of shape (coord_dim,) with Gaussian distribution
    """
    # Create array of positions [0, 1, 2, ..., coord_dim-1]
    positions = np.arange(coord_dim, dtype=np.float32)

    # Calculate Gaussian: exp(-(i - coord)^2 / (2 * sigma^2))
    target = np.exp(-((positions - coord) ** 2) / (2 * sigma ** 2))

    # Normalize to sum to 1 (create probability distribution)
    if config.SIMCC_NORMALIZE:
        target_sum = target.sum()
        if target_sum > 0:
            target = target / target_sum

    return target


def keypoints_to_simcc_targets(
    keypoints: np.ndarray,
    input_size: Tuple[int, int],
    sigma: float = 6.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert keypoints to SimCC target distributions

    Args:
        keypoints: numpy array of shape (num_keypoints, 3) - [x, y, visibility]
        input_size: tuple of (height, width)
        sigma: float, standard deviation for Gaussian

    Returns:
        target_x: numpy array of shape (num_keypoints, width)
        target_y: numpy array of shape (num_keypoints, height)
    """
    num_keypoints = keypoints.shape[0]
    height, width = input_size

    target_x = np.zeros((num_keypoints, width), dtype=np.float32)
    target_y = np.zeros((num_keypoints, height), dtype=np.float32)

    for i in range(num_keypoints):
        x, y, visibility = keypoints[i]

        # Only generate targets for visible keypoints
        if visibility == config.VISIBILITY_VISIBLE:
            # Ensure coordinates are within bounds
            if 0 <= x < width and 0 <= y < height:
                target_x[i] = generate_simcc_target(x, width, sigma)
                target_y[i] = generate_simcc_target(y, height, sigma)
        # For invisible/occluded keypoints, leave as zeros

    return target_x, target_y


def denormalize_image(tensor: torch.Tensor) -> np.ndarray:
    """
    Denormalize image tensor back to [0, 255] range for visualization

    Args:
        tensor: torch tensor of shape (3, H, W) normalized with ImageNet stats

    Returns:
        image: numpy array of shape (H, W, 3) in range [0, 255]
    """
    # Convert to numpy and change to (H, W, C)
    image = tensor.permute(1, 2, 0).cpu().numpy()

    # Denormalize
    mean = np.array(config.IMG_MEAN, dtype=np.float32).reshape(1, 1, 3)
    std = np.array(config.IMG_STD, dtype=np.float32).reshape(1, 1, 3)
    image = image * std + mean

    # Convert to [0, 255]
    image = np.clip(image * 255.0, 0, 255).astype(np.uint8)

    return image


def simcc_to_keypoints(
    pred_x: np.ndarray,
    pred_y: np.ndarray,
    threshold: float = 0.1
) -> np.ndarray:
    """
    Convert SimCC predictions back to keypoint coordinates

    Args:
        pred_x: numpy array of shape (num_keypoints, width) - x distributions
        pred_y: numpy array of shape (num_keypoints, height) - y distributions
        threshold: minimum confidence threshold

    Returns:
        keypoints: numpy array of shape (num_keypoints, 3) - [x, y, confidence]
    """
    num_keypoints = pred_x.shape[0]
    keypoints = np.zeros((num_keypoints, 3), dtype=np.float32)

    for i in range(num_keypoints):
        # Get argmax (most likely position)
        x_coord = np.argmax(pred_x[i])
        y_coord = np.argmax(pred_y[i])

        # Get confidence (max probability)
        x_conf = pred_x[i, x_coord]
        y_conf = pred_y[i, y_coord]
        confidence = (x_conf + y_conf) / 2.0

        keypoints[i] = [x_coord, y_coord, confidence]

        # Set confidence to 0 if below threshold
        if confidence < threshold:
            keypoints[i, 2] = 0.0

    return keypoints
