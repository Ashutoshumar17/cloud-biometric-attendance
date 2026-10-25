"""FastAPI router for faculty dashboard metrics, analytics, and summaries."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from backend.services import student_service, session_service, attendance_service
from backend.database.collections import get_recognition_logs_collection, get_attendance_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary():
    """
    Generate high-level statistical summary for the faculty dashboard.
    Returns:
    - Total registered student count
    - Total session count
    - Active session stats (present, absent, percentage)
    - Recent recognition events feed (last 10 events)
    """
    try:
        total_students = student_service.get_student_count()
        sessions = session_service.get_all_sessions()
        active_session = session_service.get_active_session()
        
        session_stats = None
        if active_session:
            present_count = active_session.get('total_present', 0)
            absent_count = max(0, total_students - present_count)
            percentage = round((present_count / total_students * 100), 1) if total_students > 0 else 0.0
            session_stats = {
                "session_id": active_session["session_id"],
                "course": active_session["course"],
                "date": active_session["date"],
                "start_time": active_session.get("start_time"),
                "present": present_count,
                "absent": absent_count,
                "attendance_percentage": percentage
            }

        # Fetch recent recognition attempts from recognition_logs
        logs_col = get_recognition_logs_collection()
        recent_logs = list(logs_col.find().sort('timestamp', -1).limit(10))
        recent_activity = []
        for log in recent_logs:
            recent_activity.append({
                "student_id": log.get("matched_student_id") or "Unknown",
                "name": log.get("student_name") or "Unknown",
                "result": log.get("result"),
                "confidence": round(float(log.get("confidence", 0)) * 100, 1),
                "attendance_marked": log.get("attendance_marked", False),
                "time": log.get("timestamp").strftime("%H:%M:%S") if log.get("timestamp") else "N/A"
            })

        return {
            "success": True,
            "total_students": total_students,
            "total_sessions": len(sessions),
            "active_session": session_stats,
            "recent_recognitions": recent_activity
        }
    except Exception as e:
        logger.error(f"Error compiling dashboard summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load dashboard summary")

@router.get("/session/{session_id}")
def get_session_dashboard(session_id: str):
    """Retrieve detailed dashboard statistics and full roster for a specific session."""
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found")

        total_students = student_service.get_student_count()
        records = attendance_service.get_attendance_records(session_id=session_id)
        
        present_count = len(records)
        absent_count = max(0, total_students - present_count)
        percentage = round((present_count / total_students * 100), 1) if total_students > 0 else 0.0

        return {
            "success": True,
            "session": session,
            "stats": {
                "total_students": total_students,
                "present": present_count,
                "absent": absent_count,
                "attendance_percentage": percentage
            },
            "records": records
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session dashboard: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load session details")
