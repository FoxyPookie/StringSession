# Authored By Foxy
import os
from dotenv import load_dotenv

load_dotenv()

# Variables : os.getenv("VAR_NAME", "default_value")
API_ID = int(os.getenv("API_ID", "00000"))
API_HASH = os.getenv("API_HASH", "000000")
BOT_TOKEN = os.getenv("BOT_TOKEN", "000000")
OWNER_ID = int(os.getenv("OWNER_ID", "0000000"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb.net/?appName=Cluster0") or os.getenv("MONGO_DB_URI")

CHANNEL_URL = "https://t.me/FoxryHQ"
SUPPORT_GROUP_URL = "https://t.me/FoxryChat"
OWNER_URL = "https://t.me/FoxyPookie"
START_IMG_PATH = os.path.join(os.path.dirname(__file__), "assets", "start.jpg")
