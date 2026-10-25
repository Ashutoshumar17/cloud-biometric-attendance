"""Face recognition service orchestrating face detection, embedding extraction, and matching."""
import logging
import time
import numpy as np
from typing import Dict
from PIL import Image

from backend.config import settings
from backend.utils.image_utils import validate_base64_image, decode_base64_to_pil
from backend.database.collections import get_student_embeddings_collection

logger = logging.getLogger(__name__)

# Lazy-loaded singletons for ML components
_detector = None
_embedder = None
_preprocessor = None

def _get_detector():
    global _detector
    if _detector is None:
        from ml.detector import FaceDetector
        _detector = FaceDetector()
    return _detector

def _get_embedder():
    global _embedder
    if _embedder is None:
        from ml.embedder import FaceEmbedder
        _embedder = FaceEmbedder()
    return _embedder

def _get_preprocessor():
    global _preprocessor
    if _preprocessor is None:
        from ml.preprocessing import FacePreprocessor
        _preprocessor = FacePreprocessor()
    return _preprocessor

def recognize_face(image_base64: str, session_id: str = None) -> Dict:
    """
    Execute full face recognition workflow:
    1. Validate base64 image
    2. Decode image to RGB
    3. Run MTCNN face detection and validate exactly ONE face
    4. Extract 512-d L2-normalized FaceNet embedding
    5. Load student embeddings from MongoDB and perform fast vectorized dot product
    6. Compare top match against configurable similarity threshold
    """
    start_time = time.time()
    threshold = settings.RECOGNITION_THRESHOLD
    
    # 1. Image Validation
    is_valid, err_msg = validate_base64_image(image_base64)
    if not is_valid:
        return {
            'success': False,
            'error': 'invalid_image',
            'message': err_msg
        }

    try:
        # 2. Decode Image
        pil_image = decode_base64_to_pil(image_base64)
    except Exception as e:
        return {
            'success': False,
            'error': 'invalid_image',
            'message': f"Failed to decode image data: {str(e)}"
        }

    # 3. Detect and Validate Face
    detector = _get_detector()
    status, face_tensor = detector.validate_single_face(pil_image)

    if status == 'no_face':
        return {
            'success': False,
            'error': 'no_face',
            'message': 'No face detected in the frame. Please look directly at the camera.'
        }
    elif status == 'multiple_faces':
        return {
            'success': False,
            'error': 'multiple_faces',
            'message': 'Multiple faces detected. Please ensure only one student is in front of the camera.'
        }

    # 4. Extract 512-d Embedding
    embedder = _get_embedder()
    query_embedding = embedder.extract_embedding(face_tensor)

    # 5. Load Gallery from MongoDB
    embeddings_col = get_student_embeddings_collection()
    records = list(embeddings_col.find({}, {'student_id': 1, 'name': 1, 'embedding': 1}))

    if not records:
        return {
            'success': False,
            'error': 'empty_gallery',
            'message': 'No registered face embeddings found in database. Please register students and generate embeddings first.'
        }

    # Vectorized cosine similarity computation
    gallery_embeddings = np.array([r['embedding'] for r in records])
    gallery_ids = [r['student_id'] for r in records]
    gallery_names = {r['student_id']: r.get('name', 'Unknown') for r in records}

    match = embedder.find_best_match(query_embedding, gallery_embeddings, gallery_ids)
    best_score = float(match['confidence'])
    best_id = match['student_id']
    
    processing_time = int((time.time() - start_time) * 1000)

    # 6. Threshold Check
    if best_score >= threshold:
        return {
            'success': True,
            'matched': True,
            'student_id': best_id,
            'name': gallery_names.get(best_id, 'Unknown'),
            'confidence': round(best_score, 4),
            'threshold': threshold,
            'processing_time_ms': processing_time,
            'model_version': settings.MODEL_VERSION,
            'message': 'Face recognized successfully'
        }
    else:
        return {
            'success': True,
            'matched': False,
            'student_id': None,
            'name': 'Unknown',
            'confidence': round(best_score, 4),
            'threshold': threshold,
            'processing_time_ms': processing_time,
            'model_version': settings.MODEL_VERSION,
            'message': f"Face not recognized (similarity {round(best_score * 100, 1)}% is below {int(threshold * 100)}% threshold)"
        }
