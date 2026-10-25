"""Image utility functions for validation, decoding and conversion."""
import io
import base64
import logging
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {'JPEG', 'JPG', 'PNG', 'BMP', 'WEBP'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

def validate_base64_image(base64_string: str) -> Tuple[bool, str]:
    """
    Validate base64 image data.
    Checks data size (<10MB) and decodability into supported image formats.
    """
    try:
        if not base64_string:
            return False, "Image data cannot be empty"

        raw = base64_string
        if ',' in raw:
            raw = raw.split(',', 1)[1]

        image_bytes = base64.b64decode(raw)
        if len(image_bytes) > MAX_IMAGE_SIZE:
            return False, f"Image exceeds maximum size of {MAX_IMAGE_SIZE // (1024 * 1024)} MB"

        image = Image.open(io.BytesIO(image_bytes))
        image.verify()  # Verify integrity
        
        # Re-open after verify() as verify() corrupts internal state
        image = Image.open(io.BytesIO(image_bytes))
        fmt = image.format.upper() if image.format else 'UNKNOWN'
        if fmt not in SUPPORTED_FORMATS:
            return False, f"Unsupported image format: {fmt}. Supported formats: {', '.join(SUPPORTED_FORMATS)}"

        if image.size[0] < 50 or image.size[1] < 50:
            return False, "Image is too small (minimum 50x50 pixels required)"

        return True, ""
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False, f"Invalid image payload: {str(e)}"

def decode_base64_to_bytes(base64_string: str) -> bytes:
    """Strip data URI prefix if present and return raw image bytes."""
    raw = base64_string
    if ',' in raw:
        raw = raw.split(',', 1)[1]
    return base64.b64decode(raw)

def decode_base64_to_pil(base64_string: str) -> Image.Image:
    """Decode base64 string to RGB PIL Image."""
    image_bytes = decode_base64_to_bytes(base64_string)
    return Image.open(io.BytesIO(image_bytes)).convert('RGB')
