# Authored By Foxy Bots
import asyncio
import logging
from typing import Union
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, LinkPreviewOptions

import config
from effect import get_random_effect
from FoxyStringSession.save_user import save_user
from FoxyStringSession.fsub import is_subscribed, send_fsub_prompt
from FoxyStringSession.media import get_start_photo, update_photo_file_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

START_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "⚙️ ɢᴇɴᴇʀᴀᴛᴇ ꜱᴇꜱꜱɪᴏɴ",
            callback_data="generate",
            style=ButtonStyle.SUCCESS
        ),
        InlineKeyboardButton(
            "🔍 ᴄʜᴇᴄᴋ ꜱᴇꜱꜱɪᴏɴ",
            callback_data="check_session",
            style=ButtonStyle.PRIMARY
        ),
    ],
    [
        InlineKeyboardButton(
            "📢 ᴄʜᴀɴɴᴇʟ",
            url=config.CHANNEL_URL,
            style=ButtonStyle.PRIMARY
        ),
        InlineKeyboardButton(
            "💬 ꜱᴜᴘᴘᴏʀᴛ",
            url=config.SUPPORT_GROUP_URL,
            style=ButtonStyle.PRIMARY
        ),
    ],
    [
        InlineKeyboardButton(
            "👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ",
            url=config.OWNER_URL,
            style=ButtonStyle.DANGER
        )
    ]
])

def get_start_caption(bot: Client, user) -> str:
    """Compact English start message with separate blockquotes per feature line."""
    bot_name = (bot.me.first_name if getattr(bot, "me", None) else None) or "Notty Session Bot"
    mention = user.mention if user else "User"
    return (
        f"<blockquote><b>👋 ʜᴇʏ {mention}</b>\n"
        f"<i>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ</i> <b>{bot_name}</b></blockquote>\n\n"
        "<blockquote>⚡ <i>Fastest Telegram string session generator.</i></blockquote>\n"
        "<blockquote>🔐 <i>Supports Pyrogram v1, v2 & Telethon.</i></blockquote>\n"
        "<blockquote>🛡️ <i>Safe, encrypted, in-memory processing.</i></blockquote>\n\n"
        "<b>👇 ᴛᴀᴘ ʙᴇʟᴏᴡ ᴛᴏ ʙᴇɢɪɴ:</b>"
    )

def command_filter(cmd: Union[str, list]) -> filters.Filter:
    return filters.private & filters.incoming & filters.command(cmd)

@Client.on_message(command_filter(["start", "help"]))
async def start_handler(bot: Client, message: Message):
    user = message.from_user
    logger.info(f"📩 /start from user: {user.id if user else 'Unknown'} (@{getattr(user, 'username', 'none')})")

    # Non-blocking background save
    if user:
        asyncio.create_task(save_user(user))

    # Fast Force Subscribe Check (with in-memory TTL cache)
    if not await is_subscribed(bot, user.id):
        return await send_fsub_prompt(bot, message, user)

    try:
        response_text = get_start_caption(bot, user)
        effect = get_random_effect()
        photo = get_start_photo()

        if photo:
            try:
                sent = await message.reply_photo(
                    photo=photo,
                    caption=response_text,
                    parse_mode=ParseMode.HTML,
                    has_spoiler=True,
                    effect_id=effect,
                    reply_markup=START_KEYBOARD,
                )
                update_photo_file_id(sent)
            except Exception:
                sent = await message.reply_photo(
                    photo=photo,
                    caption=response_text,
                    parse_mode=ParseMode.HTML,
                    has_spoiler=True,
                    reply_markup=START_KEYBOARD,
                )
                update_photo_file_id(sent)
        else:
            try:
                await message.reply_text(
                    text=response_text,
                    parse_mode=ParseMode.HTML,
                    effect_id=effect,
                    reply_markup=START_KEYBOARD,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            except Exception:
                await message.reply_text(
                    text=response_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=START_KEYBOARD,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )

    except Exception as e:
        logger.exception("⚠️ Error in /start or /help handler:")
        await message.reply_text(
            "<blockquote><b>⚠️ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ</b>\n<i>ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.</i></blockquote>",
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
