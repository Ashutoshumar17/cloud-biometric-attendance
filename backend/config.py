import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGODB_URI: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    DATABASE_NAME: str = os.getenv('DATABASE_NAME', 'smart_attendance')
    RECOGNITION_THRESHOLD: float = float(os.getenv('RECOGNITION_THRESHOLD', '0.65'))
    MODEL_VERSION: str = os.getenv('MODEL_VERSION', 'v1.0')
    BACKEND_HOST: str = os.getenv('BACKEND_HOST', '0.0.0.0')
    BACKEND_PORT: int = int(os.getenv('BACKEND_PORT', '8000'))
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500').split(',')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

settings = Settings()
