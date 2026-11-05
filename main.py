# Authored By Foxy Bots
import asyncio
import logging
from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from pyrogram.errors import ApiIdInvalid, ApiIdPublishedFlood, AccessTokenInvalid
import config
from FoxyStringSession.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pymongo").setLevel(logging.ERROR)

def main():
    print("🔧 Starting Spark Session Gen...")

    if not all([config.API_ID, config.API_HASH, config.BOT_TOKEN]):
        logging.critical("❌ ᴍɪꜱꜱɪɴɢ ᴀᴘɪ_ɪᴅ/ᴀᴘɪ_ʜᴀꜱʜ/ʙᴏᴛ_ᴛᴏᴋᴇɴ ɪɴ ᴄᴏɴꜰɪɢ.")
        return

    try:
        with Client(
            name="SparkSessionBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=ParseMode.HTML,
            in_memory=True,
            plugins=dict(root="FoxyStringSession"),
        ) as app:

            try:
                uname = app.get_me().username
                print(f"✅ ʙᴏᴛ @{uname} ɪꜱ ɴᴏᴡ ʀᴇᴀᴅʏ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ꜱᴇꜱꜱɪᴏɴꜱ.")
            except Exception as e:
                logging.error(f"❗ ꜰᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ʙᴏᴛ ɪɴꜰᴏ: {e}")
                return

            try:
                loop = asyncio.get_event_loop()
                loop.create_task(init_db())
            except Exception:
                pass

            idle()

    except ApiIdInvalid:
        logging.critical("❌ ɪɴᴠᴀʟɪᴅ ᴀᴘɪ_ɪᴅ ᴏʀ ᴀᴘɪ_ʜᴀꜱʜ. ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴄᴏɴꜰɪɢ.")
    except ApiIdPublishedFlood:
        logging.critical("🚫 ᴀᴘɪ_ɪᴅ/ʜᴀꜱʜ ᴄᴏᴍʙɪɴᴀᴛɪᴏɴ ɪꜱ ꜰʟᴏᴏᴅ-ʙᴀɴɴᴇᴅ.")
    except AccessTokenInvalid:
        logging.critical("🔐 ɪɴᴠᴀʟɪᴅ ʙᴏᴛ_ᴛᴏᴋᴇɴ. ᴘʟᴇᴀꜱᴇ ᴜᴘᴅᴀᴛᴇ ɪᴛ.")
    except Exception as e:
        logging.exception(f"❗ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴅᴜʀɪɴɢ ꜱᴛᴀʀᴛᴜᴘ: {e}")
    finally:
        print("🛑 ꜱᴇꜱꜱɪᴏɴ ɢᴇɴᴇʀᴀᴛɪᴏɴ ꜱᴛᴏᴘᴘᴇᴅ.")

if __name__ == "__main__":
    main()