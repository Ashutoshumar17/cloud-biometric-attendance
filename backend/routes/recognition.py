"""FastAPI router for facial recognition and attendance check-in orchestrator."""
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.recognition_service import recognize_face as execute_recognition
from backend.services.attendance_service import mark_attendance
from backend.services.session_service import get_session
from backend.database.collections import get_recognition_logs_collection, get_student_embeddings_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Recognition & Inference"])

class RecognizeRequest(BaseModel):
    image: str = Field(..., min_length=10, description="Base64 encoded webcam image frame")
    session_id: str = Field(..., min_length=1, description="Active attendance session ID")

@router.post("/recognize")
def recognize(request: RecognizeRequest):
    """
    Main face recognition and attendance endpoint.
    1. Runs ML pipeline to recognize student face.
    2. If recognized, records attendance with duplicate prevention.
    3. Logs the attempt into recognition_logs collection.
    """
    logs_col = get_recognition_logs_collection()
    session_id = request.session_id

    # 1. Verify session is valid
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance session '{session_id}' not found. Please start a session first."
        )

    # 2. Invoke ML recognition pipeline
    rec_result = execute_recognition(request.image, session_id=session_id)

    # Check for detection / payload errors
    if not rec_result.get('success'):
        error_code = rec_result.get('error', 'unknown_error')
        msg = rec_result.get('message', 'Recognition failed')

        # Log failed detection attempt
        logs_col.insert_one({
            'session_id': session_id,
            'result': error_code,
            'matched_student_id': None,
            'confidence': 0.0,
            'threshold': settings.RECOGNITION_THRESHOLD,
            'model_version': settings.MODEL_VERSION,
            'attendance_marked': False,
            'duplicate': False,
            'processing_time_ms': rec_result.get('processing_time_ms', 0),
            'error_message': msg,
            'timestamp': datetime.now(timezone.utc)
        })

        # Return 422 for face detection issues or 400 for image issues
        http_code = status.HTTP_422_UNPROCESSABLE_ENTITY if error_code in ('no_face', 'multiple_faces') else status.HTTP_400_BAD_REQUEST
        return {
            "success": False,
            "attendance": "Not Marked",
            "error": error_code,
            "message": msg
        }

    matched = rec_result.get('matched', False)
    confidence = rec_result.get('confidence', 0.0)
    processing_time = rec_result.get('processing_time_ms', 0)

    # 3. Handle Unknown / Low-confidence Face
    if not matched:
        logs_col.insert_one({
            'session_id': session_id,
            'result': 'no_match',
            'matched_student_id': None,
            'confidence': confidence,
            'threshold': settings.RECOGNITION_THRESHOLD,
            'model_version': settings.MODEL_VERSION,
            'attendance_marked': False,
            'duplicate': False,
            'processing_time_ms': processing_time,
            'error_message': 'Face not recognized',
            'timestamp': datetime.now(timezone.utc)
        })

        return {
            "success": True,
            "matched": False,
            "attendance": "Not Marked",
            "message": "Face not recognized",
            "confidence": confidence,
            "threshold": settings.RECOGNITION_THRESHOLD,
            "processing_time_ms": processing_time
        }

    # 4. Handle Recognized Face -> Mark Attendance
    student_id = rec_result['student_id']
    name = rec_result['name']

    att_result = mark_attendance(
        student_id=student_id,
        name=name,
        confidence=confidence,
        session_id=session_id,
        model_version=settings.MODEL_VERSION
    )

    is_duplicate = att_result.get('duplicate', False)
    attendance_status = att_result.get('attendance', 'Present')

    # Log successful recognition attempt
    logs_col.insert_one({
        'session_id': session_id,
        'result': 'duplicate' if is_duplicate else 'match',
        'matched_student_id': student_id,
        'student_name': name,
        'confidence': confidence,
        'threshold': settings.RECOGNITION_THRESHOLD,
        'model_version': settings.MODEL_VERSION,
        'attendance_marked': (attendance_status == 'Present' and not is_duplicate),
        'duplicate': is_duplicate,
        'processing_time_ms': processing_time,
        'error_message': None,
        'timestamp': datetime.now(timezone.utc)
    })

    return {
        "success": True,
        "matched": True,
        "student_id": student_id,
        "name": name,
        "confidence": confidence,
        "threshold": settings.RECOGNITION_THRESHOLD,
        "attendance": attendance_status,
        "duplicate": is_duplicate,
        "message": att_result.get('message'),
        "time": att_result.get('time'),
        "processing_time_ms": processing_time,
        "model_version": settings.MODEL_VERSION
    }

@router.post("/ml/generate-embeddings")
def trigger_generate_embeddings():
    """Batch generate and store 512-d embeddings for all registered students."""
    try:
        from ml.embeddings import generate_embeddings_for_all_students
        res = generate_embeddings_for_all_students()
        return {
            "success": True,
            "message": f"Successfully generated embeddings for {res.get('processed', 0)} students",
            "data": res
        }
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/ml/status")
def get_ml_status():
    """Retrieve ML pipeline health, model version, and gallery statistics."""
    try:
        emb_col = get_student_embeddings_collection()
        gallery_count = emb_col.count_documents({})
        return {
            "success": True,
            "model_name": "FaceNet (InceptionResnetV1)",
            "pretrained_weights": "vggface2",
            "embedding_dimension": 512,
            "model_version": settings.MODEL_VERSION,
            "recognition_threshold": settings.RECOGNITION_THRESHOLD,
            "gallery_size": gallery_count
        }
    except Exception as e:
        logger.error(f"Error checking ML status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
