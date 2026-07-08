"""
Loss functions for RTMPose
Implements KL Divergence loss for SimCC coordinate representation
"""
import torch
import torch.nn.functional as F
from typing import Optional, Tuple


def simcc_kl_loss(
    pred_x: torch.Tensor,
    pred_y: torch.Tensor,
    target_x: torch.Tensor,
    target_y: torch.Tensor,
    weights: Optional[torch.Tensor] = None
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    SimCC KL Divergence Loss

    Calculates KL divergence between predicted and target distributions
    for x and y coordinates separately, then combines them.

    Args:
        pred_x: (batch, num_keypoints, W) - predicted x logits
        pred_y: (batch, num_keypoints, H) - predicted y logits
        target_x: (batch, num_keypoints, W) - target x distributions
        target_y: (batch, num_keypoints, H) - target y distributions
        weights: (batch, num_keypoints) - visibility weights (optional)
                 Should be 1.0 for visible keypoints, 0.0 for invisible

    Returns:
        total_loss: scalar tensor (combined x and y loss)
        x_loss: scalar tensor (x coordinate loss only)
        y_loss: scalar tensor (y coordinate loss only)
    """
    batch_size, num_keypoints, _ = pred_x.shape

    # Apply log_softmax to predictions (kl_div expects log probabilities)
    log_pred_x = F.log_softmax(pred_x, dim=-1)
    log_pred_y = F.log_softmax(pred_y, dim=-1)

    # Calculate KL divergence
    # F.kl_div(input, target) computes KL(target || input)
    # We want KL(target || pred), so we use reduction='none' and then average
    kl_x = F.kl_div(log_pred_x, target_x, reduction='none').sum(dim=-1)  # (batch, num_keypoints)
    kl_y = F.kl_div(log_pred_y, target_y, reduction='none').sum(dim=-1)  # (batch, num_keypoints)

    # Apply visibility weights if provided
    if weights is not None:
        kl_x = kl_x * weights
        kl_y = kl_y * weights
        # Normalize by number of visible keypoints
        num_visible = weights.sum() + 1e-6  # Add epsilon to avoid division by zero
        x_loss = kl_x.sum() / num_visible
        y_loss = kl_y.sum() / num_visible
    else:
        # Average over all keypoints and batch
        x_loss = kl_x.mean()
        y_loss = kl_y.mean()

    # Combine x and y losses
    total_loss = x_loss + y_loss

    return total_loss, x_loss, y_loss


def compute_visibility_weights(keypoints: torch.Tensor, visibility_threshold: int = 2) -> torch.Tensor:
    """
    Compute visibility weights from keypoint visibility flags

    Args:
        keypoints: (batch, num_keypoints, 3) - [x, y, visibility]
        visibility_threshold: minimum visibility value to consider (default 2 for visible only)

    Returns:
        weights: (batch, num_keypoints) - binary weights (1.0 for visible, 0.0 for invisible)
    """
    # Extract visibility flags (last dimension)
    visibility = keypoints[:, :, 2]

    # Create binary weights: 1.0 for visible keypoints, 0.0 otherwise
    weights = (visibility >= visibility_threshold).float()

    return weights


def weighted_simcc_loss(
    pred_x: torch.Tensor,
    pred_y: torch.Tensor,
    target_x: torch.Tensor,
    target_y: torch.Tensor,
    keypoints: torch.Tensor
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Convenience function that computes visibility weights and applies loss

    Args:
        pred_x: (batch, num_keypoints, W) - predicted x logits
        pred_y: (batch, num_keypoints, H) - predicted y logits
        target_x: (batch, num_keypoints, W) - target x distributions
        target_y: (batch, num_keypoints, H) - target y distributions
        keypoints: (batch, num_keypoints, 3) - [x, y, visibility]

    Returns:
        total_loss: scalar tensor (combined x and y loss)
        x_loss: scalar tensor (x coordinate loss only)
        y_loss: scalar tensor (y coordinate loss only)
    """
    # Compute visibility weights
    weights = compute_visibility_weights(keypoints)

    # Apply loss with weights
    return simcc_kl_loss(pred_x, pred_y, target_x, target_y, weights)


def smooth_l1_loss(
    pred_x: torch.Tensor,
    pred_y: torch.Tensor,
    target_x: torch.Tensor,
    target_y: torch.Tensor,
    weights: Optional[torch.Tensor] = None
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Alternative loss: Smooth L1 loss for SimCC distributions
    Can be used for experimentation

    Args:
        pred_x: (batch, num_keypoints, W) - predicted x distributions (after softmax)
        pred_y: (batch, num_keypoints, H) - predicted y distributions (after softmax)
        target_x: (batch, num_keypoints, W) - target x distributions
        target_y: (batch, num_keypoints, H) - target y distributions
        weights: (batch, num_keypoints) - visibility weights (optional)

    Returns:
        total_loss: scalar tensor (combined x and y loss)
        x_loss: scalar tensor (x coordinate loss only)
        y_loss: scalar tensor (y coordinate loss only)
    """
    # Apply softmax to predictions
    pred_x = F.softmax(pred_x, dim=-1)
    pred_y = F.softmax(pred_y, dim=-1)

    # Calculate smooth L1 loss
    loss_x = F.smooth_l1_loss(pred_x, target_x, reduction='none').sum(dim=-1)
    loss_y = F.smooth_l1_loss(pred_y, target_y, reduction='none').sum(dim=-1)

    # Apply weights
    if weights is not None:
        loss_x = loss_x * weights
        loss_y = loss_y * weights
        num_visible = weights.sum() + 1e-6
        x_loss = loss_x.sum() / num_visible
        y_loss = loss_y.sum() / num_visible
    else:
        x_loss = loss_x.mean()
        y_loss = loss_y.mean()

    total_loss = x_loss + y_loss

    return total_loss, x_loss, y_loss
