# Authored By Foxy Bots
import os
import config

_cached_photo_file_id = None

def get_start_photo():
    """Returns cached file_id if available, otherwise the local image path."""
    global _cached_photo_file_id
    if _cached_photo_file_id:
        return _cached_photo_file_id
    if os.path.exists(config.START_IMG_PATH):
        return config.START_IMG_PATH
    return None

def update_photo_file_id(message):
    """Caches Telegram's photo file_id from a sent message to avoid re-uploading."""
    global _cached_photo_file_id
    if message and getattr(message, "photo", None):
        _cached_photo_file_id = message.photo.file_id
