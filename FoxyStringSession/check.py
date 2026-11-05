# Authored By Foxy Bots
import time
import base64
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
)
from pyrogram.errors import (
    AuthKeyUnregistered, UserDeactivated, SessionRevoked, SessionExpired, MessageNotModified
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyUnregisteredError, UserDeactivatedError, SessionRevokedError, SessionExpiredError
)

import config
from FoxyStringSession.fsub import is_subscribed, FSUB_KEYBOARD, FSUB_TEXT
from FoxyStringSession.generate import ask_or_cancel, safe_close_client, GEN_BUTTON

logger = logging.getLogger(__name__)

CHECK_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ ᴀɴᴏᴛʜᴇʀ", callback_data="check_session", style=ButtonStyle.PRIMARY),
        InlineKeyboardButton("⚙️ ɢᴇɴᴇʀᴀᴛᴇ ɴᴇᴡ", callback_data="generate", style=ButtonStyle.SUCCESS),
    ],
    [
        InlineKeyboardButton("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back_to_start", style=ButtonStyle.DANGER),
    ]
])

def mask_phone(phone: str | None) -> str:
    """Masks phone number for privacy, showing prefix and suffix."""
    if not phone:
        return "None"
    p = str(phone).strip()
    if not p.startswith("+"):
        p = "+" + p
    if len(p) >= 10:
        return p[:5] + "*" * (len(p) - 7) + p[-2:]
    return p[:3] + "***"

async def _test_telethon(session_str: str) -> dict:
    """Tests a Telethon string session."""
    client = None
    try:
        ts = StringSession(session_str)
        if not ts.auth_key:
            return {"status": "invalid", "error": "Not a valid Telethon auth key."}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}

    try:
        client = TelegramClient(ts, config.API_ID, config.API_HASH)
        await asyncio.wait_for(client.connect(), timeout=10)

        if not await client.is_user_authorized():
            return {"status": "revoked", "library": "Telethon"}

        me = await asyncio.wait_for(client.get_me(), timeout=10)

        has_2fa = None
        try:
            from telethon.tl.functions.account import GetPasswordRequest
            pwd = await client(GetPasswordRequest())
            has_2fa = bool(pwd.has_password)
        except Exception:
            pass

        dc_id = client.session.dc_id

        first_name = getattr(me, "first_name", "") or ""
        last_name = getattr(me, "last_name", "") or ""
        full_name = f"{first_name} {last_name}".strip() or "Telegram User"

        return {
            "status": "active",
            "library": "Telethon",
            "id": me.id,
            "full_name": full_name,
            "username": getattr(me, "username", None),
            "phone_number": getattr(me, "phone", None),
            "is_bot": bool(getattr(me, "bot", False)),
            "is_premium": bool(getattr(me, "premium", False)),
            "dc_id": dc_id,
            "has_2fa": has_2fa,
        }
    except (AuthKeyUnregisteredError, SessionRevokedError, SessionExpiredError):
        return {"status": "revoked", "library": "Telethon"}
    except UserDeactivatedError:
        return {"status": "deactivated", "library": "Telethon"}
    except Exception as e:
        logger.debug(f"Telethon test error: {e}")
        return {"status": "invalid", "error": str(e)}
    finally:
        await safe_close_client(client, is_telethon=True)

