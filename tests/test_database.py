"""Unit tests for MongoDB database operations and student service."""
import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId

from backend.services import student_service

def test_serialize_doc():
    """Test helper converting ObjectId and datetime to serializable format."""
    doc = {
        "_id": ObjectId("66d8e20f12a4b8c9d0e1f2a3"),
        "name": "Rahul Kumar",
        "student_id": "23BEC101"
    }
    serialized = student_service._serialize_doc(doc)
    assert isinstance(serialized["_id"], str)
    assert serialized["_id"] == "66d8e20f12a4b8c9d0e1f2a3"

@patch("backend.services.student_service.get_students_collection")
def test_register_student_missing_fields(mock_get_coll):
    """Test validation of required fields during student registration."""
    with pytest.raises(ValueError, match="Missing required field: semester"):
        student_service.register_student({
            "student_id": "23BEC101",
            "name": "Rahul Kumar",
            "department": "ECE",
            "section": "A"
            # Missing 'semester'
        })

@patch("backend.services.student_service.get_students_collection")
def test_register_student_success(mock_get_coll):
    """Test successful student registration."""
    mock_coll = MagicMock()
    mock_coll.insert_one.return_value.inserted_id = ObjectId("66d8e20f12a4b8c9d0e1f2a3")
    mock_get_coll.return_value = mock_coll

    student_data = {
        "student_id": "23BEC101",
        "name": "Rahul Kumar",
        "department": "ECE",
        "semester": 5,
        "section": "A",
        "email": "rahul@example.com"
    }

    result = student_service.register_student(student_data)
    assert result["student_id"] == "23BEC101"
    assert result["name"] == "Rahul Kumar"
    assert result["status"] == "active"
    assert result["face_samples_count"] == 0
    assert result["embedding_generated"] is False
    assert mock_coll.insert_one.called

@patch("backend.services.student_service.get_students_collection")
def test_get_student_not_found(mock_get_coll):
    """Test querying non-existent student."""
    mock_coll = MagicMock()
    mock_coll.find_one.return_value = None
    mock_get_coll.return_value = mock_coll

    result = student_service.get_student("NON_EXISTENT")
    assert result is None
