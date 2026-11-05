# Authored By Foxy Bots
import os
import re
import json
import logging
import asyncio
from datetime import datetime, timezone
from asyncio.exceptions import TimeoutError

import config
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telethon import TelegramClient
from telethon.sessions import StringSession
from FoxyStringSession.utils import ask, cancel_pending
from effect import get_random_effect

from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneNumberBanned, PhoneNumberFlood,
    PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid,
    AccessTokenInvalid, AccessTokenExpired, FloodWait
)
from telethon.errors import (
    ApiIdInvalidError, PhoneNumberInvalidError, PhoneNumberBannedError, PhoneNumberFloodError,
    PhoneCodeInvalidError, PhoneCodeExpiredError, SessionPasswordNeededError, PasswordHashInvalidError,
    AccessTokenInvalidError, AccessTokenExpiredError, FloodWaitError, AuthRestartError
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

os.makedirs("StringsHolder", exist_ok=True)

# Tracks active user IDs currently generating a session to prevent race conditions
active_users: set[int] = set()

ASK_QUES = (
    "<blockquote><b>☞︎︎︎ ꜱᴇʟᴇᴄᴛ ꜱᴇꜱꜱɪᴏɴ ᴛʏᴘᴇ</b>\n"
    "<i>ᴄʜᴏᴏꜱᴇ ᴛʜᴇ ʟɪʙʀᴀʀʏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ</i></blockquote>\n\n"
    "<b>👇 ᴄʜᴏᴏꜱᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ:</b>"
)

BUTTONS_QUES = [
    [
        InlineKeyboardButton("ᴘʏʀᴏɢʀᴀᴍ ᴠ1", callback_data="pyrogram_v1", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton("ᴘʏʀᴏɢʀᴀᴍ ᴠ2", callback_data="pyrogram_v2", style=ButtonStyle.SUCCESS),
    ],
    [InlineKeyboardButton("ᴛᴇʟᴇᴛʜᴏɴ", callback_data="telethon", style=ButtonStyle.DANGER)],
    [
        InlineKeyboardButton("ᴘʏʀᴏɢʀᴀᴍ ʙᴏᴛ", callback_data="pyrogram_bot", style=ButtonStyle.PRIMARY),
        InlineKeyboardButton("ᴛᴇʟᴇᴛʜᴏɴ ʙᴏᴛ", callback_data="telethon_bot", style=ButtonStyle.PRIMARY),
    ],
    [
        InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_to_start", style=ButtonStyle.DANGER),
    ]
]
GEN_BUTTON = [[InlineKeyboardButton("⚙️ ɢᴇɴᴇʀᴀᴛᴇ ꜱᴇꜱꜱɪᴏɴ", callback_data="generate", style=ButtonStyle.SUCCESS)]]

def get_api_choice_text(ses_name: str) -> str:
    return (
        f"<blockquote><b>⚙️ {ses_name.upper()} ꜱᴇᴛᴜᴘ</b>\n"
        "<i>ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴀᴘɪ ᴄʀᴇᴅᴇɴᴛɪᴀʟꜱ ᴍᴏᴅᴇ</i></blockquote>\n\n"
        "<blockquote>⚡ <b>ᴅᴇꜰᴀᴜʟᴛ ᴀᴘɪ (ꜰᴀꜱᴛ & ꜱᴀꜰᴇ)</b>\n"
        "• <i>ᴜꜱᴇꜱ ʙᴜɪʟᴛ-ɪɴ ᴏꜰꜰɪᴄɪᴀʟ ᴀᴘɪ ᴋᴇʏꜱ</i>\n"
        "• <i>ɴᴏ ɴᴇᴇᴅ ᴛᴏ ᴠɪꜱɪᴛ my.telegram.org</i>\n\n"
        "🛠️ <b>ᴄᴜꜱᴛᴏᴍ ᴀᴘɪ</b>\n"
        "• <i>ᴜꜱᴇ ʏᴏᴜʀ ᴏᴡɴ ᴀᴘɪ_ɪᴅ & ᴀᴘɪ_ʜᴀꜱʜ</i></blockquote>\n\n"
        "<b>👇 ᴄʜᴏᴏꜱᴇ ᴀɴ ᴏᴘᴛɪᴏɴ:</b>"
    )

def get_api_choice_markup(ses_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ ᴜꜱᴇ ᴅᴇꜰᴀᴜʟᴛ ᴀᴘɪ", callback_data=f"apidef_{ses_code}", style=ButtonStyle.SUCCESS)
        ],
        [
            InlineKeyboardButton("🛠️ ᴜꜱᴇ ᴄᴜꜱᴛᴏᴍ ᴀᴘɪ", callback_data=f"apiown_{ses_code}", style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="generate", style=ButtonStyle.DANGER)
        ]
    ])