async def _test_pyrogram(session_str: str, test_id: int) -> dict:
    """Tests a Pyrogram v1 or v2 string session."""
    client = None
    lib_name = "Pyrogram"
    try:
        decoded = base64.urlsafe_b64decode(session_str + "=" * (-len(session_str) % 4))
        if len(decoded) in (263, 267):
            lib_name = "Pyrogram v1"
        elif len(decoded) == 271:
            lib_name = "Pyrogram v2"
        else:
            lib_name = "Pyrogram"
    except Exception:
        return {"status": "invalid", "error": "Not a valid base64 Pyrogram session."}

    try:
        client = Client(
            f":memory:chk_{test_id}_{int(time.time())}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_str,
            in_memory=True
        )
        await asyncio.wait_for(client.connect(), timeout=10)
        me = await asyncio.wait_for(client.get_me(), timeout=10)

        has_2fa = None
        try:
            from pyrogram.raw.functions.account import GetPassword
            pwd = await client.invoke(GetPassword())
            has_2fa = bool(pwd.has_password)
        except Exception:
            pass

        try:
            dc_id = await client.storage.dc_id()
        except Exception:
            dc_id = getattr(me, "dc_id", 1)

        first_name = getattr(me, "first_name", "") or ""
        last_name = getattr(me, "last_name", "") or ""
        full_name = f"{first_name} {last_name}".strip() or "Telegram User"

        return {
            "status": "active",
            "library": lib_name,
            "id": me.id,
            "full_name": full_name,
            "username": me.username,
            "phone_number": me.phone_number,
            "is_bot": bool(me.is_bot),
            "is_premium": bool(getattr(me, "is_premium", False)),
            "dc_id": dc_id,
            "has_2fa": has_2fa,
        }
    except (AuthKeyUnregistered, SessionRevoked, SessionExpired):
        return {"status": "revoked", "library": lib_name}
    except UserDeactivated:
        return {"status": "deactivated", "library": lib_name}
    except Exception as e:
        logger.debug(f"Pyrogram test error: {e}")
        return {"status": "invalid", "error": str(e)}
    finally:
        await safe_close_client(client, is_telethon=False)

async def test_session(session_str: str, test_id: int) -> dict:
    """Dispatches session string testing to Telethon or Pyrogram."""
    session_str = session_str.strip()
    if len(session_str) < 100:
        return {"status": "invalid", "error": "Session string is too short or malformed."}

    # Heuristic 1: If string starts with '1' and has length around 353, try Telethon first
    if session_str.startswith("1") and len(session_str) in range(320, 390):
        res = await _test_telethon(session_str)
        if res.get("status") in ("active", "revoked", "deactivated"):
            return res

    # Heuristic 2: Try Pyrogram
    res = await _test_pyrogram(session_str, test_id)
    if res.get("status") in ("active", "revoked", "deactivated"):
        return res

    # Heuristic 3: Fallback to Telethon if Pyrogram failed
    if not (session_str.startswith("1") and len(session_str) in range(320, 390)):
        res_tel = await _test_telethon(session_str)
        if res_tel.get("status") in ("active", "revoked", "deactivated"):
            return res_tel

    return res

