from __future__ import annotations
"""Face image preprocessing and augmentation pipeline."""
import io
import base64
import logging
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
try:
    import torch
    from torchvision import transforms
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    transforms = None
    TORCH_AVAILABLE = False

from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

class FacePreprocessor:
    """Preprocessing pipeline for face images.
    
    Handles:
    - Base64 decoding
    - Image validation
    - Face cropping (via detector)
    - Resize to model input (160x160)
    - Normalization
    - Data augmentation for training
    """
    
    # Supported image formats
    SUPPORTED_FORMATS = {'JPEG', 'JPG', 'PNG', 'BMP', 'WEBP'}
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    
    def __init__(self):
        from ml.config import ml_config
        self.config = ml_config
        self.input_size = self.config.input_size
        
        if TORCH_AVAILABLE and transforms is not None:
            # Standard transform (matches MTCNN post_process)
            self.standard_transform = transforms.Compose([
                transforms.Resize((self.input_size, self.input_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # [-1, 1]
            ])
            
            # Augmentation transforms for training
            self.augmentation_transform = transforms.Compose([
                transforms.RandomRotation(degrees=self.config.augment_rotation),
                transforms.ColorJitter(brightness=self.config.augment_brightness),
                transforms.RandomHorizontalFlip(p=0.5 if self.config.augment_horizontal_flip else 0.0),
                transforms.Resize((self.input_size, self.input_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
            ])
        else:
            self.standard_transform = None
            self.augmentation_transform = None
    
    @staticmethod
    def decode_base64_image(base64_string: str) -> Image.Image:
        """Decode a base64-encoded image string to PIL Image.
        
        Handles both raw base64 and data URI format.
        """
        # Strip data URI prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',', 1)[1]
        
        image_bytes = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        return image
    
    @staticmethod
    def encode_image_base64(image: Image.Image, format: str = 'JPEG') -> str:
        """Encode a PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @staticmethod
    def validate_image(base64_string: str) -> Tuple[bool, str]:
        """Validate an image from base64 string.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check size
            if ',' in base64_string:
                raw = base64_string.split(',', 1)[1]
            else:
                raw = base64_string
            
            image_bytes = base64.b64decode(raw)
            
            if len(image_bytes) > FacePreprocessor.MAX_IMAGE_SIZE:
                return False, f'Image exceeds maximum size of {FacePreprocessor.MAX_IMAGE_SIZE // (1024*1024)} MB'
            
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.format and image.format.upper() not in FacePreprocessor.SUPPORTED_FORMATS:
                return False, f'Unsupported image format: {image.format}'
            
            if image.size[0] < 50 or image.size[1] < 50:
                return False, 'Image is too small (minimum 50x50 pixels)'
            
            return True, ''
            
        except Exception as e:
            return False, f'Invalid image data: {str(e)}'
    
    def preprocess_pil(self, image: Image.Image, augment: bool = False) -> torch.Tensor:
        """Preprocess a PIL image to model input tensor.
        
        Note: This does NOT perform face detection/cropping.
        Use the FaceDetector for that, then pass the cropped face here.
        
        Args:
            image: PIL Image (RGB)
            augment: Whether to apply augmentation
            
        Returns:
            Tensor of shape [3, 160, 160]
        """
        image = image.convert('RGB')
        
        if augment:
            return self.augmentation_transform(image)
        else:
            return self.standard_transform(image)
    
    def generate_augmented_samples(self, image: Image.Image, num_augments: int = 5) -> List[torch.Tensor]:
        """Generate augmented versions of a face image.
        
        Args:
            image: PIL Image (RGB) - should be a cropped face
            num_augments: Number of augmented samples to generate
            
        Returns:
            List of augmented tensors [3, 160, 160]
        """
        augmented = []
        for _ in range(num_augments):
            augmented.append(self.augmentation_transform(image.convert('RGB')))
        return augmented
    
    @staticmethod
    def bytes_to_pil(image_bytes: bytes) -> Image.Image:
        """Convert raw image bytes to PIL Image."""
        return Image.open(io.BytesIO(image_bytes)).convert('RGB')
    
    @staticmethod
    def pil_to_bytes(image: Image.Image, format: str = 'JPEG') -> bytes:
        """Convert PIL Image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
