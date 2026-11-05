# Authored By Foxy Bots
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

logger = logging.getLogger(__name__)

# Performance-tuned Motor Client with connection pooling and fast failover
mongo = AsyncIOMotorClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    maxPoolSize=50,
    minPoolSize=5,
    retryWrites=True,
)
db = mongo.notty_string_session
users = db.users

async def init_db():
    """Ensure indexes for rapid querying in /stats, /users, and user saves."""
    try:
        await users.create_index("joined", background=True)
        await users.create_index("username", background=True)
        logger.info("MongoDB indexes verified.")
    except Exception as e:
        logger.warning(f"Could not initialize MongoDB index: {e}")