def format_check_result(info: dict) -> str:
    """Formats verification report into clean English blockquotes."""
    status = info.get("status")

    if status == "active":
        two_fa = (
            "✅ <i>Enabled</i>" if info.get("has_2fa") is True else
            ("⚠️ <i>Disabled</i>" if info.get("has_2fa") is False else "<i>Unknown</i>")
        )
        prem = "⭐️ <i>Yes</i>" if info.get("is_premium") else "<i>No</i>"
        acct_type = "🤖 <i>Bot Account</i>" if info.get("is_bot") else "👤 <i>User Account</i>"
        uname = f"@{info['username']}" if info.get("username") else "<i>None</i>"
        phone = mask_phone(info.get("phone_number"))

        return (
            "<blockquote><b>🔍 ꜱᴇꜱꜱɪᴏɴ ᴄʜᴇᴄᴋ ʀᴇꜱᴜʟᴛ</b>\n"
            "<i>ꜱᴛᴀᴛᴜꜱ:</i> <b>✅ ᴀᴄᴛɪᴠᴇ / ᴀʟɪᴠᴇ</b></blockquote>\n\n"
            f"<blockquote>👤 <b>ɴᴀᴍᴇ:</b> {info['full_name']}\n"
            f"🆔 <b>ᴜꜱᴇʀ ɪᴅ:</b> <code>{info['id']}</code>\n"
            f"🏷️ <b>ᴜꜱᴇʀɴᴀᴍᴇ:</b> {uname}\n"
            f"📱 <b>ᴘʜᴏɴᴇ:</b> <code>{phone}</code>\n"
            f"💎 <b>ᴘʀᴇᴍɪᴜᴍ:</b> {prem}\n"
            f"🔐 <b>2-ꜱᴛᴇᴘ (2ꜰᴀ):</b> {two_fa}\n"
            f"🤖 <b>ᴛʏᴘᴇ:</b> {acct_type}\n"
            f"🌐 <b>ᴅᴀᴛᴀ ᴄᴇɴᴛᴇʀ:</b> <code>DC{info.get('dc_id', 1)}</code>\n"
            f"📦 <b>ʟɪʙʀᴀʀʏ:</b> <code>{info.get('library', 'Unknown')}</code></blockquote>\n\n"
            "🛡️ <i>Session verified safely in-memory without saving.</i>"
        )

    elif status == "revoked":
        lib = info.get("library", "Unknown")
        return (
            "<blockquote><b>🔍 ꜱᴇꜱꜱɪᴏɴ ᴄʜᴇᴄᴋ ʀᴇꜱᴜʟᴛ</b>\n"
            "<i>ꜱᴛᴀᴛᴜꜱ:</i> <b>❌ ᴇxᴘɪʀᴇᴅ / ᴛᴇʀᴍɪɴᴀᴛᴇᴅ</b></blockquote>\n\n"
            f"<blockquote>📦 <b>ʟɪʙʀᴀʀʏ:</b> <code>{lib}</code>\n"
            "⚠️ <b>ᴅᴇᴛᴀɪʟꜱ:</b> <i>This session has been terminated from Telegram settings or revoked.</i></blockquote>"
        )

    elif status == "deactivated":
        lib = info.get("library", "Unknown")
        return (
            "<blockquote><b>🔍 ꜱᴇꜱꜱɪᴏɴ ᴄʜᴇᴄᴋ ʀᴇꜱᴜʟᴛ</b>\n"
            "<i>ꜱᴛᴀᴛᴜꜱ:</i> <b>🚫 ᴜꜱᴇʀ ᴅᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ</b></blockquote>\n\n"
            f"<blockquote>📦 <b>ʟɪʙʀᴀʀʏ:</b> <code>{lib}</code>\n"
            "⚠️ <b>ᴅᴇᴛᴀɪʟꜱ:</b> <i>The Telegram account associated with this session is deleted.</i></blockquote>"
        )

    else:
        return (
            "<blockquote><b>🔍 ꜱᴇꜱꜱɪᴏɴ ᴄʜᴇᴄᴋ ʀᴇꜱᴜʟᴛ</b>\n"
            "<i>ꜱᴛᴀᴛᴜꜱ:</i> <b>⚠️ ɪɴᴠᴀʟɪᴅ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ</b></blockquote>\n\n"
            "<blockquote>❌ <b>ᴅᴇᴛᴀɪʟꜱ:</b> <i>Not a recognized Pyrogram or Telethon session string.</i></blockquote>"
        )

