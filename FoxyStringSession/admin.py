# Authored By Foxy Bots
import tempfile
import asyncio
import logging
from datetime import timedelta, timezone
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import OWNER_ID
from FoxyStringSession.database import users
from effect import get_random_effect

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

@Client.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_handler(_, message: Message):
    total = await users.count_documents({})
    text = (
        "<blockquote><b>📊 ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ</b>\n"
        "<i>ʟɪᴠᴇ ᴜꜱᴇʀ ᴍᴇᴛʀɪᴄꜱ</i></blockquote>\n\n"
        f"<blockquote>👥 <b>ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:</b> <code>{total}</code></blockquote>"
    )
    await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        effect_id=get_random_effect()
    )

@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_handler(bot: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply(
            "<blockquote><b>❗ ᴜꜱᴀɢᴇ</b>\n<code>/broadcast &lt;message&gt;</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    text = message.text.split(None, 1)[1]
    status_msg = await message.reply(
        "<blockquote><b>🚀 ʙʀᴏᴀᴅᴄᴀꜱᴛ ꜱᴛᴀʀᴛᴇᴅ</b>\n"
        "<i>ꜱᴇɴᴅɪɴɢ ᴍᴇꜱꜱᴀɢᴇꜱ ᴛᴏ ᴜꜱᴇʀꜱ...</i></blockquote>",
        parse_mode=ParseMode.HTML
    )

    success, failed, blocked = 0, 0, 0
    total = await users.count_documents({})

    async for user in users.find({}, {"_id": 1}):
        uid = user["_id"]
        try:
            await bot.send_message(uid, text)
            success += 1
            await asyncio.sleep(0.05)  # 20 msg/sec to prevent Telegram rate limit
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            try:
                await bot.send_message(uid, text)
                success += 1
            except Exception:
                failed += 1
        except UserIsBlocked:
            blocked += 1
        except InputUserDeactivated:
            failed += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        "<blockquote><b>✅ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>\n"
        "<i>ᴍᴇꜱꜱᴀɢᴇ ᴅᴇʟɪᴠᴇʀʏ ꜱᴜᴍᴍᴀʀʏ</i></blockquote>\n\n"
        f"<blockquote>👥 <b>ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:</b> <code>{total}</code>\n"
        f"📬 <b>ᴅᴇʟɪᴠᴇʀᴇᴅ:</b> <code>{success}</code>\n"
        f"🚫 <b>ʙʟᴏᴄᴋᴇᴅ:</b> <code>{blocked}</code>\n"
        f"⚠️ <b>ꜰᴀɪʟᴇᴅ:</b> <code>{failed}</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

@Client.on_message(filters.command("users") & filters.user(OWNER_ID))
async def users_list(bot: Client, message: Message):
    lines = []
    count = 0

    async for user in users.find().sort("joined", -1):
        uid = user["_id"]
        name = user.get("name", "N/A")
        username = user.get("username", "N/A")
        joined = user.get("joined")
        if joined:
            join_time = joined.astimezone(IST)
            join_info = join_time.strftime('%d-%m-%Y %I:%M %p') + " IST"
        else:
            join_info = "Unknown"

        lines.append(f"{uid} • {name} (@{username}) — {join_info}")
        count += 1

    total = await users.count_documents({})

    if count <= 50:
        reply_text = (
            f"<blockquote><b>👥 ʀᴇɢɪꜱᴛᴇʀᴇᴅ ᴜꜱᴇʀꜱ ({total})</b>\n"
            "<i>ʟᴀᴛᴇꜱᴛ 50 ᴍᴇᴍʙᴇʀꜱ</i></blockquote>\n\n"
            + "\n".join([f"• <code>{line}</code>" for line in lines])
        )
        await message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    else:
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".txt") as file:
            file.write("\n".join(lines))
            file.seek(0)
            await message.reply_document(
                file.name,
                caption=f"<blockquote>👥 <b>ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:</b> <code>{total}</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
