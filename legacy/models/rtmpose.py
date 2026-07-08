"""
RTMPose Model Implementation
Real-Time Multi-Person Pose Estimation with SimCC head

Architecture:
- Backbone: ResNet50 (from torchvision, optionally pretrained on ImageNet)
- Global Average Pooling
- Fully Connected layers
- SimCC head: Separate predictions for x and y coordinates
"""
import torch
import torch.nn as nn
import torchvision.models as models
from typing import Tuple
import config


class SimCCHead(nn.Module):
    """
    SimCC (Simulated Classification Coordinates) Head
    Predicts x and y coordinates as separate 1D classification problems
    """

    def __init__(
        self,
        in_channels: int,
        num_keypoints: int,
        input_size: Tuple[int, int],
        hidden_dim: int = 512
    ):
        """
        Args:
            in_channels: number of input channels from backbone
            num_keypoints: number of keypoints to predict (17 for COCO)
            input_size: (height, width) of input image
            hidden_dim: dimension of hidden layer
        """
        super().__init__()

        self.num_keypoints = num_keypoints
        self.input_height, self.input_width = input_size

        # Shared feature transformation
        self.fc_hidden = nn.Linear(in_channels, hidden_dim)
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(0.5)

        # Separate heads for x and y predictions
        # x head: predicts which column (width dimension)
        self.fc_x = nn.Linear(hidden_dim, num_keypoints * self.input_width)

        # y head: predicts which row (height dimension)
        self.fc_y = nn.Linear(hidden_dim, num_keypoints * self.input_height)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass

        Args:
            x: tensor of shape (batch, in_channels)

        Returns:
            pred_x: tensor of shape (batch, num_keypoints, width) - x coordinate logits
            pred_y: tensor of shape (batch, num_keypoints, height) - y coordinate logits
        """
        batch_size = x.shape[0]

        # Shared transformation
        x = self.fc_hidden(x)
        x = self.relu(x)
        x = self.dropout(x)

        # X predictions
        pred_x = self.fc_x(x)  # (batch, num_keypoints * width)
        pred_x = pred_x.reshape(batch_size, self.num_keypoints, self.input_width)

        # Y predictions
        pred_y = self.fc_y(x)  # (batch, num_keypoints * height)
        pred_y = pred_y.reshape(batch_size, self.num_keypoints, self.input_height)

        return pred_x, pred_y


class RTMPose(nn.Module):
    """
    RTMPose Model: Pose estimation with SimCC coordinate representation

    Architecture:
        Input (3, 256, 192)
        ↓
        ResNet50 Backbone
        ↓
        Global Average Pooling → (2048,)
        ↓
        SimCC Head
        ↓
        Output: (num_keypoints, W), (num_keypoints, H)
    """

    def __init__(
        self,
        num_keypoints: int = config.NUM_KEYPOINTS,
        input_size: Tuple[int, int] = config.INPUT_SIZE,
        pretrained: bool = True,
        hidden_dim: int = 512
    ):
        """
        Args:
            num_keypoints: number of keypoints (17 for COCO)
            input_size: (height, width) of input images
            pretrained: use ImageNet pretrained weights for backbone
            hidden_dim: dimension of hidden layer in SimCC head
        """
        super().__init__()

        self.num_keypoints = num_keypoints
        self.input_size = input_size

        # Load ResNet50 backbone
        if pretrained:
            print("Loading ResNet50 with ImageNet pretrained weights...")
            resnet = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
        else:
            print("Loading ResNet50 without pretrained weights...")
            resnet = models.resnet50(weights=None)

        # Remove the final fully connected layer
        # ResNet50 structure: conv layers → avgpool → fc
        # We want: conv layers → avgpool → our SimCC head
        self.backbone = nn.Sequential(*list(resnet.children())[:-1])

        # Get number of output channels from backbone (2048 for ResNet50)
        backbone_out_channels = 2048

        # Global average pooling is already included in backbone
        # Output shape after backbone: (batch, 2048, 1, 1)

        # SimCC head for coordinate prediction
        self.simcc_head = SimCCHead(
            in_channels=backbone_out_channels,
            num_keypoints=num_keypoints,
            input_size=input_size,
            hidden_dim=hidden_dim
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass

        Args:
            x: input tensor of shape (batch, 3, height, width)

        Returns:
            pred_x: tensor of shape (batch, num_keypoints, width) - x coordinate logits
            pred_y: tensor of shape (batch, num_keypoints, height) - y coordinate logits
        """
        # Extract features with backbone
        features = self.backbone(x)  # (batch, 2048, 1, 1)

        # Flatten spatial dimensions
        features = features.flatten(1)  # (batch, 2048)

        # Predict coordinates with SimCC head
        pred_x, pred_y = self.simcc_head(features)

        return pred_x, pred_y

    def predict_keypoints(
        self,
        x: torch.Tensor,
        threshold: float = 0.1
    ) -> torch.Tensor:
        """
        Predict keypoint coordinates from input image

        Args:
            x: input tensor of shape (batch, 3, height, width)
            threshold: confidence threshold for keypoints

        Returns:
            keypoints: tensor of shape (batch, num_keypoints, 3) - [x, y, confidence]
        """
        from utils.transforms import simcc_to_keypoints

        # Get predictions
        pred_x, pred_y = self.forward(x)

        # Apply softmax to get distributions
        pred_x = torch.softmax(pred_x, dim=-1)
        pred_y = torch.softmax(pred_y, dim=-1)

        # Convert to numpy and extract keypoints
        batch_size = pred_x.shape[0]
        keypoints = torch.zeros(batch_size, self.num_keypoints, 3, device=x.device)

        for i in range(batch_size):
            kpts = simcc_to_keypoints(
                pred_x[i].cpu().numpy(),
                pred_y[i].cpu().numpy(),
                threshold=threshold
            )
            keypoints[i] = torch.from_numpy(kpts).to(x.device)

        return keypoints