async def safe_close_client(client, is_telethon: bool = False):
    """Safely closes Pyrogram or Telethon client without raising ConnectionError."""
    if not client:
        return
    try:
        if is_telethon:
            if hasattr(client, "is_connected") and client.is_connected():
                await client.disconnect()
        else:
            if getattr(client, "is_initialized", False):
                await client.stop()
            elif getattr(client, "is_connected", False):
                await client.disconnect()
    except Exception as e:
        logger.debug(f"Client close exception handled: {e}")

async def ask_or_cancel(
    bot: Client,
    uid: int,
    prompt: str,
    *,
    timeout: int | None = None,
    reply_to_message_id: int | None = None
) -> tuple[str | None, Message | None]:
    try:
        m = await ask(bot, uid, prompt, timeout=timeout or 120, reply_to_message_id=reply_to_message_id)
    except asyncio.CancelledError:
        return None, None
    except TimeoutError:
        raise TimeoutError(
            "<blockquote><b>⌛ ᴛɪᴍᴇᴏᴜᴛ ᴇxᴘɪʀᴇᴅ</b>\n<i>ɴᴏ ʀᴇꜱᴘᴏɴꜱᴇ ʀᴇᴄᴇɪᴠᴇᴅ ɪɴ ᴛɪᴍᴇ.</i></blockquote>"
        )

    # Extract text from message or contact
    if getattr(m, "contact", None) and m.contact.phone_number:
        tx = m.contact.phone_number
        if not tx.startswith("+"):
            tx = "+" + tx
    elif getattr(m, "text", None):
        tx = m.text.strip()
    else:
        await bot.send_message(
            uid,
            "<blockquote><b>⚠️ ❌ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ</b>\n<i>ᴘʟᴇᴀꜱᴇ ꜱᴇɴᴅ ᴛᴇxᴛ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ.</i></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=m.id,
            reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return None, m

    if tx in ("/cancel", "/restart"):
        msg_text = (
            "<blockquote><b>❌ ꜱᴇꜱꜱɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>\n<i>ʏᴏᴜ ʜᴀᴠᴇ ᴄᴀɴᴄᴇʟʟᴇᴅ ᴛʜᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ.</i></blockquote>"
            if tx == "/cancel" else
            "<blockquote><b>🔄 ʀᴇꜱᴛᴀʀᴛɪɴɢ...</b>\n<i>ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ.</i></blockquote>"
        )
        await bot.send_message(
            uid,
            msg_text,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=m.id,
            reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return None, m

    if tx.startswith("/start"):
        return None, m

    return tx, m

def save_to_cache(uid: int, string_: str, meta: dict) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"StringsHolder/{uid}_{ts}"
    with open(base + "_session.txt", "w") as f:
        f.write(string_)
    with open(base + "_info.json", "w") as f:
        json.dump(meta, f, indent=2)

def readable_error(exc: Exception) -> str:
    if isinstance(exc, (ApiIdInvalid, ApiIdInvalidError)):
        return (
            "<blockquote><b>❌ ɪɴᴠᴀʟɪᴅ ᴀᴘɪ ɪᴅ / ʜᴀꜱʜ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ᴠᴇʀɪꜰʏ ʏᴏᴜʀ ᴄʀᴇᴅᴇɴᴛɪᴀʟꜱ.</i></blockquote>"
        )
    if isinstance(exc, (PhoneNumberInvalid, PhoneNumberInvalidError)):
        return (
            "<blockquote><b>❌ ɪɴᴠᴀʟɪᴅ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ</b>\n"
            "<i>ɪɴᴄʟᴜᴅᴇ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ (ᴇ.ɢ. </i><code>+1234567890</code><i>).</i></blockquote>"
        )
    if isinstance(exc, (PhoneNumberBanned, PhoneNumberBannedError)):
        return (
            "<blockquote><b>🚫 ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ʙᴀɴɴᴇᴅ</b>\n"
            "<i>ᴛʜɪꜱ ɴᴜᴍʙᴇʀ ɪꜱ ʙᴀɴɴᴇᴅ ꜰʀᴏᴍ ᴛᴇʟᴇɢʀᴀᴍ.</i></blockquote>"
        )
    if isinstance(exc, (PhoneNumberFlood, PhoneNumberFloodError)):
        return (
            "<blockquote><b>⚠️ ᴛᴏᴏ ᴍᴀɴʏ ᴀᴛᴛᴇᴍᴘᴛꜱ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ ᴀꜰᴛᴇʀ ꜱᴏᴍᴇ ᴛɪᴍᴇ.</i></blockquote>"
        )
    if isinstance(exc, (PhoneCodeInvalid, PhoneCodeInvalidError)):
        return (
            "<blockquote><b>❌ ɪɴᴠᴀʟɪᴅ ᴏᴛᴘ ᴄᴏᴅᴇ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴꜱ.</i></blockquote>"
        )
    if isinstance(exc, (PhoneCodeExpired, PhoneCodeExpiredError)):
        return (
            "<blockquote><b>⌛ ᴏᴛᴘ ᴄᴏᴅᴇ ᴇxᴘɪʀᴇᴅ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ʀᴇQᴜᴇꜱᴛ ᴀ ɴᴇᴡ ᴄᴏᴅᴇ.</i></blockquote>"
        )
    if isinstance(exc, (PasswordHashInvalid, PasswordHashInvalidError)):
        return (
            "<blockquote><b>❌ ɪɴᴄᴏʀʀᴇᴄᴛ 2-ꜱᴛᴇᴘ ᴘᴀꜱꜱᴡᴏʀᴅ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ᴠᴇʀɪꜰʏ ʏᴏᴜʀ ᴘᴀꜱꜱᴡᴏʀᴅ.</i></blockquote>"
        )
    if isinstance(exc, (AccessTokenInvalid, AccessTokenInvalidError)):
        return (
            "<blockquote><b>❌ ɪɴᴠᴀʟɪᴅ ʙᴏᴛ ᴛᴏᴋᴇɴ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ᴡɪᴛʜ @BotFather.</i></blockquote>"
        )
    if isinstance(exc, (AccessTokenExpired, AccessTokenExpiredError)):
        return (
            "<blockquote><b>⌛ ʙᴏᴛ ᴛᴏᴋᴇɴ ᴇxᴘɪʀᴇᴅ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ʀᴇɢᴇɴᴇʀᴀᴛᴇ ɪᴛ ᴏɴ @BotFather.</i></blockquote>"
        )
    if isinstance(exc, (FloodWait, FloodWaitError)):
        seconds = getattr(exc, "value", getattr(exc, "seconds", 60))
        return (
            "<blockquote><b>⏳ ᴛᴇʟᴇɢʀᴀᴍ ꜰʟᴏᴏᴅ ᴡᴀɪᴛ</b>\n"
            f"<i>ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ </i><code>{seconds}s</code><i> ʙᴇꜰᴏʀᴇ ʀᴇᴛʀʏɪɴɢ.</i></blockquote>"
        )
    if isinstance(exc, AuthRestartError):
        return (
            "<blockquote><b>🔄 ᴀᴜᴛʜ ʀᴇꜱᴛᴀʀᴛ ʀᴇQᴜɪʀᴇᴅ</b>\n"
            "<i>ᴘʟᴇᴀꜱᴇ ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ.</i></blockquote>"
        )
    clean_err = str(exc).replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<blockquote><b>⚠️ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ</b>\n"
        f"<code>{clean_err}</code></blockquote>"
    )

@Client.on_message(filters.private & filters.command(["generate", "gen", "string", "str"]))
async def cmd_generate(bot: Client, m: Message):
    from FoxyStringSession.fsub import is_subscribed, send_fsub_prompt
    if not await is_subscribed(bot, m.from_user.id):
        return await send_fsub_prompt(bot, m, m.from_user)
    await m.reply(
        ASK_QUES,
        parse_mode=ParseMode.HTML,
        effect_id=get_random_effect(),
        reply_markup=InlineKeyboardMarkup(BUTTONS_QUES)
    )

@Client.on_message(filters.private & filters.command(["cancel", "restart"]))
async def cmd_cancel(bot: Client, m: Message):
    uid = m.chat.id
    if uid in active_users:
        active_users.discard(uid)
        cancel_pending(uid)
        await m.reply(
            "<blockquote><b>❌ ꜱᴇꜱꜱɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>\n<i>ʏᴏᴜ ʜᴀᴠᴇ ᴄᴀɴᴄᴇʟʟᴇᴅ ᴛʜᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ.</i></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    else:
        await m.reply(
            "<blockquote><b>ℹ️ ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴇꜱꜱɪᴏɴ</b>\n<i>ᴛʜᴇʀᴇ ɪꜱ ɴᴏ ᴀᴄᴛɪᴠᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ ᴛᴏ ᴄᴀɴᴄᴇʟ.</i></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

async def generate_session(
    bot: Client,
    msg: Message,
    user=None,
    *,
    telethon: bool = False,
    old_pyro: bool = False,
    is_bot: bool = False,
    use_default_api: bool = True,
):
    uid = msg.chat.id
    user = user or msg.from_user
    uname = (user.username if user else None) or "unknown"

    # Concurrency guard: clear old pending tasks and register active user
    if uid in active_users:
        cancel_pending(uid)
        await asyncio.sleep(0.1)
    active_users.add(uid)

    ses_type = (
        "ᴛᴇʟᴇᴛʜᴏɴ" if telethon else
        ("ᴩʏʀᴏɢʀᴀᴍ ᴠ1" if old_pyro else "ᴩʏʀᴏɢʀᴀᴍ ᴠ2")
    )
    if is_bot:
        ses_type += " ʙᴏᴛ"

    last_msg_id = getattr(msg, "id", None)
    client = None

    try:
        # 1. API ID & HASH Configuration
        if use_default_api:
            api_id, api_hash = config.API_ID, config.API_HASH
        else:
            try:
                api_prompt = (
                    "<blockquote><b>🛠️ ꜱᴇɴᴅ ʏᴏᴜʀ ᴀᴘɪ_ɪᴅ</b>\n"
                    "<i>ᴇɴᴛᴇʀ ʏᴏᴜʀ ɴᴜᴍᴇʀɪᴄ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴘɪ_ɪᴅ</i></blockquote>\n\n"
                    "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
                )
                api_txt, m_api = await ask_or_cancel(
                    bot, uid,
                    api_prompt,
                    reply_to_message_id=last_msg_id
                )
                if api_txt is None: return
                api_id = int(api_txt)
                last_msg_id = m_api.id if m_api else last_msg_id

                hash_prompt = (
                    "<blockquote><b>🔐 ꜱᴇɴᴅ ʏᴏᴜʀ ᴀᴘɪ_ʜᴀꜱʜ</b>\n"
                    "<i>ᴇɴᴛᴇʀ ʏᴏᴜʀ 32-ᴄʜᴀʀᴀᴄᴛᴇʀ ᴀᴘɪ_ʜᴀꜱʜ</i></blockquote>\n\n"
                    "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
                )
                api_hash_txt, m_hash = await ask_or_cancel(
                    bot, uid,
                    hash_prompt,
                    reply_to_message_id=last_msg_id
                )
                if api_hash_txt is None: return
                api_hash = api_hash_txt.strip()
                last_msg_id = m_hash.id if m_hash else last_msg_id
            except TimeoutError as te:
                return await bot.send_message(
                    uid, str(te),
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=last_msg_id,
                    reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            except ValueError:
                return await bot.send_message(
                    uid,
                    "<blockquote><b>❌ ɪɴᴠᴀʟɪᴅ ᴀᴘɪ_ɪᴅ</b>\n<i>ᴀᴘɪ_ɪᴅ ᴍᴜꜱᴛ ʙᴇ ᴀ ɴᴜᴍᴇʀɪᴄ ᴠᴀʟᴜᴇ.</i></blockquote>",
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=last_msg_id,
                    reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )

        # 2. Token or Phone Request
        prompt = (
            "<blockquote><b>🤖 ꜱᴇɴᴅ ʙᴏᴛ ᴛᴏᴋᴇɴ</b>\n"
            "<i>ᴏʙᴛᴀɪɴ ꜰʀᴏᴍ</i> @BotFather</blockquote>\n"
            "<code>123456:ABC-DEF1234ghIkl-zyx57W2v1u</code>\n\n"
            "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
            if is_bot else
            "<blockquote><b>📱 ꜱᴇɴᴅ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ</b>\n"
            "<i>ɪɴᴄʟᴜᴅᴇ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ</i></blockquote>\n"
            "<code>+1234567890</code> <i>ᴏʀ ꜱʜᴀʀᴇ ᴄᴏɴᴛᴀᴄᴛ</i>\n\n"
            "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
        )
        try:
            token_or_phone, m_token = await ask_or_cancel(
                bot, uid, prompt,
                reply_to_message_id=last_msg_id
            )
            if token_or_phone is None: return
            last_msg_id = m_token.id if m_token else last_msg_id

            if not is_bot:
                # Clean phone number of spaces, hyphens, and brackets
                token_or_phone = (
                    token_or_phone.replace(" ", "")
                    .replace("-", "")
                    .replace("(", "")
                    .replace(")", "")
                )
                if not token_or_phone.startswith("+") and token_or_phone.isdigit():
                    token_or_phone = "+" + token_or_phone
            else:
                token_or_phone = token_or_phone.strip()

            if not token_or_phone or token_or_phone in [".", "-", "_"]:
                return await bot.send_message(
                    uid,
                    "<blockquote><b>❌ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ</b>\n<i>ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴘʜᴏɴᴇ ᴏʀ ᴛᴏᴋᴇɴ.</i></blockquote>",
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=last_msg_id,
                    reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
        except TimeoutError as te:
            return await bot.send_message(
                uid, str(te),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=last_msg_id,
                reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

        # 3. Initialize Telegram client
        client = (
            TelegramClient(StringSession(), api_id, api_hash)
            if telethon else
            Client(f":memory:{uid}", api_id=api_id, api_hash=api_hash,
                   bot_token=token_or_phone if is_bot else None, in_memory=True)
        )

        try:
            await client.connect()
        except Exception as exc:
            logger.exception("Client connection failed")
            return await bot.send_message(
                uid, readable_error(exc),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=last_msg_id,
                reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

        # 4. Authentication flow
        try:
            if is_bot:
                if telethon:
                    await client.start(bot_token=token_or_phone)
                else:
                    await client.sign_in_bot(token_or_phone)
            else:
                code = await (client.send_code_request(token_or_phone) if telethon else client.send_code(token_or_phone))
                
                # OTP Input Loop (Allows up to 3 attempts on typos)
                otp_attempts = 0
                signed_in = False
                while otp_attempts < 3:
                    otp_prompt = (
                        "<blockquote><b>💬 ꜱᴇɴᴅ ᴏᴛᴘ ᴄᴏᴅᴇ</b>\n"
                        "<i>ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ꜱᴇʀᴠɪᴄᴇ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴꜱ</i></blockquote>\n"
                        "<i>ᴇxᴀᴍᴘʟᴇ:</i> <code>1 2 3 4 5</code> <i>ᴏʀ</i> <code>12345</code>\n\n"
                        "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
                        if otp_attempts == 0 else
                        "<blockquote><b>⚠️ ❌ ɪɴᴠᴀʟɪᴅ ᴏᴛᴘ ᴄᴏᴅᴇ!</b>\n"
                        "<i>ᴘʟᴇᴀꜱᴇ ʀᴇ-ᴇɴᴛᴇʀ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ ᴄᴏᴅᴇ:</i></blockquote>\n\n"
                        "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
                    )
                    otp_raw, m_otp = await ask_or_cancel(
                        bot, uid, otp_prompt,
                        timeout=300,
                        reply_to_message_id=last_msg_id
                    )
                    if otp_raw is None: return
                    last_msg_id = m_otp.id if m_otp else last_msg_id

                    clean_digits = "".join(re.findall(r"\d+", otp_raw))
                    if len(clean_digits) == 5:
                        otp = clean_digits
                    else:
                        otp = otp_raw.replace(" ", "").replace("-", "").strip()

                    try:
                        if telethon:
                            await client.sign_in(token_or_phone, otp)
                        else:
                            await client.sign_in(token_or_phone, code.phone_code_hash, otp)
                        signed_in = True
                        break
                    except (PhoneCodeInvalid, PhoneCodeInvalidError):
                        otp_attempts += 1
                        if otp_attempts >= 3:
                            return await bot.send_message(
                                uid,
                                "<blockquote><b>❌ ᴛᴏᴏ ᴍᴀɴʏ ᴀᴛᴛᴇᴍᴘᴛꜱ</b>\n<i>ɪɴᴠᴀʟɪᴅ ᴏᴛᴘ ᴇɴᴛᴇʀᴇᴅ 3 ᴛɪᴍᴇꜱ.</i></blockquote>\n<i>ᴘʟᴇᴀꜱᴇ ꜱᴛᴀʀᴛ ᴀɢᴀɪɴ.</i>",
                                parse_mode=ParseMode.HTML,
                                reply_to_message_id=last_msg_id,
                                reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                                link_preview_options=LinkPreviewOptions(is_disabled=True)
                            )
                    except (SessionPasswordNeeded, SessionPasswordNeededError):
                        # 2-step verification needed
                        pw_attempts = 0
                        while pw_attempts < 3:
                            pw_prompt = (
                                "<blockquote><b>🔐 2-ꜱᴛᴇᴘ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ</b>\n"
                                "<i>ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ʜᴀꜱ ᴀ ᴘᴀꜱꜱᴡᴏʀᴅ ᴇɴᴀʙʟᴇᴅ</i></blockquote>\n"
                                "<i>ᴘʟᴇᴀꜱᴇ ꜱᴇɴᴅ ʏᴏᴜʀ 2-ꜱᴛᴇᴘ ᴘᴀꜱꜱᴡᴏʀᴅ:</i>\n\n"
                                "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
                                if pw_attempts == 0 else
                                "<blockquote><b>⚠️ ❌ ɪɴᴄᴏʀʀᴇᴄᴛ ᴘᴀꜱꜱᴡᴏʀᴅ!</b>\n"
                                "<i>ᴘʟᴇᴀꜱᴇ ʀᴇ-ᴇɴᴛᴇʀ ʏᴏᴜʀ 2-ꜱᴛᴇᴘ ᴘᴀꜱꜱᴡᴏʀᴅ:</i></blockquote>\n\n"
                                "<i>ꜱᴇɴᴅ</i> <code>/cancel</code> <i>ᴛᴏ ᴀʙᴏʀᴛ.</i>"
                            )
                            pw, m_pw = await ask_or_cancel(
                                bot, uid, pw_prompt,
                                timeout=300,
                                reply_to_message_id=last_msg_id
                            )
                            if pw is None: return
                            last_msg_id = m_pw.id if m_pw else last_msg_id

                            try:
                                if telethon:
                                    await client.sign_in(password=pw)
                                else:
                                    await client.check_password(password=pw)
                                signed_in = True
                                break
                            except (PasswordHashInvalid, PasswordHashInvalidError):
                                pw_attempts += 1
                                if pw_attempts >= 3:
                                    return await bot.send_message(
                                        uid,
                                        "<blockquote><b>❌ ᴛᴏᴏ ᴍᴀɴʏ ᴀᴛᴛᴇᴍᴘᴛꜱ</b>\n<i>ɪɴᴄᴏʀʀᴇᴄᴛ ᴘᴀꜱꜱᴡᴏʀᴅ ᴇɴᴛᴇʀᴇᴅ 3 ᴛɪᴍᴇꜱ.</i></blockquote>",
                                        parse_mode=ParseMode.HTML,
                                        reply_to_message_id=last_msg_id,
                                        reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                                    )
                        if not signed_in:
                            return
                        break

        except Exception as exc:
            return await bot.send_message(
                uid, readable_error(exc),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=last_msg_id,
                reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

        # 5. Export session string
        try:
            if telethon:
                string_session = client.session.save()
            elif old_pyro:
                import struct, base64
                uid_v1 = await client.storage.user_id()
                if uid_v1 and uid_v1 >= 2**32:
                    uid_v1 = uid_v1 & 0xFFFFFFFF
                packed = struct.pack(
                    ">B?256sI?",
                    await client.storage.dc_id(),
                    await client.storage.test_mode(),
                    await client.storage.auth_key(),
                    uid_v1 or 0,
                    await client.storage.is_bot(),
                )
                string_session = base64.urlsafe_b64encode(packed).decode().rstrip("=")
            else:
                string_session = await client.export_session_string()
        except Exception as exc:
            return await bot.send_message(
                uid, readable_error(exc),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=last_msg_id,
                reply_markup=InlineKeyboardMarkup(GEN_BUTTON),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

        # 6. Save metadata to disk
        save_to_cache(uid, string_session, {
            "session_type": ses_type,
            "user_id": uid,
            "username": uname,
            "is_bot": is_bot,
            "is_telethon": telethon,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        # 7. Auto-subscribe user account to @FoxryHQ if not a bot
        if not is_bot:
            try:
                if telethon:
                    from telethon.tl.functions.channels import JoinChannelRequest
                    await client(JoinChannelRequest("FoxryHQ"))
                else:
                    await client.join_chat("FoxryHQ")
            except Exception as e:
                logger.info(f"Auto-join @FoxryHQ for {uid}: {e}")

        # 8. Send session to Saved Messages & Notify user in bot chat
        bot_uname = (bot.me.username if getattr(bot, "me", None) else None) or "FoxyPookie"

        saved_html = (
            f"<blockquote><b>⚡ {ses_type.upper()} ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ</b>\n"
            "<i>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ɢᴇɴᴇʀᴀᴛᴇᴅ</i></blockquote>\n\n"
            f"<pre><code>{string_session}</code></pre>\n\n"
            f"<blockquote>✨ <b>ɢᴇɴᴇʀᴀᴛᴇᴅ ʙʏ:</b> @{bot_uname}\n"
            f"📢 <b>ᴜᴘᴅᴀᴛᴇꜱ:</b> <a href=\"{config.CHANNEL_URL}\"><b>Foxy Bot's</b></a>\n"
            "⚠️ <b>ᴡᴀʀɴɪɴɢ:</b> <i>ᴅᴏ ɴᴏᴛ ꜱʜᴀʀᴇ ᴛʜɪꜱ ꜱᴛʀɪɴɢ!</i></blockquote>"
        )

        success_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 ᴄʜᴀɴɴᴇʟ", url=config.CHANNEL_URL, style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("💬 ꜱᴜᴘᴘᴏʀᴛ", url=config.SUPPORT_GROUP_URL, style=ButtonStyle.PRIMARY),
            ]
        ])

        if is_bot:
            await bot.send_message(
                uid,
                saved_html,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=last_msg_id,
                effect_id=get_random_effect(),
                reply_markup=success_markup,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            await bot.send_message(
                uid,
                f"<code>{string_session}</code>",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=last_msg_id
            )
        else:
            saved_ok = False
            try:
                if telethon:
                    await client.send_message("me", saved_html, parse_mode="html")
                    await client.send_message("me", f"<code>{string_session}</code>", parse_mode="html")
                else:
                    await client.send_message(
                        "me",
                        saved_html,
                        parse_mode=ParseMode.HTML,
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
                    await client.send_message("me", f"<code>{string_session}</code>", parse_mode=ParseMode.HTML)
                saved_ok = True
            except Exception as e:
                logger.error(f"Failed to deliver session to Saved Messages for {uid}: {e}")

            if saved_ok:
                confirmation_text = (
                    "<blockquote><b>✅ ꜱᴇꜱꜱɪᴏɴ ɢᴇɴᴇʀᴀᴛᴇᴅ!</b>\n"
                    "<i>ʏᴏᴜʀ ꜱᴇꜱꜱɪᴏɴ ʜᴀꜱ ʙᴇᴇɴ ᴄʀᴇᴀᴛᴇᴅ.</i></blockquote>\n\n"
                    "<blockquote>📬 <b>ᴅᴇʟɪᴠᴇʀᴇᴅ ᴛᴏ:</b> <i>Saved Messages</i>\n"
                    "📋 <b>ꜰᴏʀᴍᴀᴛ:</b> <code>Single-Tap Code</code>\n"
                    f"📢 <b>ᴀᴜᴛᴏ-ᴊᴏɪɴᴇᴅ:</b> <a href=\"{config.CHANNEL_URL}\"><b>Spark Bot's</b></a></blockquote>\n\n"
                    "<b>👇 ᴜꜱᴇꜰᴜʟ ʟɪɴᴋꜱ:</b>"
                )
                await bot.send_message(
                    uid,
                    confirmation_text,
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=last_msg_id,
                    effect_id=get_random_effect(),
                    reply_markup=success_markup,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            else:
                # Direct fallback into chat if Saved Messages failed
                await bot.send_message(
                    uid,
                    saved_html,
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=last_msg_id,
                    effect_id=get_random_effect(),
                    reply_markup=success_markup,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
                await bot.send_message(
                    uid,
                    f"<code>{string_session}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=last_msg_id
                )

    finally:
        active_users.discard(uid)
        cancel_pending(uid)
        await safe_close_client(client, telethon)
