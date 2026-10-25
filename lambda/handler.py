"""AWS Lambda entry point for serverless deployment.

Supports both:
1. API Gateway HTTP API (v2) and REST proxy requests via Mangum (ASGI adapter)
2. Direct invocation payloads for custom testing or asynchronous microservice invocations
"""
import os
import json
import base64
import logging
from mangum import Mangum

# Import the FastAPI application
from backend.app import app
from backend.services.recognition_service import recognize_face
from backend.services.attendance_service import mark_attendance
from backend.config import settings

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Mangum adapter converts AWS API Gateway events into ASGI requests for FastAPI
asgi_handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """
    AWS Lambda entry handler.
    Auto-detects API Gateway proxy events vs direct microservice JSON payloads.
    """
    # 1. API Gateway Proxy Request (HTTP API v2 or REST)
    if "requestContext" in event or "httpMethod" in event or "rawPath" in event:
        return asgi_handler(event, context)

    # 2. Direct JSON Event Invocation
    try:
        action = event.get("action", "recognize")
        
        if action == "recognize":
            image_b64 = event.get("image")
            session_id = event.get("session_id")
            
            if not image_b64:
                return {
                    "statusCode": 400,
                    "body": {"error": "Missing 'image' base64 payload"}
                }
            if not session_id:
                return {
                    "statusCode": 400,
                    "body": {"error": "Missing 'session_id' parameter"}
                }

            rec_result = recognize_face(image_b64, session_id=session_id)
            
            if not rec_result.get("success"):
                return {
                    "statusCode": 422,
                    "body": rec_result
                }

            if not rec_result.get("matched"):
                return {
                    "statusCode": 200,
                    "body": rec_result
                }

            # Mark attendance
            att_result = mark_attendance(
                student_id=rec_result["student_id"],
                name=rec_result["name"],
                confidence=rec_result["confidence"],
                session_id=session_id,
                model_version=settings.MODEL_VERSION
            )

            return {
                "statusCode": 200,
                "body": {
                    **rec_result,
                    "attendance": att_result.get("attendance"),
                    "duplicate": att_result.get("duplicate", False),
                    "attendance_message": att_result.get("message")
                }
            }

        elif action == "health":
            return {
                "statusCode": 200,
                "body": {
                    "status": "healthy",
                    "model_version": settings.MODEL_VERSION,
                    "threshold": settings.RECOGNITION_THRESHOLD
                }
            }

        else:
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown action: {action}"}
            }

    except Exception as e:
        logger.error(f"Error handling Lambda event: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }
