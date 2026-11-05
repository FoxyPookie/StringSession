# Authored By Foxy Bots
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, LinkPreviewOptions
from asyncio.exceptions import TimeoutError

logger = logging.getLogger(__name__)

pending_users: dict[int, asyncio.Future] = {}

TIMEOUT_TEXT = (
    "<blockquote><b>⌛ ᴛɪᴍᴇᴏᴜᴛ ᴇxᴘɪʀᴇᴅ</b>\n"
    "<i>ɴᴏ ʀᴇꜱᴘᴏɴꜱᴇ ʀᴇᴄᴇɪᴠᴇᴅ ɪɴ ᴛɪᴍᴇ.</i></blockquote>\n\n"
    "<i>ꜱᴇꜱꜱɪᴏɴ ɢᴇɴᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.</i>"
)

def cancel_pending(user_id: int) -> None:
    """Cancels and clears any pending ask() future for the given user."""
    future = pending_users.pop(user_id, None)
    if future and not future.done():
        future.cancel()

async def ask(
    client: Client,
    user_id: int,
    text: str,
    timeout: int = 120,
    reply_to_message_id: int | None = None
) -> Message:
    """Asks a question and waits for the user's next message."""
    await client.send_message(
        user_id,
        text,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    # Cancel previous future if exists
    cancel_pending(user_id)

    future = loop.create_future()
    pending_users[user_id] = future

    try:
        return await asyncio.wait_for(future, timeout)
    except TimeoutError:
        pending_users.pop(user_id, None)
        await client.send_message(
            user_id,
            TIMEOUT_TEXT,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_to_message_id,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        raise
    except asyncio.CancelledError:
        pending_users.pop(user_id, None)
        raise
    except Exception:
        pending_users.pop(user_id, None)
        raise

@Client.on_message(filters.private & (filters.text | filters.contact), group=-1)
async def listen_for_reply(bot: Client, message: Message):
    user_id = message.chat.id
    future = pending_users.get(user_id)
    if not future or future.done():
        message.continue_propagation()
        return

    # If the user typed /start, cancel pending future and let /start handler run cleanly
    if message.text and message.text.strip().startswith("/start"):
        pending_users.pop(user_id, None)
        future.cancel()
        message.continue_propagation()
        return

    pending_users.pop(user_id, None)
    future.set_result(message)
