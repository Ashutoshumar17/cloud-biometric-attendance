"""Model evaluation script for face recognition."""
import os
import json
import logging
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc, classification_report, confusion_matrix

from ml.dataset_loader import DatasetLoader
from ml.detector import FaceDetector
from ml.embedder import FaceEmbedder

logger = logging.getLogger(__name__)

def evaluate_model(model_path: str = None, threshold: float = 0.65):
    """Evaluate trained model and generate metrics."""
    os.makedirs('ml/artifacts', exist_ok=True)
    logging.basicConfig(level=logging.INFO)
    
    loader = DatasetLoader()
    dataset_info = loader.load_dataset(min_samples_per_student=2)
    if dataset_info['total_students'] < 2:
        logger.error("Not enough students for evaluation.")
        return
        
    _, val_data = loader.create_train_val_split(dataset_info, val_ratio=0.5)
    
    detector = FaceDetector()
    embedder = FaceEmbedder(model_path=model_path)
    
    # Extract embeddings for val data
    embeddings = {}
    for student_id, info in val_data.items():
        embeddings[student_id] = []
        for img in info['samples']:
            face = detector.detect_single_face(img)
            if face is not None:
                emb = embedder.extract_embedding(face)
                embeddings[student_id].append(emb)
                
    # Generate pairwise similarities
    y_true = []
    y_scores = []
    
    student_ids = list(embeddings.keys())
    
    for i, sid1 in enumerate(student_ids):
        for emb1 in embeddings[sid1]:
            # Genuine pairs
            for emb2 in embeddings[sid1]:
                if not np.array_equal(emb1, emb2):
                    similarity = embedder.compute_similarity(emb1, emb2)
                    y_true.append(1)
                    y_scores.append(similarity)
            
            # Imposter pairs
            for sid2 in student_ids[i+1:]:
                for emb2 in embeddings[sid2]:
                    similarity = embedder.compute_similarity(emb1, emb2)
                    y_true.append(0)
                    y_scores.append(similarity)
                    
    if not y_true:
        logger.error("No valid pairs to evaluate.")
        return
        
    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    
    # Calculate ROC and AUC
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    
    # Calculate EER
    fnr = 1 - tpr
    eer_idx = np.nanargmin(np.absolute((fnr - fpr)))
    eer = fpr[eer_idx]
    optimal_threshold = thresholds[eer_idx]
    
    # Calculate Accuracy, FAR, FRR at configured threshold
    y_pred = (y_scores >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0,0,0,0)
    far = fp / (fp + tn) if (fp + tn) > 0 else 0
    frr = fn / (fn + tp) if (fn + tp) > 0 else 0
    accuracy = (tp + tn) / len(y_true)
    
    # Save ROC Curve
    plt.figure()
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.savefig('ml/artifacts/roc_curve.png')
    plt.close()
    
    # Save Confusion Matrix
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    plt.savefig('ml/artifacts/confusion_matrix.png')
    plt.close()
    
    report = {
        'auc': float(roc_auc),
        'eer': float(eer),
        'optimal_threshold': float(optimal_threshold),
        'accuracy_at_threshold': float(accuracy),
        'far_at_threshold': float(far),
        'frr_at_threshold': float(frr),
        'configured_threshold': float(threshold)
    }
    
    with open('ml/artifacts/evaluation_report.json', 'w') as f:
        json.dump(report, f, indent=4)
        
    logger.info(f"Evaluation Complete:\nAUC: {roc_auc:.4f}\nEER: {eer:.4f}\nAccuracy: {accuracy:.4f}")
    
    return report

if __name__ == "__main__":
    evaluate_model(threshold=0.65)
