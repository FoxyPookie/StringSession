# Authored By Foxy Bots
import os
import sys
import asyncio
import traceback
from time import time
from io import StringIO
from inspect import getfullargspec

from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle, ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID

async def aexec(code, client, message):
    exec(
        "async def __aexec(client, message):"
        + "".join(f"\n {line}" for line in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)

async def edit_or_reply(msg: Message, **kwargs):
    func = msg.edit_text if getattr(getattr(msg, "from_user", None), "is_self", False) else msg.reply
    spec = getfullargspec(func.__wrapped__).args
    await func(**{k: v for k, v in kwargs.items() if k in spec})

@Client.on_message(
    filters.command("eval")
    & filters.user(OWNER_ID)
    & ~filters.forwarded
    & ~filters.via_bot
)
@Client.on_edited_message(
    filters.command("eval")
    & filters.user(OWNER_ID)
    & ~filters.forwarded
    & ~filters.via_bot
)
async def executor(client, message: Message):
    if len(message.command) < 2:
        return await edit_or_reply(
            message,
            text="<blockquote><b>💻 ᴇxᴇᴄᴜᴛᴏʀ</b>\n<i>ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴄᴏᴅᴇ ᴛᴏ ᴇxᴇᴄᴜᴛᴇ.</i></blockquote>",
            parse_mode=ParseMode.HTML
        )

    cmd = message.text.split(" ", maxsplit=1)[1]
    start = time()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    redirected_output, redirected_error = StringIO(), StringIO()
    sys.stdout, sys.stderr = redirected_output, redirected_error

    try:
        await aexec(cmd, client, message)
    except Exception:
        error = traceback.format_exc()
    else:
        error = None

    sys.stdout, sys.stderr = old_stdout, old_stderr
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()

    result = error or stderr or stdout or "Success"
    output_text = (
        "<blockquote><b>💻 ᴇxᴇᴄᴜᴛɪᴏɴ ʀᴇꜱᴜʟᴛ</b></blockquote>\n"
        f"<pre><code>{result.strip()}</code></pre>"
    )

    if len(output_text) > 4096:
        filename = "output.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.strip())

        end = time()
        await message.reply_document(
            filename,
            caption=f"<blockquote><b>INPUT:</b> <code>{cmd[:100]}</code>\n<b>RUNTIME:</b> <code>{end - start:.2f}s</code></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳", callback_data=f"runtime {end - start:.2f} Seconds", style=ButtonStyle.PRIMARY)]
            ])
        )
        os.remove(filename)
    else:
        end = time()
        await edit_or_reply(
            message,
            text=output_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 ᴄʟᴏꜱᴇ", callback_data=f"forceclose abc|{message.from_user.id}", style=ButtonStyle.DANGER)]
            ])
        )

@Client.on_callback_query(filters.regex(r"^runtime"))
async def runtime_callback(_, cq):
    try:
        _, runtime = cq.data.split(None, 1)
        await cq.answer(runtime, show_alert=True)
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r"^forceclose"))
async def forceclose_callback(_, callback_query):
    try:
        _, data = callback_query.data.strip().split(None, 1)
        _, user_id = data.split("|")
        if callback_query.from_user.id != int(user_id):
            return await callback_query.answer(
                "⚠️ Only the bot owner can close this!", show_alert=True
            )
        await callback_query.message.delete()
        await callback_query.answer()
    except Exception:
        pass

@Client.on_message(filters.command("sh") & filters.user(OWNER_ID))
@Client.on_edited_message(filters.command("sh") & filters.user(OWNER_ID))
async def shellrunner(client: Client, message: Message):
    if len(message.command) < 2:
        return await edit_or_reply(
            message,
            text="<blockquote><b>⚡ ꜱʜᴇʟʟ ᴇxᴇᴄᴜᴛᴏʀ</b>\n<i>ᴇxᴀᴍᴘʟᴇ:</i> <code>/sh ls -la</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    cmd = message.text.split(None, 1)[1]
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        output = (stdout.decode().strip() or stderr.decode().strip()) or "No output"
    except Exception as err:
        output = f"ERROR:\n{err}"

    if len(output) > 4000:
        filename = "output.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output)
        await client.send_document(
            message.chat.id,
            filename,
            caption="<blockquote><b>⚡ ꜱʜᴇʟʟ ᴏᴜᴛᴘᴜᴛ</b></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=message.id,
        )
        os.remove(filename)
    else:
        await edit_or_reply(
            message,
            text=f"<blockquote><b>⚡ ꜱʜᴇʟʟ ᴏᴜᴛᴘᴜᴛ</b></blockquote>\n<pre><code>{output}</code></pre>",
            parse_mode=ParseMode.HTML
        )