def create_rtmpose(
    num_keypoints: int = config.NUM_KEYPOINTS,
    input_size: Tuple[int, int] = config.INPUT_SIZE,
    pretrained: bool = True,
    hidden_dim: int = 512
) -> RTMPose:
    """
    Factory function to create RTMPose model

    Args:
        num_keypoints: number of keypoints (17 for COCO)
        input_size: (height, width) of input images
        pretrained: use ImageNet pretrained weights
        hidden_dim: dimension of hidden layer

    Returns:
        RTMPose model
    """
    model = RTMPose(
        num_keypoints=num_keypoints,
        input_size=input_size,
        pretrained=pretrained,
        hidden_dim=hidden_dim
    )

    return model


def load_checkpoint(
    model: RTMPose,
    checkpoint_path: str,
    device: str = 'cpu'
) -> Tuple[RTMPose, int, float]:
    """
    Load model from checkpoint

    Args:
        model: RTMPose model
        checkpoint_path: path to checkpoint file
        device: device to load model to

    Returns:
        model: loaded model
        epoch: epoch number from checkpoint
        best_metric: best validation metric from checkpoint
    """
    print(f"Loading checkpoint from {checkpoint_path}...")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    model.load_state_dict(checkpoint['model_state_dict'])

    epoch = checkpoint.get('epoch', 0)
    best_metric = checkpoint.get('val_pck', 0.0)

    print(f"Loaded checkpoint from epoch {epoch} with PCK: {best_metric:.4f}")

    return model, epoch, best_metric


if __name__ == '__main__':
    # Test model creation and forward pass
    print("Testing RTMPose model...")

    # Create model
    model = create_rtmpose(pretrained=False)
    print(f"\nModel created successfully!")

    # Print model summary
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Test forward pass
    batch_size = 2
    dummy_input = torch.randn(batch_size, 3, config.INPUT_HEIGHT, config.INPUT_WIDTH)
    print(f"\nInput shape: {dummy_input.shape}")

    pred_x, pred_y = model(dummy_input)
    print(f"Output pred_x shape: {pred_x.shape}")
    print(f"Output pred_y shape: {pred_y.shape}")

    # Test keypoint prediction
    keypoints = model.predict_keypoints(dummy_input)
    print(f"Predicted keypoints shape: {keypoints.shape}")

    print("\n✓ Model test passed!")
