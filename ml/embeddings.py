"""Batch face embedding generation and MongoDB storage."""
import logging
import time
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

def generate_embeddings_for_all_students() -> Dict:
    """
    Generate and store averaged face embeddings for all registered students.
    
    Pipeline:
    1. Load all face samples from MongoDB
    2. For each student:
       a. Detect face in each sample
       b. Extract 512-d embedding for each face
       c. Average all embeddings
       d. L2-normalize the averaged embedding
       e. Store in student_embeddings collection
    3. Update student records (embedding_generated = True)
    
    Returns:
        Summary dict with processing results
    """
    from ml.detector import FaceDetector
    from ml.embedder import FaceEmbedder
    from ml.preprocessing import FacePreprocessor
    from ml.config import ml_config
    from backend.database.collections import (
        get_face_data_collection, 
        get_students_collection,
        get_student_embeddings_collection
    )
    
    start_time = time.time()
    
    detector = FaceDetector()
    embedder = FaceEmbedder()
    preprocessor = FacePreprocessor()
    
    students_col = get_students_collection()
    face_col = get_face_data_collection()
    embeddings_col = get_student_embeddings_collection()
    
    # Get all active students
    students = list(students_col.find({'status': 'active'}))
    
    results = {
        'total_students': len(students),
        'processed': 0,
        'skipped': 0,
        'errors': [],
        'details': []
    }
    
    for student in students:
        student_id = student['student_id']
        student_name = student.get('name', '')
        
        try:
            # Get face samples
            samples = list(face_col.find({'student_id': student_id}))
            
            if not samples:
                results['skipped'] += 1
                results['details'].append({
                    'student_id': student_id,
                    'status': 'skipped',
                    'reason': 'No face samples found'
                })
                continue
            
            # Extract embeddings for each sample
            embeddings = []
            for sample in samples:
                try:
                    # Decode image
                    image = preprocessor.decode_base64_image(sample['image_base64'])
                    
                    # Detect single face
                    face_tensor = detector.detect_single_face(image)
                    
                    if face_tensor is not None:
                        # Extract embedding
                        embedding = embedder.extract_embedding(face_tensor)
                        embeddings.append(embedding)
                        
                        # Also store individual embedding in face_data
                        face_col.update_one(
                            {'_id': sample['_id']},
                            {'$set': {
                                'embedding': embedding.tolist(),
                                'face_detected': True,
                                'preprocessed': True
                            }}
                        )
                    else:
                        face_col.update_one(
                            {'_id': sample['_id']},
                            {'$set': {'face_detected': False}}
                        )
                        logger.warning(f'No face detected in sample for {student_id}')
                except Exception as e:
                    logger.warning(f'Error processing sample for {student_id}: {e}')
            
            if not embeddings:
                results['skipped'] += 1
                results['details'].append({
                    'student_id': student_id,
                    'status': 'skipped',
                    'reason': 'No valid faces detected in any sample'
                })
                continue
            
            # Average all embeddings
            avg_embedding = np.mean(embeddings, axis=0)
            # L2-normalize the averaged embedding
            avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
            
            # Store in student_embeddings collection (upsert)
            embeddings_col.update_one(
                {'student_id': student_id},
                {'$set': {
                    'student_id': student_id,
                    'name': student_name,
                    'embedding': avg_embedding.tolist(),
                    'num_samples': len(embeddings),
                    'model_version': ml_config.model_version,
                    'generated_at': datetime.now(timezone.utc)
                }},
                upsert=True
            )
            
            # Update student record
            students_col.update_one(
                {'student_id': student_id},
                {'$set': {
                    'embedding_generated': True,
                    'updated_at': datetime.now(timezone.utc)
                }}
            )
            
            results['processed'] += 1
            results['details'].append({
                'student_id': student_id,
                'status': 'success',
                'num_samples_used': len(embeddings),
                'total_samples': len(samples)
            })
            
            logger.info(f'Generated embedding for {student_id} using {len(embeddings)}/{len(samples)} samples')
            
        except Exception as e:
            results['errors'].append({'student_id': student_id, 'error': str(e)})
            logger.error(f'Error generating embedding for {student_id}: {e}')
    
    results['processing_time_seconds'] = round(time.time() - start_time, 2)
    results['model_version'] = ml_config.model_version
    
    logger.info(f'Embedding generation complete: {results["processed"]}/{results["total_students"]} students processed in {results["processing_time_seconds"]}s')
    
    return results


def generate_embedding_for_student(student_id: str) -> Dict:
    """Generate embedding for a single student. Same logic as batch but for one student."""
    from ml.detector import FaceDetector
    from ml.embedder import FaceEmbedder  
    from ml.preprocessing import FacePreprocessor
    from ml.config import ml_config
    from backend.database.collections import (
        get_face_data_collection,
        get_students_collection, 
        get_student_embeddings_collection
    )
    
    detector = FaceDetector()
    embedder = FaceEmbedder()
    preprocessor = FacePreprocessor()
    
    students_col = get_students_collection()
    face_col = get_face_data_collection()
    embeddings_col = get_student_embeddings_collection()
    
    student = students_col.find_one({'student_id': student_id})
    if not student:
        return {'success': False, 'error': f'Student {student_id} not found'}
    
    samples = list(face_col.find({'student_id': student_id}))
    if not samples:
        return {'success': False, 'error': f'No face samples found for {student_id}'}
    
    embeddings = []
    for sample in samples:
        try:
            image = preprocessor.decode_base64_image(sample['image_base64'])
            face_tensor = detector.detect_single_face(image)
            if face_tensor is not None:
                embedding = embedder.extract_embedding(face_tensor)
                embeddings.append(embedding)
        except Exception as e:
            logger.warning(f'Error processing sample: {e}')
    
    if not embeddings:
        return {'success': False, 'error': 'No valid faces detected'}
    
    avg_embedding = np.mean(embeddings, axis=0)
    avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
    
    embeddings_col.update_one(
        {'student_id': student_id},
        {'$set': {
            'student_id': student_id,
            'name': student.get('name', ''),
            'embedding': avg_embedding.tolist(),
            'num_samples': len(embeddings),
            'model_version': ml_config.model_version,
            'generated_at': datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    students_col.update_one(
        {'student_id': student_id},
        {'$set': {'embedding_generated': True, 'updated_at': datetime.now(timezone.utc)}}
    )
    
    return {
        'success': True,
        'student_id': student_id,
        'num_samples_used': len(embeddings),
        'model_version': ml_config.model_version
    }
