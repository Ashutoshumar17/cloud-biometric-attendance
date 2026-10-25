import logging
from pymongo import ASCENDING, DESCENDING
from backend.database.connection import get_database

logger = logging.getLogger(__name__)

def get_students_collection():
    return get_database()['students']

def get_face_data_collection():
    return get_database()['face_data']

def get_student_embeddings_collection():
    return get_database()['student_embeddings']

def get_attendance_collection():
    return get_database()['attendance']

def get_sessions_collection():
    return get_database()['attendance_sessions']

def get_recognition_logs_collection():
    return get_database()['recognition_logs']

def setup_indexes():
    """Create all required database indexes."""
    try:
        # Students indexes
        students = get_students_collection()
        students.create_index('student_id', unique=True)
        students.create_index([('department', ASCENDING), ('section', ASCENDING)])
        
        # Face data indexes
        face_data = get_face_data_collection()
        face_data.create_index('student_id')
        face_data.create_index(
            [('student_id', ASCENDING), ('sample_index', ASCENDING)],
            unique=True
        )
        
        # Student embeddings indexes
        embeddings = get_student_embeddings_collection()
        embeddings.create_index('student_id', unique=True)
        
        # Attendance indexes
        attendance = get_attendance_collection()
        attendance.create_index(
            [('student_id', ASCENDING), ('session_id', ASCENDING)],
            unique=True
        )
        attendance.create_index('session_id')
        attendance.create_index('date')
        
        # Sessions indexes
        sessions = get_sessions_collection()
        sessions.create_index('session_id', unique=True)
        sessions.create_index('status')
        
        # Recognition logs indexes
        logs = get_recognition_logs_collection()
        logs.create_index('session_id')
        logs.create_index([('timestamp', DESCENDING)])
        
        logger.info('All database indexes created successfully')
    except Exception as e:
        logger.error(f'Error creating indexes: {e}')
        raise
