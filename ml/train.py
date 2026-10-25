"""Fine-tuning pipeline with triplet loss for Face Recognition."""
import os
import logging
import time
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import Dict, List, Tuple
from facenet_pytorch import InceptionResnetV1

from ml.dataset_loader import DatasetLoader
from ml.detector import FaceDetector

logger = logging.getLogger(__name__)

class TripletFaceDataset(Dataset):
    """Dataset for generating anchor, positive, and negative face triplets."""
    
    def __init__(self, data_dict: Dict, detector: FaceDetector):
        self.data_dict = data_dict
        self.student_ids = list(data_dict.keys())
        self.detector = detector
        self.triplets = self._generate_triplets()
        
    def _generate_triplets(self) -> List[Tuple]:
        triplets = []
        for anchor_id in self.student_ids:
            samples = self.data_dict[anchor_id]['samples']
            if len(samples) < 2:
                continue
                
            for i in range(len(samples)):
                for j in range(i + 1, len(samples)):
                    anchor_img = samples[i]
                    positive_img = samples[j]
                    
                    # Choose a negative sample from a different student
                    negative_id = np.random.choice([sid for sid in self.student_ids if sid != anchor_id])
                    negative_img = np.random.choice(self.data_dict[negative_id]['samples'])
                    
                    triplets.append((anchor_img, positive_img, negative_img))
        return triplets

    def __len__(self):
        return len(self.triplets)
        
    def __getitem__(self, idx):
        a_img, p_img, n_img = self.triplets[idx]
        
        # Detect and crop faces
        a_face = self.detector.detect_single_face(a_img)
        p_face = self.detector.detect_single_face(p_img)
        n_face = self.detector.detect_single_face(n_img)
        
        # Ensure faces are tensors, return zeros if detection fails
        shape = (3, 160, 160)
        a_face = a_face if a_face is not None else torch.zeros(shape)
        p_face = p_face if p_face is not None else torch.zeros(shape)
        n_face = n_face if n_face is not None else torch.zeros(shape)
        
        return a_face, p_face, n_face

def train_model(epochs: int = 10, batch_size: int = 16, lr: float = 1e-4):
    """Run fine-tuning pipeline."""
    os.makedirs('ml/artifacts', exist_ok=True)
    logging.basicConfig(level=logging.INFO)
    
    loader = DatasetLoader()
    dataset_info = loader.load_dataset(min_samples_per_student=3)
    if dataset_info['total_students'] < 2:
        logger.error("Not enough students for triplet loss (need at least 2).")
        return
        
    train_data, val_data = loader.create_train_val_split(dataset_info)
    
    detector = FaceDetector()
    train_dataset = TripletFaceDataset(train_data, detector)
    val_dataset = TripletFaceDataset(val_data, detector)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    device = torch.device('cpu')
    model = InceptionResnetV1(pretrained='vggface2').to(device)
    
    # Freeze backbone, train last few layers
    for param in model.parameters():
        param.requires_grad = False
    for param in model.last_linear.parameters():
        param.requires_grad = True
    for param in model.last_bn.parameters():
        param.requires_grad = True
        
    criterion = nn.TripletMarginLoss(margin=1.0, p=2)
    optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)
    
    best_loss = float('inf')
    loss_history = {'train': [], 'val': []}
    
    logger.info("Starting training...")
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for a, p, n in train_loader:
            a, p, n = a.to(device), p.to(device), n.to(device)
            
            optimizer.zero_grad()
            a_out = model(a)
            p_out = model(p)
            n_out = model(n)
            
            loss = criterion(a_out, p_out, n_out)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        train_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for a, p, n in val_loader:
                a, p, n = a.to(device), p.to(device), n.to(device)
                a_out = model(a)
                p_out = model(p)
                n_out = model(n)
                loss = criterion(a_out, p_out, n_out)
                val_loss += loss.item()
        val_loss /= len(val_loader) if len(val_loader) > 0 else 1
        
        loss_history['train'].append(train_loss)
        loss_history['val'].append(val_loss)
        
        logger.info(f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save(model.state_dict(), 'ml/artifacts/best_model.pth')
            logger.info("Saved new best model.")
            
    logger.info("Training complete.")
    
    summary = {
        'epochs': epochs,
        'loss_history': loss_history,
        'model_path': 'ml/artifacts/best_model.pth',
        'best_val_loss': best_loss
    }
    with open('ml/artifacts/training_summary.json', 'w') as f:
        json.dump(summary, f, indent=4)
        
    return summary

if __name__ == "__main__":
    train_model()
