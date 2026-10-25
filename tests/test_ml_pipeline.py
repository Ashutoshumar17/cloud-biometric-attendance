"""Unit tests for ML face recognition mathematical properties, preprocessing, and matching."""
import io
import base64
import numpy as np
import pytest
from PIL import Image

from ml.embedder import FaceEmbedder
from ml.preprocessing import FacePreprocessor
from backend.utils.image_utils import validate_base64_image

def test_cosine_similarity_orthogonal_and_parallel():
    """Verify mathematical properties of cosine similarity."""
    # Parallel vectors -> similarity = 1.0
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 0.0, 0.0])
    assert pytest.approx(FaceEmbedder.compute_similarity(v1, v2), 0.0001) == 1.0

    # Orthogonal vectors -> similarity = 0.0
    v3 = np.array([0.0, 1.0, 0.0])
    assert pytest.approx(FaceEmbedder.compute_similarity(v1, v3), 0.0001) == 0.0

    # Opposite vectors -> similarity = -1.0
    v4 = np.array([-1.0, 0.0, 0.0])
    assert pytest.approx(FaceEmbedder.compute_similarity(v1, v4), 0.0001) == -1.0

def test_vectorized_gallery_matching():
    """Verify 1:N gallery matching using vectorized matrix multiplication."""
    # Create normalized gallery embeddings
    g1 = np.random.randn(512)
    g1 = g1 / np.linalg.norm(g1)
    
    g2 = np.random.randn(512)
    g2 = g2 / np.linalg.norm(g2)
    
    g3 = np.random.randn(512)
    g3 = g3 / np.linalg.norm(g3)

    gallery = np.stack([g1, g2, g3])
    gallery_ids = ["STU_001", "STU_002", "STU_003"]

    # Query identical to STU_002 with small perturbation
    query = g2.copy() + 0.01 * np.random.randn(512)
    query = query / np.linalg.norm(query)

    result = FaceEmbedder.find_best_match(query, gallery, gallery_ids)
    assert result["student_id"] == "STU_002"
    assert result["confidence"] > 0.95

def test_image_validation_empty_and_valid():
    """Test image validation logic."""
    # Empty string
    valid, msg = validate_base64_image("")
    assert not valid

    # Create dummy 100x100 RGB image
    img = Image.new("RGB", (100, 100), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

    valid, msg = validate_base64_image(b64_str)
    assert valid
    assert msg == ""

def test_decode_base64_to_pil():
    """Test base64 to PIL image decoding."""
    img = Image.new("RGB", (80, 80), color="green")
    b64 = FacePreprocessor.encode_image_base64(img)
    decoded = FacePreprocessor.decode_base64_image(b64)
    assert decoded.size == (80, 80)
