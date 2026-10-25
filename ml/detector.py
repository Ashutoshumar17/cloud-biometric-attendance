from __future__ import annotations
"""Face detection using MTCNN from facenet-pytorch."""
import logging
import numpy as np
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
from PIL import Image
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)

class FaceDetector:
    """MTCNN-based face detector.
    
    Detects faces in images, returns bounding boxes, landmarks,
    and aligned/cropped face tensors ready for embedding extraction.
    """
    
    def __init__(self, device=None):
        from facenet_pytorch import MTCNN
        from ml.config import ml_config
        
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.config = ml_config
        
        # MTCNN for detection + alignment + cropping
        self.mtcnn = MTCNN(
            image_size=self.config.mtcnn_image_size,
            margin=self.config.mtcnn_margin,
            min_face_size=self.config.mtcnn_min_face_size,
            thresholds=self.config.mtcnn_thresholds,
            factor=self.config.mtcnn_factor,
            post_process=True,  # Normalizes to [-1, 1]
            device=self.device,
            keep_all=True  # Detect ALL faces (we check count ourselves)
        )
        
        # Single-face MTCNN (returns only highest-confidence face)
        self.mtcnn_single = MTCNN(
            image_size=self.config.mtcnn_image_size,
            margin=self.config.mtcnn_margin,
            min_face_size=self.config.mtcnn_min_face_size,
            thresholds=self.config.mtcnn_thresholds,
            factor=self.config.mtcnn_factor,
            post_process=True,
            device=self.device,
            keep_all=False  # Return only best face
        )
        
        logger.info(f'FaceDetector initialized on {self.device}')
    
    def detect_faces(self, image: Image.Image) -> Dict:
        """Detect all faces in an image.
        
        Args:
            image: PIL Image (RGB)
            
        Returns:
            Dict with keys:
                - num_faces: int
                - faces: list of face tensors [3, 160, 160]
                - boxes: list of bounding boxes [x1, y1, x2, y2]
                - confidences: list of detection confidences
        """
        image = image.convert('RGB')
        
        boxes, confidences = self.mtcnn.detect(image)
        
        if boxes is None or len(boxes) == 0:
            return {
                'num_faces': 0,
                'faces': [],
                'boxes': [],
                'confidences': []
            }
        
        # Get aligned face tensors
        face_tensors = self.mtcnn(image)
        
        if face_tensors is None:
            return {
                'num_faces': 0,
                'faces': [],
                'boxes': [],
                'confidences': []
            }
        
        # Ensure tensors are in list format
        if face_tensors.dim() == 3:
            face_tensors = face_tensors.unsqueeze(0)
        
        num_faces = face_tensors.shape[0]
        
        return {
            'num_faces': num_faces,
            'faces': [face_tensors[i] for i in range(num_faces)],
            'boxes': boxes.tolist() if isinstance(boxes, np.ndarray) else boxes,
            'confidences': confidences.tolist() if isinstance(confidences, np.ndarray) else confidences
        }
    
    def detect_single_face(self, image: Image.Image) -> Optional[torch.Tensor]:
        """Detect and return the single best face as a preprocessed tensor.
        
        Args:
            image: PIL Image (RGB)
            
        Returns:
            Face tensor [3, 160, 160] normalized to [-1, 1], or None if no face found.
        """
        image = image.convert('RGB')
        face_tensor = self.mtcnn_single(image)
        return face_tensor
    
    def validate_single_face(self, image: Image.Image) -> Tuple[str, Optional[torch.Tensor]]:
        """Validate that exactly one face is present and return it.
        
        Args:
            image: PIL Image (RGB)
            
        Returns:
            Tuple of (status, face_tensor)
            status: 'ok', 'no_face', 'multiple_faces'
            face_tensor: preprocessed face tensor or None
        """
        result = self.detect_faces(image)
        
        if result['num_faces'] == 0:
            return 'no_face', None
        elif result['num_faces'] > 1:
            return 'multiple_faces', None
        else:
            return 'ok', result['faces'][0]