async def handle_session_verification(bot: Client, user_id: int, session_str: str, reply_to_msg_id: int | None = None):
    """Executes verification and sends formatted response."""
    status_msg = await bot.send_message(
        user_id,
        "<blockquote><b>🔍 ᴠᴇʀɪꜰʏɪɴɢ ꜱᴇꜱꜱɪᴏɴ...</b>\n<i>ᴄʜᴇᴄᴋɪɴɢ ᴄᴏɴɴᴇᴄᴛɪᴏɴ ᴛᴏ ᴛᴇʟᴇɢʀᴀᴍ...</i></blockquote>",
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_msg_id,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

    info = await test_session(session_str, user_id)
    result_text = format_check_result(info)

    await status_msg.edit_text(
        result_text,
        parse_mode=ParseMode.HTML,
        reply_markup=CHECK_BUTTONS,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

@Client.on_message(filters.private & filters.command(["check", "checksession", "test", "verify"]))
async def cmd_check(bot: Client, message: Message):
    user = message.from_user
    logger.info(f"🔍 /check command from user: {user.id if user else 'Unknown'} (@{getattr(user, 'username', 'none')})")
    if not await is_subscribed(bot, user.id):
        from FoxyStringSession.fsub import send_fsub_prompt
        return await send_fsub_prompt(bot, message, user)

    # If session provided in command argument: /check <string>
    if len(message.command) > 1:
        session_str = message.text.split(None, 1)[1].strip()
        # Immediately delete the secret string for privacy
        try:
            await message.delete()
        except Exception:
            pass
        return await handle_session_verification(bot, user.id, session_str)

    # Otherwise ask user to send session
    prompt = (
        "<blockquote><b>🔍 ᴄʜᴇᴄᴋ ꜱᴛʀɪɴɢ ꜱᴇꜱꜱɪᴏɴ</b>\n"
        "<i>ᴘʟᴇᴀꜱᴇ ꜱᴇɴᴅ ʏᴏᴜʀ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ ᴛᴏ ᴠᴇʀɪꜰʏ:</i></blockquote>\n\n"
        "🛡️ <i>Your message will be auto-deleted for privacy.</i>\n\n"
        "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
    )

    try:
        session_txt, m_sess = await ask_or_cancel(
            bot, user.id, prompt,
            reply_to_message_id=message.id
        )
        if session_txt is None:
            return

        # Delete user's string message for privacy
        if m_sess:
            try:
                await m_sess.delete()
            except Exception:
                pass

        await handle_session_verification(bot, user.id, session_txt, reply_to_msg_id=message.id)
    except TimeoutError as te:
        await bot.send_message(
            user.id, str(te),
            parse_mode=ParseMode.HTML,
            reply_markup=CHECK_BUTTONS,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

@Client.on_callback_query(filters.regex(r"^check_session$"))
async def callback_check_session(bot: Client, cq: CallbackQuery):
    user = cq.from_user
    logger.info(f"🔘 Callback 'check_session' from user: {user.id if user else 'Unknown'} (@{getattr(user, 'username', 'none')})")
    if not await is_subscribed(bot, user.id):
        await cq.answer("⚠️ ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ @SparkDevBotz ꜰɪʀꜱᴛ!", show_alert=True)
        text = FSUB_TEXT.format(mention=user.mention)
        if cq.message.photo:
            try:
                return await cq.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=FSUB_KEYBOARD)
            except MessageNotModified:
                return
        else:
            try:
                return await cq.edit_message_text(text=text, parse_mode=ParseMode.HTML, reply_markup=FSUB_KEYBOARD)
            except MessageNotModified:
                return

    await cq.answer()

    prompt = (
        "<blockquote><b>🔍 ᴄʜᴇᴄᴋ ꜱᴛʀɪɴɢ ꜱᴇꜱꜱɪᴏɴ</b>\n"
        "<i>ᴘʟᴇᴀꜱᴇ ꜱᴇɴᴅ ʏᴏᴜʀ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ ᴛᴏ ᴠᴇʀɪꜰʏ:</i></blockquote>\n\n"
        "🛡️ <i>Your message will be auto-deleted for privacy.</i>\n\n"
        "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
    )

    try:
        session_txt, m_sess = await ask_or_cancel(
            bot, user.id, prompt,
            reply_to_message_id=cq.message.id
        )
        if session_txt is None:
            return

        # Auto-delete user's secret string message
        if m_sess:
            try:
                await m_sess.delete()
            except Exception:
                pass

        await handle_session_verification(bot, user.id, session_txt, reply_to_msg_id=cq.message.id)
    except TimeoutError as te:
        await bot.send_message(
            user.id, str(te),
            parse_mode=ParseMode.HTML,
            reply_markup=CHECK_BUTTONS,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
