# Authored By Foxy Bots
import logging
from datetime import datetime, timedelta, timezone
from FoxyStringSession.database import users

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

async def save_user(user):
    if not user:
        return
    try:
        await users.update_one(
            {"_id": user.id},
            {
                "$set": {
                    "name": user.first_name,
                    "username": user.username,
                    "is_bot": user.is_bot,
                },
                "$setOnInsert": {
                    "joined": datetime.now(IST)
                }
            },
            upsert=True
        )
    except Exception as e:
        logger.debug(f"[DB] Failed to save user {user.id} - {e}")
