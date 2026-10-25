"""Session management service for creating, managing, and concluding attendance sessions."""
import logging
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from backend.database.collections import get_sessions_collection, get_attendance_collection

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

def start_session(course: str, date: str = None, session_id: str = None, created_by: str = "Faculty") -> dict:
    """
    Start a new attendance session.
    If another session is currently active, it is marked as completed or warned.
    """
    sessions_col = get_sessions_collection()
    
    # Check if there is an active session
    active = sessions_col.find_one({'status': 'active'})
    if active:
        logger.info(f"Auto-closing previously active session {active['session_id']}")
        sessions_col.update_one(
            {'_id': active['_id']},
            {'$set': {
                'status': 'completed',
                'end_time': datetime.now(timezone.utc).strftime("%H:%M:%S"),
                'updated_at': datetime.now(timezone.utc)
            }}
        )

    now = datetime.now(timezone.utc)
    current_date = date or now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    if not session_id:
        course_clean = "".join(c for c in course if c.isalnum()).upper()[:6]
        seq = sessions_col.count_documents({'date': current_date}) + 1
        session_id = f"{course_clean}-{current_date}-{seq:02d}"

    doc = {
        'session_id': session_id,
        'course': course,
        'date': current_date,
        'start_time': current_time,
        'end_time': None,
        'status': 'active',
        'total_present': 0,
        'created_by': created_by,
        'created_at': now
    }

    try:
        res = sessions_col.insert_one(doc)
        doc['_id'] = res.inserted_id
        return _serialize_doc(doc)
    except DuplicateKeyError:
        raise ValueError(f"Session with ID '{session_id}' already exists")
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise

def end_session(session_id: str) -> dict:
    """End an active attendance session and calculate final tally."""
    sessions_col = get_sessions_collection()
    att_col = get_attendance_collection()
    
    session = sessions_col.find_one({'session_id': session_id})
    if not session:
        raise ValueError(f"Session '{session_id}' not found")

    total_present = att_col.count_documents({'session_id': session_id, 'status': 'Present'})
    now = datetime.now(timezone.utc)

    updated = sessions_col.find_one_and_update(
        {'session_id': session_id},
        {'$set': {
            'status': 'completed',
            'end_time': now.strftime("%H:%M:%S"),
            'total_present': total_present,
            'updated_at': now
        }},
        return_document=True
    )
    return _serialize_doc(updated)

def get_active_session() -> dict:
    """Get the currently active attendance session, or None."""
    sessions_col = get_sessions_collection()
    att_col = get_attendance_collection()
    session = sessions_col.find_one({'status': 'active'}, sort=[('created_at', -1)])
    if session:
        # Dynamically refresh total_present count
        count = att_col.count_documents({'session_id': session['session_id'], 'status': 'Present'})
        session['total_present'] = count
    return _serialize_doc(session)

def get_session(session_id: str) -> dict:
    """Retrieve details for a specific session."""
    sessions_col = get_sessions_collection()
    att_col = get_attendance_collection()
    session = sessions_col.find_one({'session_id': session_id})
    if session:
        count = att_col.count_documents({'session_id': session['session_id'], 'status': 'Present'})
        session['total_present'] = count
    return _serialize_doc(session)

def get_all_sessions() -> list:
    """Retrieve all sessions ordered by creation date descending."""
    sessions_col = get_sessions_collection()
    sessions = list(sessions_col.find().sort('created_at', -1))
    return [_serialize_doc(s) for s in sessions]
