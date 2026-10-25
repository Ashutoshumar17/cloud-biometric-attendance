"""FastAPI router for attendance tracking, session controls, and reporting."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel, Field

from backend.services import session_service, attendance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

class StartSessionRequest(BaseModel):
    course: str = Field(..., min_length=1, max_length=100, description="Course or Subject name")
    date: Optional[str] = Field(None, description="Session date (YYYY-MM-DD), defaults to today")
    session_id: Optional[str] = Field(None, description="Custom session ID (auto-generated if omitted)")

class EndSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="ID of session to end")

@router.post("/sessions/start", status_code=status.HTTP_201_CREATED)
def start_session(request: StartSessionRequest):
    """Start a new attendance session for a class/course."""
    try:
        session = session_service.start_session(
            course=request.course,
            date=request.date,
            session_id=request.session_id
        )
        return {
            "success": True,
            "message": f"Session '{session['session_id']}' started successfully",
            "session": session
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start session")

@router.post("/sessions/end")
def end_session(request: EndSessionRequest):
    """Conclude an ongoing attendance session."""
    try:
        session = session_service.end_session(request.session_id)
        return {
            "success": True,
            "message": f"Session '{request.session_id}' concluded successfully",
            "session": session
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to end session")

@router.get("/sessions/active")
def get_active_session():
    """Retrieve details of the currently active session."""
    session = session_service.get_active_session()
    return {
        "success": True,
        "active": session is not None,
        "session": session
    }

@router.get("/sessions")
def list_sessions():
    """List all created sessions with their statuses and attendance summaries."""
    sessions = session_service.get_all_sessions()
    return {
        "success": True,
        "count": len(sessions),
        "data": sessions
    }

@router.get("")
def get_attendance(
    session_id: Optional[str] = None,
    date: Optional[str] = None,
    student_id: Optional[str] = None,
    department: Optional[str] = None
):
    """Retrieve attendance records with optional filtering by session, date, student, or department."""
    try:
        records = attendance_service.get_attendance_records(
            session_id=session_id,
            date=date,
            student_id=student_id,
            department=department
        )
        return {
            "success": True,
            "count": len(records),
            "data": records
        }
    except Exception as e:
        logger.error(f"Error querying attendance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve attendance")

@router.get("/export/csv")
def export_csv(session_id: str):
    """Export attendance records for a specific session in CSV format."""
    try:
        csv_content = attendance_service.export_attendance_csv(session_id=session_id)
        filename = f"attendance_{session_id}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to export CSV")

@router.get("/{student_id}")
def get_student_attendance(student_id: str):
    """Retrieve full attendance history for a single student."""
    try:
        records = attendance_service.get_student_attendance(student_id)
        return {
            "success": True,
            "student_id": student_id,
            "count": len(records),
            "data": records
        }
    except Exception as e:
        logger.error(f"Error fetching student attendance: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve student attendance")
