"""
Training script for RTMPose
Includes data loading, training loop, validation, checkpointing, and logging
"""
import os
import argparse
import time
from datetime import datetime
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader

import config
from models import create_rtmpose
from utils.dataset import get_train_loader, get_val_loader
from utils.loss import weighted_simcc_loss
from utils.visualization import save_prediction_grid


def compute_pck(
    pred_x: torch.Tensor,
    pred_y: torch.Tensor,
    target_x: torch.Tensor,
    target_y: torch.Tensor,
    keypoints: torch.Tensor,
    threshold: float = config.PCK_THRESHOLD
) -> float:
    """
    Compute PCK (Percentage of Correct Keypoints) metric

    Args:
        pred_x: (batch, num_keypoints, W) predicted x distributions
        pred_y: (batch, num_keypoints, H) predicted y distributions
        target_x: (batch, num_keypoints, W) target x distributions
        target_y: (batch, num_keypoints, H) target y distributions
        keypoints: (batch, num_keypoints, 3) ground truth keypoints
        threshold: distance threshold as percentage of bbox diagonal

    Returns:
        pck: percentage of correct keypoints
    """
    batch_size, num_keypoints, _ = pred_x.shape

    # Get predicted coordinates (argmax)
    pred_x_coords = torch.argmax(pred_x, dim=-1).float()  # (batch, num_keypoints)
    pred_y_coords = torch.argmax(pred_y, dim=-1).float()  # (batch, num_keypoints)

    # Get target coordinates (argmax)
    target_x_coords = torch.argmax(target_x, dim=-1).float()
    target_y_coords = torch.argmax(target_y, dim=-1).float()

    # Calculate Euclidean distance
    distances = torch.sqrt(
        (pred_x_coords - target_x_coords) ** 2 +
        (pred_y_coords - target_y_coords) ** 2
    )

    # Get visibility mask (only evaluate visible keypoints)
    visibility = keypoints[:, :, 2]
    visible_mask = (visibility == config.VISIBILITY_VISIBLE).float()

    # Calculate bbox diagonal as normalization factor
    # Use input size diagonal as approximation
    bbox_diag = np.sqrt(config.INPUT_HEIGHT ** 2 + config.INPUT_WIDTH ** 2)
    threshold_pixels = threshold * bbox_diag

    # Count correct keypoints (within threshold distance)
    correct = (distances < threshold_pixels).float() * visible_mask
    total_visible = visible_mask.sum()

    if total_visible > 0:
        pck = correct.sum() / total_visible
    else:
        pck = 0.0

    return pck.item()


def train_epoch(
    model: torch.nn.Module,
    train_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: str,
    epoch: int
) -> tuple:
    """
    Train for one epoch

    Returns:
        avg_loss: average loss for the epoch
        avg_pck: average PCK for the epoch
    """
    model.train()

    total_loss = 0.0
    total_x_loss = 0.0
    total_y_loss = 0.0
    total_pck = 0.0
    num_batches = len(train_loader)

    start_time = time.time()

    for batch_idx, batch in enumerate(train_loader):
        # Move data to device
        images = batch['image'].to(device)
        target_x = batch['target_x'].to(device)
        target_y = batch['target_y'].to(device)
        keypoints = batch['keypoints'].to(device)

        # Forward pass
        pred_x, pred_y = model(images)

        # Calculate loss
        loss, x_loss, y_loss = weighted_simcc_loss(
            pred_x, pred_y, target_x, target_y, keypoints
        )

        # Backward pass
        optimizer.zero_grad()
        loss.backward()

        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()

        # Calculate PCK
        with torch.no_grad():
            pck = compute_pck(pred_x, pred_y, target_x, target_y, keypoints)

        # Accumulate metrics
        total_loss += loss.item()
        total_x_loss += x_loss.item()
        total_y_loss += y_loss.item()
        total_pck += pck

        # Log progress
        if (batch_idx + 1) % config.LOG_INTERVAL == 0:
            avg_loss = total_loss / (batch_idx + 1)
            avg_pck = total_pck / (batch_idx + 1)
            elapsed = time.time() - start_time
            print(f"Epoch [{epoch}] Batch [{batch_idx + 1}/{num_batches}] "
                  f"Loss: {avg_loss:.4f} (x: {total_x_loss/(batch_idx+1):.4f}, "
                  f"y: {total_y_loss/(batch_idx+1):.4f}) "
                  f"PCK: {avg_pck:.4f} "
                  f"Time: {elapsed:.1f}s")

    # Calculate averages
    avg_loss = total_loss / num_batches
    avg_x_loss = total_x_loss / num_batches
    avg_y_loss = total_y_loss / num_batches
    avg_pck = total_pck / num_batches

    epoch_time = time.time() - start_time
    print(f"\nEpoch [{epoch}] Training Summary:")
    print(f"  Loss: {avg_loss:.4f} (x: {avg_x_loss:.4f}, y: {avg_y_loss:.4f})")
    print(f"  PCK: {avg_pck:.4f}")
    print(f"  Time: {epoch_time:.1f}s")

    return avg_loss, avg_pck


