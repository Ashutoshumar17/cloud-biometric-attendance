"""Integration tests for FastAPI REST API endpoints using TestClient."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)

def test_health_check():
    """Verify /api/health returns valid system status."""
    with patch("backend.app.check_health") as mock_health:
        mock_health.return_value = {"status": "healthy", "message": "MongoDB connection is active"}
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model_version" in data
        assert "recognition_threshold" in data

@patch("backend.routes.students.student_service.register_student")
def test_register_student_api(mock_register):
    """Verify POST /api/students/register parses request and calls service."""
    mock_register.return_value = {
        "_id": "66d8e20f12a4b8c9d0e1f2a3",
        "student_id": "23BEC101",
        "name": "Rahul Kumar",
        "department": "ECE",
        "semester": 5,
        "section": "A"
    }

    payload = {
        "student_id": "23BEC101",
        "name": "Rahul Kumar",
        "department": "ECE",
        "semester": 5,
        "section": "A",
        "email": "rahul@example.com"
    }

    response = client.post("/api/students/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["student_id"] == "23BEC101"

@patch("backend.routes.attendance.session_service.get_active_session")
def test_get_active_session_api(mock_get_active):
    """Verify GET /api/attendance/sessions/active returns session status."""
    mock_get_active.return_value = {
        "session_id": "CC-2026-09-04-01",
        "course": "Cloud Computing",
        "date": "2026-09-04",
        "status": "active",
        "total_present": 5
    }

    response = client.get("/api/attendance/sessions/active")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["active"] is True
    assert data["session"]["session_id"] == "CC-2026-09-04-01"
