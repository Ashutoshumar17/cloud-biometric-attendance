"""FastAPI main application entry point for Cloud-Based Smart Attendance System."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.config import settings
from backend.database.connection import check_health, close_connection
from backend.database.collections import setup_indexes
from backend.routes import students, recognition, attendance, dashboard

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("smart_attendance")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting Cloud-Based Smart Attendance System...")
    try:
        setup_indexes()
        logger.info("MongoDB collections and indexes initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning (Atlas connection will retry on first request): {e}")
    yield
    logger.info("Shutting down Smart Attendance System...")
    close_connection()
    logger.info("Database connections closed.")

app = FastAPI(
    title="Cloud-Based Smart Attendance System API",
    description="REST API orchestrating custom ML Face Recognition, AWS Serverless inference, and MongoDB Atlas storage.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(students.router)
app.include_router(recognition.router)
app.include_router(attendance.router)
app.include_router(dashboard.router)

# Mount frontend static files for unified single-server deployment/demo
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/registration", include_in_schema=False)
    def serve_registration():
        return FileResponse(os.path.join(frontend_dir, "registration.html"))

    @app.get("/attendance", include_in_schema=False)
    def serve_attendance():
        return FileResponse(os.path.join(frontend_dir, "attendance.html"))

    @app.get("/dashboard", include_in_schema=False)
    def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "dashboard.html"))

@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint validating API status and MongoDB connectivity."""
    db_health = check_health()
    return {
        "status": "healthy" if db_health.get("status") == "healthy" else "degraded",
        "version": "1.0.0",
        "model_name": "FaceNet (InceptionResnetV1)",
        "model_version": settings.MODEL_VERSION,
        "recognition_threshold": settings.RECOGNITION_THRESHOLD,
        "database": db_health
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
