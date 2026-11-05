# Authored By Foxy Bots
import time
import logging
from pyrogram import Client
from pyrogram.enums import ButtonStyle, ChatMemberStatus, ParseMode
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, RPCError
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, LinkPreviewOptions

import config
from effect import get_random_effect
from FoxyStringSession.media import get_start_photo, update_photo_file_id

logger = logging.getLogger(__name__)

FSUB_CHANNEL = "@SparkDevBotz"

# Fast in-memory subscription cache: user_id -> expire_timestamp
_fsub_cache: dict[int, float] = {}

FSUB_TEXT = (
    "<blockquote><b>⚠️ ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ</b>\n"
    "<i>ʜᴇʏ</i> {mention}</blockquote>\n\n"
    "<blockquote>📢 <b>ʏᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ</b>\n"
    f"<i>ᴊᴏɪɴ</i> <a href=\"{config.CHANNEL_URL}\"><b>Spark Bot's</b></a> <i>ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ.</i></blockquote>\n\n"
    "<b>👇 ᴊᴏɪɴ & ᴛᴀᴘ ᴄʜᴇᴄᴋ ᴛᴏ ᴜɴʟᴏᴄᴋ:</b>"
)

FSUB_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ",
            url=config.CHANNEL_URL,
            style=ButtonStyle.PRIMARY
        )
    ],
    [
        InlineKeyboardButton(
            "🔄 ᴄʜᴇᴄᴋ ᴊᴏɪɴᴇᴅ",
            callback_data="check_fsub",
            style=ButtonStyle.SUCCESS
        )
    ]
])

async def is_subscribed(bot: Client, user_id: int, force_refresh: bool = False) -> bool:
    """Checks if the user is a subscriber of @SparkDevBotz with caching."""
    global _fsub_cache
    if user_id == config.OWNER_ID:
        return True

    now = time.time()

    # Clean old cache entries if list exceeds 2000 items
    if len(_fsub_cache) > 2000:
        _fsub_cache = {u: exp for u, exp in _fsub_cache.items() if exp > now}

    if not force_refresh and user_id in _fsub_cache:
        if now < _fsub_cache[user_id]:
            return True
        else:
            _fsub_cache.pop(user_id, None)

    try:
        member = await bot.get_chat_member(chat_id=FSUB_CHANNEL, user_id=user_id)
        if member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.RESTRICTED,
        ]:
            _fsub_cache[user_id] = now + 120  # Cache valid for 2 minutes
            return True
        return False
    except UserNotParticipant:
        _fsub_cache.pop(user_id, None)
        return False
    except ChatAdminRequired:
        logger.warning("Bot is not an admin in @FoxryHQ! FSub cannot be enforced.")
        return True
    except RPCError as e:
        logger.warning(f"FSub check RPC error for {user_id}: {e}")
        if "USER_NOT_PARTICIPANT" in str(e):
            _fsub_cache.pop(user_id, None)
            return False
        return True
    except Exception as e:
        logger.exception(f"Unexpected error in is_subscribed: {e}")
        return True

async def send_fsub_prompt(bot: Client, message: Message, user=None):
    """Sends the force subscribe prompt message with spoiler image and web preview disabled."""
    user = user or message.from_user
    mention = user.mention if user else "User"
    text = FSUB_TEXT.format(mention=mention)
    effect = get_random_effect()
    photo = get_start_photo()

    if photo:
        try:
            sent = await message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML,
                has_spoiler=True,
                effect_id=effect,
                reply_markup=FSUB_KEYBOARD
            )
            update_photo_file_id(sent)
            return sent
        except Exception:
            sent = await message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML,
                has_spoiler=True,
                reply_markup=FSUB_KEYBOARD
            )
            update_photo_file_id(sent)
            return sent
    else:
        try:
            return await message.reply_text(
                text=text,
                parse_mode=ParseMode.HTML,
                effect_id=effect,
                reply_markup=FSUB_KEYBOARD,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception:
            return await message.reply_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=FSUB_KEYBOARD,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
