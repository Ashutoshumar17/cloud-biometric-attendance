"""ML Pipeline Configuration."""
import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class MLConfig:
    """Configuration for the ML pipeline."""
    
    # Model settings
    model_name: str = 'InceptionResnetV1'
    pretrained: str = 'vggface2'
    embedding_dim: int = 512
    input_size: int = 160
    
    # MTCNN settings
    mtcnn_image_size: int = 160
    mtcnn_margin: int = 20
    mtcnn_min_face_size: int = 20
    mtcnn_thresholds: List[float] = field(default_factory=lambda: [0.6, 0.7, 0.7])
    mtcnn_factor: float = 0.709
    
    # Recognition settings
    recognition_threshold: float = float(os.getenv('RECOGNITION_THRESHOLD', '0.65'))
    
    # Training settings
    learning_rate: float = 1e-4
    head_learning_rate: float = 1e-3
    batch_size: int = 16
    num_epochs: int = 10
    triplet_margin: float = 0.5
    train_val_split: float = 0.8
    
    # Augmentation settings
    augment_rotation: int = 15
    augment_brightness: float = 0.2
    augment_horizontal_flip: bool = True
    
    # Model versioning
    model_version: str = os.getenv('MODEL_VERSION', 'v1.0')
    
    # Paths
    artifacts_dir: str = os.path.join(os.path.dirname(__file__), 'artifacts')

ml_config = MLConfig()
