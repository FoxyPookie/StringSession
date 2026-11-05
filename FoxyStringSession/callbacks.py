# Authored By Foxy Bots 
import logging
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.errors import MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, LinkPreviewOptions

import config
from effect import get_random_effect
from FoxyStringSession.fsub import is_subscribed, FSUB_KEYBOARD, FSUB_TEXT
from FoxyStringSession.generate import (
    generate_session,
    get_api_choice_text,
    get_api_choice_markup,
    ASK_QUES,
    BUTTONS_QUES,
)
from FoxyStringSession.start import get_start_caption, START_KEYBOARD
from FoxyStringSession.media import get_start_photo, update_photo_file_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ERROR_MESSAGE = (
    "<blockquote><b>❌ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ</b>\n"
    "<i>ᴘʟᴇᴀꜱᴇ ᴍᴀᴋᴇ ꜱᴜʀᴇ ʏᴏᴜ ᴇɴᴛᴇʀ ᴠᴀʟɪᴅ ᴅᴀᴛᴀ.</i></blockquote>\n\n"
    f"<i>ɪꜰ ᴛʜᴇ ɪꜱꜱᴜᴇ ᴘᴇʀꜱɪꜱᴛꜱ, ᴄᴏɴᴛᴀᴄᴛ <a href=\"{config.SUPPORT_GROUP_URL}\"><b>ꜱᴜᴘᴘᴏʀᴛ</b></a>.</i>"
)

SES_MAP = {
    "pyro_v1": {"name": "Pyrogram v1", "old_pyro": True, "telethon": False, "is_bot": False},
    "pyro_v2": {"name": "Pyrogram v2", "old_pyro": False, "telethon": False, "is_bot": False},
    "telethon": {"name": "Telethon", "old_pyro": False, "telethon": True, "is_bot": False},
    "pyro_bot": {"name": "Pyrogram Bot", "old_pyro": False, "telethon": False, "is_bot": True},
    "telethon_bot": {"name": "Telethon Bot", "old_pyro": False, "telethon": True, "is_bot": True},
}

KEY_MAP = {
    "pyrogram_v1": "pyro_v1",
    "pyrogram_v2": "pyro_v2",
    "telethon": "telethon",
    "pyrogram_bot": "pyro_bot",
    "telethon_bot": "telethon_bot",
}

CALLBACK_PATTERN = r"^(generate|back_to_start|check_fsub|pyrogram_v1|pyrogram_v2|pyrogram_bot|telethon|telethon_bot|apidef_.+|apiown_.+)$"

@Client.on_callback_query(filters.regex(CALLBACK_PATTERN))
async def sessiongen_callbacks(bot: Client, cq: CallbackQuery):
    choice = cq.data
    user = cq.from_user
    logger.info(f"🔘 Callback '{choice}' from user: {user.id if user else 'Unknown'} (@{getattr(user, 'username', 'none')})")

    try:
        # 1. Force Subscribe verification
        if choice == "check_fsub":
            if await is_subscribed(bot, user.id, force_refresh=True):
                await cq.answer("✅ ᴀᴄᴄᴇꜱꜱ ɢʀᴀɴᴛᴇᴅ! ᴡᴇʟᴄᴏᴍᴇ.", show_alert=True)
                caption = get_start_caption(bot, user)
                if cq.message.photo:
                    try:
                        return await cq.edit_message_caption(
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=START_KEYBOARD
                        )
                    except MessageNotModified:
                        return
                else:
                    try:
                        await cq.message.delete()
                    except Exception:
                        pass
                    photo = get_start_photo()
                    if photo:
                        sent = await bot.send_photo(
                            chat_id=user.id,
                            photo=photo,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            has_spoiler=True,
                            effect_id=get_random_effect(),
                            reply_markup=START_KEYBOARD,
                        )
                        update_photo_file_id(sent)
                        return sent
                    else:
                        return await bot.send_message(
                            chat_id=user.id,
                            text=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=START_KEYBOARD,
                            link_preview_options=LinkPreviewOptions(is_disabled=True)
                        )
            else:
                return await cq.answer("❌ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ @FoxryHQ ʏᴇᴛ! ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ꜰɪʀꜱᴛ.", show_alert=True)

        # For all other callbacks, enforce FSub
        if not await is_subscribed(bot, user.id):
            await cq.answer("⚠️ ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ @FoxryHQ ꜰɪʀꜱᴛ!", show_alert=True)
            text = FSUB_TEXT.format(mention=user.mention)
            if cq.message.photo:
                try:
                    return await cq.edit_message_caption(
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=FSUB_KEYBOARD
                    )
                except MessageNotModified:
                    return
            else:
                try:
                    return await cq.edit_message_text(
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=FSUB_KEYBOARD,
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
                except MessageNotModified:
                    return

        await cq.answer()

        # 2. Main generate menu (edits existing message)
        if choice == "generate":
            if cq.message.photo:
                try:
                    return await cq.edit_message_caption(
                        caption=ASK_QUES,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(BUTTONS_QUES)
                    )
                except MessageNotModified:
                    return
            else:
                try:
                    return await cq.edit_message_text(
                        text=ASK_QUES,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(BUTTONS_QUES),
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
                except MessageNotModified:
                    return

        # 3. Back to Start
        if choice == "back_to_start":
            caption = get_start_caption(bot, user)
            if cq.message.photo:
                try:
                    return await cq.edit_message_caption(
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=START_KEYBOARD
                    )
                except MessageNotModified:
                    return
            else:
                try:
                    await cq.message.delete()
                except Exception:
                    pass
                photo = get_start_photo()
                if photo:
                    sent = await bot.send_photo(
                        chat_id=user.id,
                        photo=photo,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        has_spoiler=True,
                        effect_id=get_random_effect(),
                        reply_markup=START_KEYBOARD,
                    )
                    update_photo_file_id(sent)
                    return sent
                else:
                    return await bot.send_message(
                        chat_id=user.id,
                        text=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=START_KEYBOARD,
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )

        # 4. Session type clicked -> Edit message to show API ID selection (Default vs Custom)
        if choice in KEY_MAP:
            code = KEY_MAP[choice]
            name = SES_MAP[code]["name"]
            text = get_api_choice_text(name)
            markup = get_api_choice_markup(code)
            if cq.message.photo:
                try:
                    return await cq.edit_message_caption(
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup
                    )
                except MessageNotModified:
                    return
            else:
                try:
                    return await cq.edit_message_text(
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup,
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
                except MessageNotModified:
                    return

        # 5. User selected Default API or Custom API
        if choice.startswith("apidef_") or choice.startswith("apiown_"):
            use_default = choice.startswith("apidef_")
            code = choice.split("_", 1)[1]
            info = SES_MAP[code]
            return await generate_session(
                bot,
                cq.message,
                user=cq.from_user,
                telethon=info["telethon"],
                old_pyro=info["old_pyro"],
                is_bot=info["is_bot"],
                use_default_api=use_default
            )

        await cq.message.reply(
            "<blockquote><b>⚠️ ᴜɴᴋɴᴏᴡɴ ʀᴇQᴜᴇꜱᴛ</b>\n<i>ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ.</i></blockquote>",
            parse_mode=ParseMode.HTML
        )

    except MessageNotModified:
        pass
    except Exception:
        logger.exception("⚠️ Error in callback handler")
        await cq.message.reply(
            ERROR_MESSAGE,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