def validate(
    model: torch.nn.Module,
    val_loader: DataLoader,
    device: str,
    epoch: int,
    save_vis: bool = False
) -> tuple:
    """
    Validate the model

    Returns:
        avg_loss: average validation loss
        avg_pck: average validation PCK
    """
    model.eval()

    total_loss = 0.0
    total_x_loss = 0.0
    total_y_loss = 0.0
    total_pck = 0.0
    num_batches = len(val_loader)

    start_time = time.time()

    with torch.no_grad():
        for batch_idx, batch in enumerate(val_loader):
            # Move data to device
            images = batch['image'].to(device)
            target_x = batch['target_x'].to(device)
            target_y = batch['target_y'].to(device)
            keypoints = batch['keypoints'].to(device)

            # Forward pass
            pred_x, pred_y = model(images)

            # Calculate loss
            loss, x_loss, y_loss = weighted_simcc_loss(
                pred_x, pred_y, target_x, target_y, keypoints
            )

            # Calculate PCK
            pck = compute_pck(pred_x, pred_y, target_x, target_y, keypoints)

            # Accumulate metrics
            total_loss += loss.item()
            total_x_loss += x_loss.item()
            total_y_loss += y_loss.item()
            total_pck += pck

            # Save visualization for first batch
            if save_vis and batch_idx == 0:
                os.makedirs('visualizations', exist_ok=True)
                save_path = f'visualizations/epoch_{epoch}_val.png'
                save_prediction_grid(
                    images, (pred_x, pred_y), (target_x, target_y),
                    save_path=save_path, num_samples=4
                )

    # Calculate averages
    avg_loss = total_loss / num_batches
    avg_x_loss = total_x_loss / num_batches
    avg_y_loss = total_y_loss / num_batches
    avg_pck = total_pck / num_batches

    val_time = time.time() - start_time
    print(f"\nEpoch [{epoch}] Validation Summary:")
    print(f"  Loss: {avg_loss:.4f} (x: {avg_x_loss:.4f}, y: {avg_y_loss:.4f})")
    print(f"  PCK: {avg_pck:.4f}")
    print(f"  Time: {val_time:.1f}s")

    return avg_loss, avg_pck


def save_checkpoint(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    val_pck: float,
    is_best: bool = False
):
    """Save model checkpoint"""
    os.makedirs(config.CHECKPOINT_DIR, exist_ok=True)

    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'val_pck': val_pck,
    }

    # Save regular checkpoint
    checkpoint_path = os.path.join(config.CHECKPOINT_DIR, f'checkpoint_epoch_{epoch}.pth')
    torch.save(checkpoint, checkpoint_path)
    print(f"Saved checkpoint to {checkpoint_path}")

    # Save best checkpoint
    if is_best:
        best_path = os.path.join(config.CHECKPOINT_DIR, 'best_model.pth')
        torch.save(checkpoint, best_path)
        print(f"Saved best model to {best_path}")


def main():
    parser = argparse.ArgumentParser(description='Train RTMPose model')
    parser.add_argument('--batch-size', type=int, default=config.BATCH_SIZE,
                        help='batch size for training')
    parser.add_argument('--epochs', type=int, default=config.NUM_EPOCHS,
                        help='number of epochs to train')
    parser.add_argument('--lr', type=float, default=config.LEARNING_RATE,
                        help='learning rate')
    parser.add_argument('--resume', type=str, default=None,
                        help='path to checkpoint to resume from')
    parser.add_argument('--no-pretrained', action='store_true',
                        help='do not use pretrained backbone')
    parser.add_argument('--device', type=str, default=config.DEVICE,
                        help='device to use (cuda/cpu)')

    args = parser.parse_args()

    # Set device
    device = args.device
    print(f"Using device: {device}")

    # Create data loaders
    print("\nCreating data loaders...")
    train_loader = get_train_loader(batch_size=args.batch_size)
    val_loader = get_val_loader(batch_size=args.batch_size)

    print(f"Training samples: {len(train_loader.dataset)}")
    print(f"Validation samples: {len(val_loader.dataset)}")

    # Create model
    print("\nCreating model...")
    model = create_rtmpose(pretrained=not args.no_pretrained)
    model = model.to(device)

    # Print model info
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Create optimizer
    optimizer = optim.Adam(
        model.parameters(),
        lr=args.lr,
        weight_decay=config.WEIGHT_DECAY
    )

    # Learning rate scheduler
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=args.epochs,
        eta_min=config.LR_MIN
    )

    # Resume from checkpoint if specified
    start_epoch = 0
    best_pck = 0.0

    if args.resume:
        print(f"\nResuming from checkpoint: {args.resume}")
        checkpoint = torch.load(args.resume, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_pck = checkpoint.get('val_pck', 0.0)
        print(f"Resumed from epoch {checkpoint['epoch']}, best PCK: {best_pck:.4f}")

    # Training loop
    print(f"\nStarting training from epoch {start_epoch} to {args.epochs}...")
    print("=" * 80)

    for epoch in range(start_epoch, args.epochs):
        print(f"\n{'='*80}")
        print(f"Epoch {epoch + 1}/{args.epochs}")
        print(f"Learning rate: {optimizer.param_groups[0]['lr']:.6f}")
        print(f"{'='*80}")

        # Train
        train_loss, train_pck = train_epoch(
            model, train_loader, optimizer, device, epoch + 1
        )

        # Validate
        val_loss, val_pck = validate(
            model, val_loader, device, epoch + 1,
            save_vis=(epoch % 5 == 0)  # Save visualizations every 5 epochs
        )

        # Update learning rate
        scheduler.step()

        # Check if this is the best model
        is_best = val_pck > best_pck
        if is_best:
            best_pck = val_pck
            print(f"\n✓ New best PCK: {best_pck:.4f}")

        # Save checkpoint
        if (epoch + 1) % config.SAVE_FREQ == 0 or is_best:
            save_checkpoint(model, optimizer, epoch + 1, val_pck, is_best=is_best)

    print("\n" + "=" * 80)
    print("Training completed!")
    print(f"Best validation PCK: {best_pck:.4f}")
    print("=" * 80)


if __name__ == '__main__':
    main()
