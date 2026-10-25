"""Standardized API response helper functions."""
from typing import Any, Optional
from fastapi.responses import JSONResponse

def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> JSONResponse:
    """Standardized success response structure."""
    payload = {
        "success": True,
        "message": message
    }
    if data is not None:
        payload["data"] = data
    return JSONResponse(status_code=status_code, content=payload)

def error_response(message: str = "Error", status_code: int = 400, details: Optional[Any] = None) -> JSONResponse:
    """Standardized error response structure."""
    payload = {
        "success": False,
        "error": message
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)
