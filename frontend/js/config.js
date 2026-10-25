/**
 * Application Configuration
 * Central configuration for API endpoints and settings.
 */
const CONFIG = {
    // API Base URL - includes /api prefix matching FastAPI routers
    API_BASE_URL: 'http://3.7.55.180:8000/api',
    
    
    // Webcam settings
    CAMERA: {
        WIDTH: 640,
        HEIGHT: 480,
        FACING_MODE: 'user',
        IMAGE_QUALITY: 0.92,
        IMAGE_FORMAT: 'image/jpeg'
    },
    
    // Auto-capture interval (ms) for attendance mode
    AUTO_CAPTURE_INTERVAL: 3000,
    
    // Recognition display timeout (ms)
    RESULT_DISPLAY_TIMEOUT: 5000,
    
    // Maximum face samples per student
    MAX_FACE_SAMPLES: 20,
    
    // Minimum face samples for registration
    MIN_FACE_SAMPLES: 5
};
