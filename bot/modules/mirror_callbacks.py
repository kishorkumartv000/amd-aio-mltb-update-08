import shutil
import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot.logger import LOGGER

@Client.on_callback_query(filters.regex(pattern=r"^mirror_cleanup\|"))
async def mirror_cleanup_cb(c: Client, cb: CallbackQuery):
    """
    Callback handler to clean up downloaded files after user is done.
    """
    try:
        path_to_delete = cb.data.split("|", 1)[1]

        LOGGER.info(f"User {cb.from_user.id} chose to delete files at: {path_to_delete}")

        # Use shutil.rmtree for directories, os.remove for files
        try:
            if os.path.isdir(path_to_delete):
                await asyncio.to_thread(shutil.rmtree, path_to_delete)
            else:
                await asyncio.to_thread(os.remove, path_to_delete)
        except Exception as e:
            LOGGER.error(f"Error during cleanup: {e}")
            # Still try to edit the message
            pass

        await cb.edit_message_text("✅ Files have been deleted from the server.")
        await cb.answer("Cleanup complete!", show_alert=False)

    except Exception as e:
        LOGGER.error(f"Error in mirror_cleanup_cb: {e}")
        try:
            await cb.answer("Error during cleanup.", show_alert=True)
        except Exception:
            pass

from bot.mirror.modules.mirror_leech import mirror
from types import SimpleNamespace

@Client.on_callback_query(filters.regex(pattern=r"^mirror_upload\|"))
async def mirror_upload_cb(c: Client, cb: CallbackQuery):
    """
    Callback handler to start a mirror/upload task for a local path.
    This function constructs a fake message object to pass to the mirror bot's
    existing command-parsing logic.
    """
    try:
        path_to_upload = cb.data.split("|", 1)[1]
        LOGGER.info(f"User {cb.from_user.id} chose to upload files from: {path_to_upload}")

        # Construct a fake message
        cmd = f"/mirror_mirror {path_to_upload}"

        # Create a mock message object that has the attributes the listener expects
        mock_message = SimpleNamespace()
        mock_message.text = cmd
        mock_message.from_user = cb.from_user
        mock_message.chat = cb.message.chat
        mock_message.id = cb.message.id
        mock_message.reply_to_message = cb.message.reply_to_message

        await cb.edit_message_text(f"✅ Cloud upload initiated for `{path_to_upload}`.\nThe status will appear in a new message.")
        await cb.answer("Upload Started!", show_alert=False)

        # Start the mirror task by calling the standard mirror command handler
        await mirror(c, mock_message)

        # The listener will now handle the upload and cleanup of the original path.
        # We don't need to do anything else here.

    except Exception as e:
        LOGGER.error(f"Error in mirror_upload_cb: {e}")
        try:
            await cb.answer("Error during upload initiation.", show_alert=True)
        except Exception:
            pass
