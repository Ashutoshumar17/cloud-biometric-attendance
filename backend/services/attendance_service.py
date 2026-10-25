"""Attendance service handling check-in, duplicate prevention, records retrieval, and export."""
import io
import csv
import logging
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from backend.database.collections import (
    get_attendance_collection,
    get_sessions_collection,
    get_students_collection
)
from backend.config import settings

logger = logging.getLogger(__name__)

def _serialize_doc(doc):
    """Helper to convert ObjectId to string and datetime to ISO format."""
    if not doc:
        return None
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

def mark_attendance(student_id: str, name: str, confidence: float, session_id: str, model_version: str = None) -> dict:
    """
    Mark student attendance for a given session.
    Strictly checks and prevents duplicate check-ins for the same student in the same session.
    """
    sessions_col = get_sessions_collection()
    att_col = get_attendance_collection()
    
    # 1. Validate session
    session = sessions_col.find_one({'session_id': session_id})
    if not session:
        return {
            'success': False,
            'attendance': 'Not Marked',
            'message': f"Session '{session_id}' not found or inactive"
        }
        
    if session.get('status') != 'active':
        return {
            'success': False,
            'attendance': 'Not Marked',
            'message': f"Attendance session '{session_id}' has already concluded"
        }

    # 2. Check for duplicate attendance
    existing = att_col.find_one({'student_id': student_id, 'session_id': session_id})
    if existing:
        return {
            'success': True,
            'duplicate': True,
            'student_id': student_id,
            'name': name,
            'confidence': confidence,
            'attendance': 'Already Marked',
            'message': f"Attendance already marked for {name} ({student_id}) in this session",
            'time': existing.get('time')
        }

    now = datetime.now(timezone.utc)
    date_str = session.get('date', now.strftime("%Y-%m-%d"))
    time_str = now.strftime("%H:%M:%S")

    att_doc = {
        'student_id': student_id,
        'name': name,
        'date': date_str,
        'time': time_str,
        'status': 'Present',
        'confidence': round(float(confidence), 4),
        'session_id': session_id,
        'model_version': model_version or settings.MODEL_VERSION,
        'created_at': now
    }

    try:
        res = att_col.insert_one(att_doc)
        att_doc['_id'] = res.inserted_id
        
        # Increment session present count
        sessions_col.update_one(
            {'session_id': session_id},
            {'$inc': {'total_present': 1}}
        )

        return {
            'success': True,
            'duplicate': False,
            'student_id': student_id,
            'name': name,
            'confidence': att_doc['confidence'],
            'attendance': 'Present',
            'message': 'Attendance marked successfully',
            'date': date_str,
            'time': time_str,
            'model_version': att_doc['model_version']
        }
    except DuplicateKeyError:
        return {
            'success': True,
            'duplicate': True,
            'student_id': student_id,
            'name': name,
            'confidence': confidence,
            'attendance': 'Already Marked',
            'message': f"Attendance already marked for {name} ({student_id}) in this session"
        }
    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        return {
            'success': False,
            'attendance': 'Not Marked',
            'message': f"Internal server error marking attendance: {str(e)}"
        }

def get_attendance_records(session_id: str = None, date: str = None, student_id: str = None, department: str = None) -> list:
    """Retrieve attendance records with optional filtering."""
    att_col = get_attendance_collection()
    students_col = get_students_collection()
    
    query = {}
    if session_id:
        query['session_id'] = session_id
    if date:
        query['date'] = date
    if student_id:
        query['student_id'] = student_id

    records = list(att_col.find(query).sort('time', -1))
    
    # Enrich records with department if possible
    student_dept_map = {}
    if records:
        student_ids = list(set(r['student_id'] for r in records if 'student_id' in r))
        student_docs = students_col.find({'student_id': {'$in': student_ids}}, {'student_id': 1, 'department': 1})
        student_dept_map = {s['student_id']: s.get('department', 'N/A') for s in student_docs}

    filtered_records = []
    for r in records:
        r_serialized = _serialize_doc(r)
        dept = student_dept_map.get(r_serialized['student_id'], 'N/A')
        r_serialized['department'] = dept
        
        if department and dept != department:
            continue
        filtered_records.append(r_serialized)

    return filtered_records

def get_student_attendance(student_id: str) -> list:
    """Retrieve all attendance history for a given student."""
    att_col = get_attendance_collection()
    records = list(att_col.find({'student_id': student_id}).sort('date', -1))
    return [_serialize_doc(r) for r in records]

def export_attendance_csv(session_id: str) -> str:
    """Generate CSV string of attendance records for a given session."""
    records = get_attendance_records(session_id=session_id)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Session ID', 'Student ID', 'Name', 'Department', 'Date', 'Time', 'Status', 'Confidence', 'Model Version'])
    
    for r in records:
        writer.writerow([
            r.get('session_id', ''),
            r.get('student_id', ''),
            r.get('name', ''),
            r.get('department', ''),
            r.get('date', ''),
            r.get('time', ''),
            r.get('status', ''),
            f"{float(r.get('confidence', 0)) * 100:.1f}%" if r.get('confidence') is not None else '',
            r.get('model_version', '')
        ])
        
    return output.getvalue()
