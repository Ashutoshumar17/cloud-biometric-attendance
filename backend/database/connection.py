import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_client = None
_db = None

def get_client():
    """Get or create MongoDB client (singleton)."""
    global _client
    if _client is None:
        from backend.config import settings
        try:
            _client = MongoClient(
                settings.MONGODB_URI,
                maxPoolSize=10,
                connectTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
                retryWrites=True
            )
            # Verify connection
            _client.admin.command('ping')
            logger.info('Successfully connected to MongoDB')
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f'Failed to connect to MongoDB: {e}')
            _client = None
            raise
    return _client

def get_database():
    """Get the application database."""
    global _db
    if _db is None:
        from backend.config import settings
        client = get_client()
        _db = client[settings.DATABASE_NAME]
    return _db

def check_health():
    """Check MongoDB connection health."""
    try:
        client = get_client()
        client.admin.command('ping')
        return {"status": "healthy", "message": "MongoDB connection is active"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

def close_connection():
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info('MongoDB connection closed')
