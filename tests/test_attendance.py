"""Unit tests for attendance check-in workflow and duplicate prevention."""
from unittest.mock import MagicMock, patch
from bson import ObjectId

from backend.services import attendance_service, session_service

@patch("backend.services.attendance_service.get_sessions_collection")
def test_mark_attendance_inactive_session(mock_get_sessions):
    """Ensure attendance is rejected if the session has concluded."""
    mock_sessions = MagicMock()
    mock_sessions.find_one.return_value = {
        "_id": ObjectId(),
        "session_id": "CS-101",
        "status": "completed"
    }
    mock_get_sessions.return_value = mock_sessions

    result = attendance_service.mark_attendance(
        student_id="23BEC101",
        name="Rahul Kumar",
        confidence=0.95,
        session_id="CS-101"
    )

    assert result["success"] is False
    assert result["attendance"] == "Not Marked"
    assert "concluded" in result["message"]

@patch("backend.services.attendance_service.get_attendance_collection")
@patch("backend.services.attendance_service.get_sessions_collection")
def test_duplicate_attendance_prevention(mock_get_sessions, mock_get_att):
    """Ensure a student cannot be marked present more than once in the same session."""
    mock_sessions = MagicMock()
    mock_sessions.find_one.return_value = {
        "_id": ObjectId(),
        "session_id": "CS-101",
        "status": "active",
        "date": "2026-09-04"
    }
    mock_get_sessions.return_value = mock_sessions

    # Simulate already present record in database
    mock_att = MagicMock()
    mock_att.find_one.return_value = {
        "_id": ObjectId(),
        "student_id": "23BEC101",
        "session_id": "CS-101",
        "status": "Present",
        "time": "09:03:14"
    }
    mock_get_att.return_value = mock_att

    result = attendance_service.mark_attendance(
        student_id="23BEC101",
        name="Rahul Kumar",
        confidence=0.96,
        session_id="CS-101"
    )

    assert result["success"] is True
    assert result["duplicate"] is True
    assert result["attendance"] == "Already Marked"
    assert "already marked" in result["message"].lower()

@patch("backend.services.attendance_service.get_attendance_collection")
@patch("backend.services.attendance_service.get_sessions_collection")
def test_first_time_attendance_marking(mock_get_sessions, mock_get_att):
    """Verify first-time attendance marking succeeds and updates session."""
    mock_sessions = MagicMock()
    mock_sessions.find_one.return_value = {
        "_id": ObjectId(),
        "session_id": "CS-101",
        "status": "active",
        "date": "2026-09-04"
    }
    mock_get_sessions.return_value = mock_sessions

    mock_att = MagicMock()
    mock_att.find_one.return_value = None  # Not yet present
    mock_att.insert_one.return_value.inserted_id = ObjectId()
    mock_get_att.return_value = mock_att

    result = attendance_service.mark_attendance(
        student_id="23BEC101",
        name="Rahul Kumar",
        confidence=0.96,
        session_id="CS-101"
    )

    assert result["success"] is True
    assert result["duplicate"] is False
    assert result["attendance"] == "Present"
    assert result["student_id"] == "23BEC101"
    assert mock_att.insert_one.called
    assert mock_sessions.update_one.called
