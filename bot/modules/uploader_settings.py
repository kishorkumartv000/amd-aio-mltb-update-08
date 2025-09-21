from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot import CMD
from ..helpers.database.pg_impl import user_set_db

@Client.on_message(filters.command(["uploadersettings", "usettings"]))
async def uploader_settings_command(client: Client, message: Message):
    """
    Main command to access uploader settings.
    """
    user_id = message.from_user.id

    # Fetch current default uploader
    default_uploader, _ = user_set_db.get_user_setting(user_id, 'default_uploader')
    if not default_uploader:
        default_uploader = "Telegram" # Default if not set

    text = f"⚙️ **Uploader Settings**\n\n"
    text += f"Here you can configure your upload destinations.\n\n"
    text += f"**Current Default Uploader:** `{default_uploader.capitalize()}`"

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⬆️ Set Default Uploader", callback_data="us_set_default"),
            ],
            [
                InlineKeyboardButton("🔐 GDrive Settings", callback_data="us_gdrive"),
                InlineKeyboardButton("☁️ Rclone Settings", callback_data="us_rclone"),
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="us_close"),
            ]
        ]
    )

    await message.reply_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^us_"))
async def uploader_settings_callbacks(client: Client, callback_query):
    """
    Handle callbacks from the uploader settings panel.
    """
    data = callback_query.data

    if data == "us_close":
        await callback_query.message.delete()
    elif data == "us_set_default":
        # This will show the options to change the default uploader
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✈️ Telegram", callback_data="us_set_default_telegram"),
                    InlineKeyboardButton("🔐 Google Drive", callback_data="us_set_default_gdrive"),
                    InlineKeyboardButton("☁️ Rclone", callback_data="us_set_default_rclone"),
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="us_back_main"),
                ]
            ]
        )
        await callback_query.message.edit_text("Select your default upload destination:", reply_markup=buttons)

    elif data.startswith("us_set_default_"):
        user_id = callback_query.from_user.id
        new_default = data.split("_")[-1]
        user_set_db.set_user_setting(user_id, 'default_uploader', new_default)
        await callback_query.answer(f"Default uploader set to {new_default.capitalize()}", show_alert=True)
        # Refresh the main settings panel
        await uploader_settings_command(client, callback_query.message)

    elif data == "us_back_main":
        # Refresh the main settings panel by calling the original command function
        await uploader_settings_command(client, callback_query.message)

    elif data == "us_gdrive":
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⬆️ Upload token.pickle", callback_data="us_gdrive_upload"),
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="us_back_main"),
                ]
            ]
        )
        await callback_query.message.edit_text("GDrive Settings:", reply_markup=buttons)

    elif data == "us_gdrive_upload":
        await callback_query.answer("Please reply to my next message with your token.pickle file.", show_alert=True)
        await callback_query.message.reply_text("Send your `token.pickle` file here. This message will be used to identify your reply.")

    elif data == "us_rclone":
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⬆️ Upload rclone.conf", callback_data="us_rclone_upload"),
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="us_back_main"),
                ]
            ]
        )
        await callback_query.message.edit_text("Rclone Settings:", reply_markup=buttons)

    elif data == "us_rclone_upload":
        await callback_query.answer("Please reply to my next message with your rclone.conf file.", show_alert=True)
        await callback_query.message.reply_text("Send your `rclone.conf` file here. This message will be used to identify your reply.")

    else:
        await callback_query.answer("Not implemented yet.", show_alert=True)

@Client.on_message(filters.document & filters.reply)
async def handle_config_uploads(client: Client, message: Message):
    """
    Handles the upload of config files like rclone.conf and token.pickle.
    """
    if not message.reply_to_message or not message.reply_to_message.text:
        return

    user_id = message.from_user.id
    reply_text = message.reply_to_message.text

    if "rclone.conf" in reply_text:
        setting_name = "rclone_config"
        success_message = "✅ `rclone.conf` has been saved successfully."
    elif "token.pickle" in reply_text:
        setting_name = "gdrive_token"
        success_message = "✅ `token.pickle` has been saved successfully."
    else:
        return

    file = await message.download(in_memory=True)
    file_content = file.read()

    user_set_db.set_user_setting(user_id, setting_name, file_content, is_blob=True)

    await message.reply_text(success_message)
