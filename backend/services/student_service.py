import logging
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from backend.database.collections import (
    get_students_collection,
    get_face_data_collection,
    get_student_embeddings_collection
)

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

def register_student(data: dict) -> dict:
    """
    Register a new student.
    Validates required fields, checks for duplicates, and initializes metadata.
    """
    required_fields = ['student_id', 'name', 'department', 'semester', 'section']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
            
    student_data = data.copy()
    student_data.update({
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'status': 'active',
        'face_samples_count': 0,
        'embedding_generated': False
    })
    
    students_coll = get_students_collection()
    
    try:
        result = students_coll.insert_one(student_data)
        student_data['_id'] = result.inserted_id
        return _serialize_doc(student_data)
    except DuplicateKeyError:
        raise ValueError(f"Student with ID {data['student_id']} already exists")
    except Exception as e:
        logger.error(f"Error registering student: {e}")
        raise

def get_student(student_id: str) -> dict:
    """
    Retrieve a student by their student_id.
    """
    students_coll = get_students_collection()
    student = students_coll.find_one({'student_id': student_id})
    return _serialize_doc(student)

def get_all_students(department=None, section=None) -> list:
    """
    Retrieve all students, optionally filtered by department and section.
    """
    students_coll = get_students_collection()
    query = {}
    if department:
        query['department'] = department
    if section:
        query['section'] = section
        
    students = list(students_coll.find(query))
    return [_serialize_doc(student) for student in students]

def update_student(student_id: str, data: dict) -> dict:
    """
    Update an existing student's information.
    """
    students_coll = get_students_collection()
    
    update_data = data.copy()
    update_data.pop('_id', None)
    update_data.pop('student_id', None)  # Prevent changing student_id
    update_data['updated_at'] = datetime.now(timezone.utc)
    
    result = students_coll.find_one_and_update(
        {'student_id': student_id},
        {'$set': update_data},
        return_document=True
    )
    
    if not result:
        raise ValueError(f"Student with ID {student_id} not found")
        
    return _serialize_doc(result)

def delete_student(student_id: str) -> bool:
    """
    Delete a student and their associated face data and embeddings.
    """
    try:
        students_coll = get_students_collection()
        face_data_coll = get_face_data_collection()
        embeddings_coll = get_student_embeddings_collection()
        
        # Delete from students collection
        result = students_coll.delete_one({'student_id': student_id})
        
        if result.deleted_count > 0:
            # Delete associated data
            face_data_coll.delete_many({'student_id': student_id})
            embeddings_coll.delete_one({'student_id': student_id})
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {e}")
        raise

def add_face_sample(student_id: str, image_base64: str, sample_index: int, pose: str = 'front') -> dict:
    """
    Add a face sample image for a student and increment their face_samples_count.
    """
    students_coll = get_students_collection()
    face_data_coll = get_face_data_collection()
    
    # Check if student exists
    student = students_coll.find_one({'student_id': student_id})
    if not student:
        raise ValueError(f"Student with ID {student_id} not found")
        
    sample_data = {
        'student_id': student_id,
        'image_base64': image_base64,
        'sample_index': sample_index,
        'pose': pose,
        'created_at': datetime.now(timezone.utc)
    }
    
    try:
        # Insert face data
        result = face_data_coll.insert_one(sample_data)
        sample_data['_id'] = result.inserted_id
        
        # Update student count
        students_coll.update_one(
            {'student_id': student_id},
            {
                '$inc': {'face_samples_count': 1},
                '$set': {'updated_at': datetime.now(timezone.utc)}
            }
        )
        
        return _serialize_doc(sample_data)
    except DuplicateKeyError:
        raise ValueError(f"Sample index {sample_index} already exists for student {student_id}")
    except Exception as e:
        logger.error(f"Error adding face sample for student {student_id}: {e}")
        raise

def get_face_samples(student_id: str) -> list:
    """
    Retrieve all face samples for a student.
    """
    face_data_coll = get_face_data_collection()
    samples = list(face_data_coll.find({'student_id': student_id}).sort('sample_index', 1))
    return [_serialize_doc(sample) for sample in samples]

def get_student_count() -> int:
    """
    Get the total number of registered students.
    """
    students_coll = get_students_collection()
    return students_coll.count_documents({})
