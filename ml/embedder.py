from __future__ import annotations
"""Face embedding extraction using InceptionResnetV1 (FaceNet)."""
import logging
import os
try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    F = None
    TORCH_AVAILABLE = False

import numpy as np
from typing import Optional, List
from PIL import Image

logger = logging.getLogger(__name__)

class FaceEmbedder:
    """Extracts 512-dimensional face embeddings using InceptionResnetV1.
    
    Uses VGGFace2 pretrained weights for robust face representation.
    Embeddings are L2-normalized to lie on the unit hypersphere.
    """
    
    def __init__(self, device=None, model_path=None):
        from facenet_pytorch import InceptionResnetV1
        from ml.config import ml_config
        
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.config = ml_config
        
        if model_path and os.path.exists(model_path):
            # Load fine-tuned model
            logger.info(f'Loading fine-tuned model from {model_path}')
            self.model = InceptionResnetV1(pretrained=None, classify=False)
            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict, strict=False)
        else:
            # Use pretrained VGGFace2 model
            logger.info('Loading pretrained VGGFace2 model')
            self.model = InceptionResnetV1(pretrained=self.config.pretrained)
        
        self.model = self.model.eval().to(self.device)
        logger.info(f'FaceEmbedder initialized on {self.device} (embedding_dim={self.config.embedding_dim})')
    
    def extract_embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        """Extract a 512-d L2-normalized embedding from a preprocessed face tensor.
        
        Args:
            face_tensor: Preprocessed face tensor of shape [3, 160, 160]
            
        Returns:
            numpy array of shape (512,), L2-normalized
        """
        with torch.no_grad():
            if face_tensor.dim() == 3:
                face_tensor = face_tensor.unsqueeze(0)  # [1, 3, 160, 160]
            
            face_tensor = face_tensor.to(self.device)
            raw_embedding = self.model(face_tensor)
            normalized = F.normalize(raw_embedding, p=2, dim=1)
            
            return normalized.squeeze().cpu().numpy()
    
    def extract_embeddings_batch(self, face_tensors: List[torch.Tensor]) -> List[np.ndarray]:
        """Extract embeddings for a batch of face tensors.
        
        Args:
            face_tensors: List of face tensors, each [3, 160, 160]
            
        Returns:
            List of numpy arrays, each of shape (512,)
        """
        if not face_tensors:
            return []
        
        batch = torch.stack(face_tensors).to(self.device)  # [N, 3, 160, 160]
        
        with torch.no_grad():
            raw_embeddings = self.model(batch)
            normalized = F.normalize(raw_embeddings, p=2, dim=1)
        
        return [normalized[i].cpu().numpy() for i in range(normalized.shape[0])]
    
    @staticmethod
    def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two L2-normalized embeddings.
        
        Since embeddings are already L2-normalized, cosine similarity
        is simply the dot product.
        
        Args:
            embedding1: numpy array of shape (512,)
            embedding2: numpy array of shape (512,)
            
        Returns:
            Cosine similarity score in range [-1, 1]
        """
        return float(np.dot(embedding1, embedding2))
    
    @staticmethod
    def find_best_match(query_embedding: np.ndarray, gallery_embeddings: np.ndarray, 
                        gallery_ids: List[str]) -> dict:
        """Find the best matching identity from the gallery.
        
        Uses vectorized matrix multiplication for efficient 1:N matching.
        
        Args:
            query_embedding: numpy array of shape (512,)
            gallery_embeddings: numpy array of shape (N, 512)
            gallery_ids: list of student IDs corresponding to gallery rows
            
        Returns:
            dict with keys: student_id, confidence, index
        """
        if len(gallery_embeddings) == 0:
            return {'student_id': None, 'confidence': 0.0, 'index': -1}
        
        # Vectorized cosine similarity (embeddings are L2-normalized)
        similarities = np.dot(gallery_embeddings, query_embedding)
        
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        
        return {
            'student_id': gallery_ids[best_idx],
            'confidence': best_score,
            'index': best_idx
        }
