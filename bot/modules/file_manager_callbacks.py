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
        # Format: fm_browse:/path/to/dir:page
        parts = cb.data.split(":", 2)
        path = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
    except (IndexError, ValueError):
        await cb.answer("Error: Invalid callback data.", show_alert=True)
        return

    text, buttons = await build_file_browser(path, page)

    # Add a close button to the main browser view
    back_button_row = -1
    # Find a row with a "Back" button to append to, or just add a new row
    for i, row in enumerate(buttons):
        for button in row:
            if button.callback_data and "providerPanel" in button.callback_data:
                back_button_row = i
                break

    # The generic browser doesn't know the context of which provider panel to return to.
    # For now, we'll just add a generic close button. This will be improved when integrated.
    if back_button_row == -1:
         buttons.append([InlineKeyboardButton("❌ Close", callback_data="close")])


    await edit_message(cb.message, text, InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(pattern=r"^fm_select:"))
async def fm_select_cb(c: Client, cb: CallbackQuery):
    """Callback for selecting a file to show actions."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    try:
        filepath = cb.data.split(":", 1)[1]
        # To get the parent dir for the back button, we need to handle the case where the path is a file
        parent_dir = os.path.dirname(filepath) if os.path.isdir(filepath) else os.path.dirname(os.path.abspath(filepath))

    except IndexError:
        await cb.answer("Error: Invalid file path in callback.", show_alert=True)
        return

    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        await cb.answer("Error: File no longer exists.", show_alert=True)
        # Try to refresh the parent directory view
        text, buttons = await build_file_browser(parent_dir, 0)
        await edit_message(cb.message, text, InlineKeyboardMarkup(buttons))
        return

    filename = os.path.basename(filepath)
    text = f"**Selected File:**\n`{filename}`\n\nChoose an action:"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬇️ Download", callback_data=f"fm_download:{filepath}"),
            InlineKeyboardButton("❌ Delete", callback_data=f"fm_delete_confirm:{filepath}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Browser", callback_data=f"fm_browse:{parent_dir}")
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
        filepath = cb.data.split(":", 1)[1]
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
        filepath = cb.data.split(":", 1)[1]
        parent_dir = os.path.dirname(os.path.abspath(filepath))
    except IndexError:
        await cb.answer("Error: Invalid file path in callback.", show_alert=True)
        return

    filename = os.path.basename(filepath)
    text = f"**⚠️ Are you sure you want to delete this file?**\n\n`{filename}`\n\nThis action cannot be undone."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Delete It", callback_data=f"fm_delete_execute:{filepath}"),
            InlineKeyboardButton("❌ No, Cancel", callback_data=f"fm_select:{filepath}")
        ],
        [
            InlineKeyboardButton("🔙 Back to Browser", callback_data=f"fm_browse:{parent_dir}")
        ]
    ])
    await edit_message(cb.message, text, buttons)

@Client.on_callback_query(filters.regex(pattern=r"^fm_delete_execute:"))
async def fm_delete_execute_cb(c: Client, cb: CallbackQuery):
    """Callback to execute file deletion."""
    if not await check_user(cb.from_user.id, restricted=True):
        return

    try:
        filepath = cb.data.split(":", 1)[1]
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
    text, buttons = await build_file_browser(parent_dir, 0)
    # Add a close button
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close")])
    await edit_message(cb.message, text, InlineKeyboardMarkup(buttons))
