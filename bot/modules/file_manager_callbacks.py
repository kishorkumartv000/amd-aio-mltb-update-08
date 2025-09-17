import os
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ..helpers.file_manager import build_file_browser
from ..helpers.message import edit_message, check_user

@Client.on_callback_query(filters.regex(pattern=r"^fm_browse:"))
async def fm_browse_cb(c: Client, cb: CallbackQuery):
    """Callback for browsing directories."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    try:
        # Format: fm_browse:path:page:back_callback
        parts = cb.data.split(":", 3)
        path = parts[1]
        # Handle optional page and back_callback
        page = 0
        back_callback = None
        if len(parts) > 2 and parts[2].isdigit():
            page = int(parts[2])
        if len(parts) > 3:
            back_callback = parts[3]
        elif len(parts) > 2 and not parts[2].isdigit():
             back_callback = parts[2]

    except (IndexError, ValueError):
        await cb.answer("Error: Invalid callback data.", show_alert=True)
        return

    text, buttons = await build_file_browser(path, page, back_callback)
    await edit_message(cb.message, text, InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(pattern=r"^fm_select:"))
async def fm_select_cb(c: Client, cb: CallbackQuery):
    """Callback for selecting a file to show actions."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    try:
        # Format: fm_select:filepath:back_callback
        parts = cb.data.split(":", 2)
        filepath = parts[1]
        back_callback = parts[2] if len(parts) > 2 else None
        parent_dir = os.path.dirname(os.path.abspath(filepath))
    except IndexError:
        await cb.answer("Error: Invalid file path in callback.", show_alert=True)
        return

    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        await cb.answer("Error: File no longer exists.", show_alert=True)
        text, buttons = await build_file_browser(parent_dir, 0, back_callback)
        await edit_message(cb.message, text, InlineKeyboardMarkup(buttons))
        return

    filename = os.path.basename(filepath)
    text = f"**Selected File:**\n`{filename}`\n\nChoose an action:"

    # Propagate the back_callback
    back_browse_cb = f"fm_browse:{parent_dir}:{back_callback}" if back_callback else f"fm_browse:{parent_dir}"
    download_cb = f"fm_download:{filepath}:{back_callback}" if back_callback else f"fm_download:{filepath}"
    delete_cb = f"fm_delete_confirm:{filepath}:{back_callback}" if back_callback else f"fm_delete_confirm:{filepath}"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬇️ Download", callback_data=download_cb),
            InlineKeyboardButton("❌ Delete", callback_data=delete_cb)
        ],
        [
            InlineKeyboardButton("🔙 Back to Browser", callback_data=back_browse_cb)
        ]
    ])
    await edit_message(cb.message, text, buttons)

@Client.on_callback_query(filters.regex(pattern=r"^fm_download:"))
async def fm_download_cb(c: Client, cb: CallbackQuery):
    """Callback to download a selected file."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    await cb.answer("Preparing to send file...", show_alert=False)
    try:
        # Format: fm_download:filepath:back_callback
        filepath = cb.data.split(":", 2)[1]
        if os.path.isfile(filepath):
            await c.send_document(
                chat_id=cb.message.chat.id,
                document=filepath,
                caption=f"**File:**\n`{os.path.basename(filepath)}`"
            )
        else:
            await c.send_message(cb.message.chat.id, "❌ **Error:** File not found or is a directory.")
    except Exception as e:
        await c.send_message(cb.message.chat.id, f"❌ **Error:** An error occurred while sending the file:\n`{e}`")


@Client.on_callback_query(filters.regex(pattern=r"^fm_delete_confirm:"))
async def fm_delete_confirm_cb(c: Client, cb: CallbackQuery):
    """Callback to confirm file deletion."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    try:
        # Format: fm_delete_confirm:filepath:back_callback
        parts = cb.data.split(":", 2)
        filepath = parts[1]
        back_callback = parts[2] if len(parts) > 2 else None
        parent_dir = os.path.dirname(os.path.abspath(filepath))
    except IndexError:
        await cb.answer("Error: Invalid file path in callback.", show_alert=True)
        return

    filename = os.path.basename(filepath)
    text = f"**⚠️ Are you sure you want to delete this file?**\n\n`{filename}`\n\nThis action cannot be undone."

    # Propagate back_callback
    execute_cb = f"fm_delete_execute:{filepath}:{back_callback}" if back_callback else f"fm_delete_execute:{filepath}"
    select_cb = f"fm_select:{filepath}:{back_callback}" if back_callback else f"fm_select:{filepath}"
    browse_cb = f"fm_browse:{parent_dir}:{back_callback}" if back_callback else f"fm_browse:{parent_dir}"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Delete It", callback_data=execute_cb),
            InlineKeyboardButton("❌ No, Cancel", callback_data=select_cb)
        ],
        [
            InlineKeyboardButton("🔙 Back to Browser", callback_data=browse_cb)
        ]
    ])
    await edit_message(cb.message, text, buttons)

@Client.on_callback_query(filters.regex(pattern=r"^fm_delete_execute:"))
async def fm_delete_execute_cb(c: Client, cb: CallbackQuery):
    """Callback to execute file deletion."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    try:
        # Format: fm_delete_execute:filepath:back_callback
        parts = cb.data.split(":", 2)
        filepath = parts[1]
        back_callback = parts[2] if len(parts) > 2 else None
        parent_dir = os.path.dirname(os.path.abspath(filepath))
    except IndexError:
        await cb.answer("Error: Invalid file path in callback.", show_alert=True)
        return

    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
            await cb.answer("✅ File deleted successfully.", show_alert=False)
        else:
            await cb.answer("File not found. It may have already been deleted.", show_alert=True)
    except Exception as e:
        await cb.answer(f"❌ Error deleting file: {e}", show_alert=True)

    # Refresh the file browser to show the updated file list
    text, buttons = await build_file_browser(parent_dir, 0, back_callback)
    await edit_message(cb.message, text, InlineKeyboardMarkup(buttons))
