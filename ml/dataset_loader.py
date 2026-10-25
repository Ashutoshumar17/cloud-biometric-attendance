"""Load training dataset from MongoDB."""
import logging
import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Optional
from ml.preprocessing import FacePreprocessor

logger = logging.getLogger(__name__)

class DatasetLoader:
    """Loads and validates face dataset from MongoDB for training."""
    
    def __init__(self):
        self.preprocessor = FacePreprocessor()
    
    def load_dataset(self, min_samples_per_student: int = 3) -> Dict:
        """
        Load all face samples from MongoDB.
        
        Returns:
            Dict with:
                - students: dict mapping student_id -> {name, department, samples: [PIL Images]}
                - total_samples: int
                - total_students: int
                - skipped_students: list of student_ids with insufficient samples
        """
        from backend.database.collections import get_face_data_collection, get_students_collection
        
        face_col = get_face_data_collection()
        students_col = get_students_collection()
        
        # Get all students
        all_students = {s['student_id']: s for s in students_col.find({'status': 'active'})}
        
        dataset = {}
        skipped = []
        total_samples = 0
        
        for student_id, student_info in all_students.items():
            # Get face samples
            samples = list(face_col.find({'student_id': student_id}).sort('sample_index', 1))
            
            if len(samples) < min_samples_per_student:
                skipped.append(student_id)
                logger.warning(f'Student {student_id} has only {len(samples)} samples (min: {min_samples_per_student}), skipping')
                continue
            
            # Decode images
            images = []
            for sample in samples:
                try:
                    img = self.preprocessor.decode_base64_image(sample['image_base64'])
                    images.append(img)
                except Exception as e:
                    logger.warning(f'Failed to decode image for {student_id} sample {sample.get("sample_index")}: {e}')
            
            if len(images) >= min_samples_per_student:
                dataset[student_id] = {
                    'name': student_info.get('name', ''),
                    'department': student_info.get('department', ''),
                    'samples': images
                }
                total_samples += len(images)
        
        logger.info(f'Dataset loaded: {len(dataset)} students, {total_samples} samples')
        return {
            'students': dataset,
            'total_samples': total_samples,
            'total_students': len(dataset),
            'skipped_students': skipped
        }
    
    def create_train_val_split(self, dataset: Dict, val_ratio: float = 0.2) -> Tuple[Dict, Dict]:
        """
        Split dataset into training and validation sets.
        
        For each student, split their samples into train/val.
        """
        train_data = {}
        val_data = {}
        
        for student_id, info in dataset['students'].items():
            samples = info['samples']
            n_val = max(1, int(len(samples) * val_ratio))
            n_train = len(samples) - n_val
            
            # Shuffle samples
            indices = np.random.permutation(len(samples))
            train_indices = indices[:n_train]
            val_indices = indices[n_train:]
            
            train_data[student_id] = {
                'name': info['name'],
                'samples': [samples[i] for i in train_indices]
            }
            val_data[student_id] = {
                'name': info['name'],
                'samples': [samples[i] for i in val_indices]
            }
        
        return train_data, val_data
    
    def get_dataset_summary(self) -> Dict:
        """Get summary statistics of the current dataset."""
        from backend.database.collections import get_face_data_collection, get_students_collection
        
        students_col = get_students_collection()
        face_col = get_face_data_collection()
        
        total_students = students_col.count_documents({'status': 'active'})
        total_samples = face_col.count_documents({})
        
        # Samples per student
        pipeline = [
            {'$group': {'_id': '$student_id', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        per_student = list(face_col.aggregate(pipeline))
        
        return {
            'total_students': total_students,
            'total_samples': total_samples,
            'samples_per_student': {r['_id']: r['count'] for r in per_student},
            'min_samples': min(r['count'] for r in per_student) if per_student else 0,
            'max_samples': max(r['count'] for r in per_student) if per_student else 0,
            'avg_samples': round(total_samples / total_students, 1) if total_students > 0 else 0
        }
