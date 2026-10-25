"""FastAPI router for student registration, profile queries, and face sample uploads."""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr

from backend.services import student_service
from backend.services.recognition_service import _get_preprocessor, _get_detector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/students", tags=["Students"])

class RegisterStudentRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=30, description="Unique student registration number")
    name: str = Field(..., min_length=1, max_length=100, description="Student full name")
    department: str = Field(..., min_length=1, max_length=50, description="Department name")
    semester: int = Field(..., ge=1, le=12, description="Semester number (1-12)")
    section: str = Field(..., min_length=1, max_length=10, description="Section code, e.g. A, B, C")
    email: Optional[str] = Field(None, description="Optional student email address")

class CaptureRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    image: str = Field(..., min_length=10, description="Base64 encoded face photograph")
    pose: Optional[str] = Field("front", description="Pose variation: front, left, right, smile, etc.")
    sample_index: int = Field(..., ge=1, description="Sequential sample index (1-based)")

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_student(request: RegisterStudentRequest):
    """Register a new student profile in MongoDB."""
    try:
        data = request.model_dump()
        result = student_service.register_student(data)
        return {
            "success": True,
            "message": f"Student '{request.name}' registered successfully",
            "student_id": request.student_id,
            "data": result
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error registering student: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register student")

@router.post("/capture")
def capture_face_sample(request: CaptureRequest):
    """
    Upload and save a single webcam face sample for a registered student.
    Validates face presence using MTCNN before persisting to MongoDB.
    """
    # 1. Verify student exists
    student = student_service.get_student(request.student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{request.student_id}' not found")

    try:
        # 2. Quick pre-check for face presence
        preprocessor = _get_preprocessor()
        is_valid, err_msg = preprocessor.validate_image(request.image)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

        pil_img = preprocessor.decode_base64_image(request.image)
        detector = _get_detector()
        face_status, _ = detector.validate_single_face(pil_img)
        
        face_detected = (face_status == 'ok')
        if not face_detected:
            # Still allow upload with flag, or provide warning
            logger.info(f"Sample {request.sample_index} for {request.student_id} had face status: {face_status}")

        result = student_service.add_face_sample(
            student_id=request.student_id,
            image_base64=request.image,
            sample_index=request.sample_index,
            pose=request.pose
        )
        
        updated_student = student_service.get_student(request.student_id)
        total_samples = updated_student.get('face_samples_count', 0) if updated_student else request.sample_index

        return {
            "success": True,
            "message": f"Face sample #{request.sample_index} stored successfully",
            "sample_index": request.sample_index,
            "face_detected": face_detected,
            "face_status": face_status,
            "total_samples": total_samples
        }
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error capturing face sample: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save face sample: {str(e)}")

@router.get("")
def list_students(department: Optional[str] = None, section: Optional[str] = None):
    """Retrieve all registered students, optionally filtered by department or section."""
    try:
        students = student_service.get_all_students(department=department, section=section)
        return {
            "success": True,
            "count": len(students),
            "data": students
        }
    except Exception as e:
        logger.error(f"Error listing students: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list students")

@router.get("/{student_id}")
def get_student(student_id: str):
    """Retrieve details of a specific student by student_id."""
    student = student_service.get_student(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{student_id}' not found")
    return {
        "success": True,
        "data": student
    }

@router.delete("/{student_id}")
def delete_student(student_id: str):
    """De-register student and delete all associated biometric and face sample records."""
    deleted = student_service.delete_student(student_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{student_id}' not found")
    return {
        "success": True,
        "message": f"Student '{student_id}' and all biometric data removed successfully"
    }
