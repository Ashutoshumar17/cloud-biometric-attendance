"""Standalone test runner using standard library unittest to verify core logic."""
import os
import sys
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import io
import base64
from PIL import Image

from ml.embedder import FaceEmbedder
from ml.preprocessing import FacePreprocessor
from backend.utils.image_utils import validate_base64_image

class TestMLMathematicalProperties(unittest.TestCase):
    def test_cosine_similarity(self):
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        v3 = np.array([0.0, 1.0, 0.0])
        
        self.assertAlmostEqual(FaceEmbedder.compute_similarity(v1, v2), 1.0, places=4)
        self.assertAlmostEqual(FaceEmbedder.compute_similarity(v1, v3), 0.0, places=4)

    def test_vectorized_gallery_matching(self):
        # 512-d normalized embeddings
        g1 = np.random.randn(512)
        g1 = g1 / np.linalg.norm(g1)
        g2 = np.random.randn(512)
        g2 = g2 / np.linalg.norm(g2)
        
        gallery = np.stack([g1, g2])
        gallery_ids = ["STUDENT_A", "STUDENT_B"]
        
        # Query identical to STUDENT_B with tiny noise
        query = g2 + 0.001 * np.random.randn(512)
        query = query / np.linalg.norm(query)
        
        match = FaceEmbedder.find_best_match(query, gallery, gallery_ids)
        self.assertEqual(match["student_id"], "STUDENT_B")
        self.assertGreater(match["confidence"], 0.99)

    def test_image_validation(self):
        # Empty string should fail
        valid, _ = validate_base64_image("")
        self.assertFalse(valid)
        
        # Valid test image
        img = Image.new("RGB", (64, 64), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        valid, msg = validate_base64_image(b64)
        self.assertTrue(valid)

    def test_base64_pil_roundtrip(self):
        img = Image.new("RGB", (70, 70), color="yellow")
        b64 = FacePreprocessor.encode_image_base64(img)
        decoded = FacePreprocessor.decode_base64_image(b64)
        self.assertEqual(decoded.size, (70, 70))

if __name__ == "__main__":
    unittest.main()
