"""Face recognition inference module.

Provides a clean interface for face recognition that can be used
by both the local FastAPI backend and AWS Lambda handler.
"""
import logging
import time
import numpy as np
from typing import Dict, Optional
from PIL import Image

logger = logging.getLogger(__name__)

class FaceRecognitionEngine:
    """Complete face recognition inference engine.
    
    Encapsulates detection, embedding, and matching into a single
    reusable component with lazy model loading.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self._detector = None
        self._embedder = None
        self._model_path = model_path
        self._initialized = False
    
    def _initialize(self):
        """Lazy initialization of ML models."""
        if not self._initialized:
            from ml.detector import FaceDetector
            from ml.embedder import FaceEmbedder
            self._detector = FaceDetector()
            self._embedder = FaceEmbedder(model_path=self._model_path)
            self._initialized = True
            logger.info('FaceRecognitionEngine initialized')
    
    def recognize(self, image: Image.Image, gallery_embeddings: np.ndarray, 
                  gallery_ids: list, gallery_names: dict,
                  threshold: float = 0.65) -> Dict:
        """
        Recognize a face against the gallery.
        
        Args:
            image: PIL Image
            gallery_embeddings: (N, 512) array
            gallery_ids: list of student_ids
            gallery_names: dict mapping student_id to name
            threshold: recognition threshold
            
        Returns:
            Result dict with match info
        """
        self._initialize()
        start_time = time.time()
        
        # Detect and validate face
        status, face_tensor = self._detector.validate_single_face(image)
        
        if status == 'no_face':
            return {'success': False, 'error': 'no_face', 'message': 'No face detected'}
        elif status == 'multiple_faces':
            return {'success': False, 'error': 'multiple_faces', 'message': 'Multiple faces detected'}
        
        # Extract embedding
        query_embedding = self._embedder.extract_embedding(face_tensor)
        
        # Match against gallery
        match = self._embedder.find_best_match(query_embedding, gallery_embeddings, gallery_ids)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if match['confidence'] >= threshold:
            return {
                'success': True,
                'matched': True,
                'student_id': match['student_id'],
                'name': gallery_names.get(match['student_id'], ''),
                'confidence': round(match['confidence'], 4),
                'processing_time_ms': processing_time
            }
        else:
            return {
                'success': True,
                'matched': False,
                'confidence': round(match['confidence'], 4),
                'processing_time_ms': processing_time,
                'message': 'Face not recognized'
            }

# Singleton engine instance
_engine = None

def get_engine(model_path=None) -> FaceRecognitionEngine:
    global _engine
    if _engine is None:
        _engine = FaceRecognitionEngine(model_path=model_path)
    return _engine

def recognize_face_from_bytes(image_bytes: bytes, gallery_embeddings: np.ndarray,
                               gallery_ids: list, gallery_names: dict,
                               threshold: float = 0.65) -> Dict:
    """Convenience function for recognizing face from raw image bytes."""
    from ml.preprocessing import FacePreprocessor
    image = FacePreprocessor.bytes_to_pil(image_bytes)
    engine = get_engine()
    return engine.recognize(image, gallery_embeddings, gallery_ids, gallery_names, threshold)
