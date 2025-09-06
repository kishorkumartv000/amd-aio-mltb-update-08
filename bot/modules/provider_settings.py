import bot.helpers.translations as lang
import asyncio

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from config import Config

from ..settings import bot_set
from ..helpers.buttons.settings import *
from ..helpers.database.pg_impl import set_db, user_set_db
from ..helpers.tidal.tidal_api import tidalapi

from ..helpers.message import edit_message, check_user
from ..helpers.state import conversation_state
import os
import json


# Custom filter to check if a user is in the tidal NG file import state
async def is_awaiting_tidal_ng_file_filter(_, __, message: Message):
    if not message.from_user:
        return False
    state = await conversation_state.get(message.from_user.id)
    return state and state.get('stage') == "awaiting_tidal_ng_file"

# Apply the custom filter and set a high priority group (-1) to run before the default handlers
@Client.on_message(filters.document & filters.private & filters.create(is_awaiting_tidal_ng_file_filter), group=-1)
async def handle_tidal_ng_config_upload(c: Client, msg: Message):
    user_id = msg.from_user.id
    state = await conversation_state.get(user_id)
    # The state check is now handled by the filter, so we can remove it from here.

    if not msg.document:
        return

    target_dir = state.get('data', {}).get('target_dir')
    if not target_dir:
        await c.send_message(user_id, "❌ An error occurred. The target directory was not set. Please start over.")
        await conversation_state.clear(user_id)
        return

    original_filename = msg.document.file_name
    target_path = os.path.join(target_dir, original_filename)

    progress_msg = await c.send_message(user_id, f"Importing `{original_filename}`...")
    temp_path = None
    try:
        temp_path = await c.download_media(msg)
        os.makedirs(target_dir, exist_ok=True)
        os.replace(temp_path, target_path)
        os.chmod(target_path, 0o666)
        await edit_message(progress_msg, f"✅ **Import Successful!**\nFile `{original_filename}` has been saved to `{target_dir}`.")

    except Exception as e:
        await edit_message(progress_msg, f"❌ **An Error Occurred:**\n`{str(e)}`")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        await conversation_state.clear(user_id)


@Client.on_callback_query(filters.regex(pattern=r"^providerPanel"))
async def provider_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        buttons = []
        # Always show Apple Music button
        buttons.append([
            InlineKeyboardButton("🍎 Apple Music", callback_data="appleP")
        ])

        # Conditionally show other providers
        if bot_set.qobuz:
            buttons.append([
                InlineKeyboardButton(lang.s.QOBUZ, callback_data="qbP")
            ])
        if bot_set.deezer:
            buttons.append([
                InlineKeyboardButton(lang.s.DEEZER, callback_data="dzP")
            ])
        if bot_set.can_enable_tidal:
            buttons.append([
                InlineKeyboardButton(lang.s.TIDAL, callback_data="tdP")
            ])
            buttons.append([
                InlineKeyboardButton("Tidal DL NG", callback_data="tidalNgP")
            ])

        buttons += [
            [InlineKeyboardButton(lang.s.MAIN_MENU_BUTTON, callback_data="main_menu")],
            [InlineKeyboardButton(lang.s.CLOSE_BUTTON, callback_data="close")]
        ]
        
        await edit_message(
            cb.message,
            lang.s.PROVIDERS_PANEL,
            InlineKeyboardMarkup(buttons)
        )


#----------------
# APPLE MUSIC
#----------------
@Client.on_callback_query(filters.regex(pattern=r"^appleP"))
async def apple_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        formats = {
            'alac': 'ALAC',
            'atmos': 'Dolby Atmos'
        }
        current = Config.APPLE_DEFAULT_FORMAT
        formats[current] += ' ✅'
        
        await edit_message(
            cb.message,
            "🍎 **Apple Music Settings**\n\n"
            "Use the buttons below to configure formats, quality, and manage the Wrapper service.\n\n"
            "**Available Formats:**\n"
            "- ALAC: Apple Lossless Audio Codec\n"
            "- Dolby Atmos: Spatial audio experience\n\n"
            "**Current Default Format:**",
            apple_button(formats)
        )


@Client.on_callback_query(filters.regex(pattern=r"^appleF"))
async def apple_format_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        format_type = cb.data.split('_')[1]
        # Update configuration
        set_db.set_variable('APPLE_DEFAULT_FORMAT', format_type)
        Config.APPLE_DEFAULT_FORMAT = format_type
        await apple_cb(c, cb)


@Client.on_callback_query(filters.regex(pattern=r"^appleQ"))
async def apple_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        qualities = {
            'alac': ['192000', '256000', '320000'],
            'atmos': ['2768', '3072', '3456']
        }
        current_format = Config.APPLE_DEFAULT_FORMAT
        current_quality = getattr(Config, f'APPLE_{current_format.upper()}_QUALITY')
        
        # Create quality buttons
        buttons = []
        for quality in qualities[current_format]:
            label = f"{quality} kbps"
            if quality == current_quality:
                label += " ✅"
            buttons.append([InlineKeyboardButton(label, callback_data=f"appleSQ_{current_format}_{quality}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="appleP")])
        
        await edit_message(
            cb.message,
            f"⚙️ **{current_format.upper()} Quality Settings**\n\n"
            "Select the maximum quality for downloads:",
            InlineKeyboardMarkup(buttons)
        )


@Client.on_callback_query(filters.regex(pattern=r"^appleSQ"))
async def apple_set_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        _, format_type, quality = cb.data.split('_')
        # Update configuration
        set_db.set_variable(f'APPLE_{format_type.upper()}_QUALITY', quality)
        setattr(Config, f'APPLE_{format_type.upper()}_QUALITY', quality)
        await apple_quality_cb(c, cb)


# Apple Wrapper: Stop with confirmation
@Client.on_callback_query(filters.regex(pattern=r"^appleStop$"))
async def apple_wrapper_stop_cb(c: Client, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        # Ask for confirmation
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm Stop", callback_data="appleStopConfirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="appleP")]
        ])
        await edit_message(cb.message, "Are you sure you want to stop the Wrapper?", buttons)


@Client.on_callback_query(filters.regex(pattern=r"^appleStopConfirm$"))
async def apple_wrapper_stop_confirm_cb(c: Client, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from config import Config as Cfg
        import asyncio
        await c.answer_callback_query(cb.id, "Stopping wrapper...", show_alert=False)
        try:
            proc = await asyncio.create_subprocess_exec(
                "/bin/bash", Cfg.APPLE_WRAPPER_STOP_PATH,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode(errors='ignore')
            err = stderr.decode(errors='ignore')
            text = "⏹️ Wrapper stop result:\n\n" + (out.strip() or err.strip() or "Done.")
        except Exception as e:
            text = f"❌ Failed to stop wrapper: {e}"
        await edit_message(cb.message, text, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="appleP")]]))


# Apple Wrapper: Setup flow entry (asks for username then password)
@Client.on_callback_query(filters.regex(pattern=r"^appleSetup$"))
async def apple_wrapper_setup_cb(c: Client, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        # Explain flow
        await edit_message(cb.message, "We'll set up the Wrapper. Please send your Apple ID username.\n\nYou can cancel anytime by sending /cancel.", InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="appleP")]]))
        # Mark state for this user
        from ..helpers.state import conversation_state
        # Also clear any other pending flows for safety
        await conversation_state.clear(cb.from_user.id)
        await conversation_state.start(cb.from_user.id, "apple_setup_username", {"chat_id": cb.message.chat.id, "msg_id": cb.message.id})


#----------------
# QOBUZ
#----------------
@Client.on_callback_query(filters.regex(pattern=r"^qbP"))
async def qobuz_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        quality = {5: 'MP3 320', 6: 'Lossless', 7: '24B<=96KHZ', 27: '24B>96KHZ'}
        current = bot_set.qobuz.quality
        quality[current] = quality[current] + '✅'
        try:
            await edit_message(
                cb.message,
                lang.s.QOBUZ_QUALITY_PANEL,
                markup=qb_button(quality)
            )
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^qbQ"))
async def qobuz_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        qobuz = {5: 'MP3 320', 6: 'Lossless', 7: '24B<=96KHZ', 27: '24B>96KHZ'}
        to_set = cb.data.split('_')[1]
        bot_set.qobuz.quality = list(filter(lambda x: qobuz[x] == to_set, qobuz))[0]
        set_db.set_variable('QOBUZ_QUALITY', bot_set.qobuz.quality)
        await qobuz_cb(c, cb)


#----------------
# TIDAL
#----------------
@Client.on_callback_query(filters.regex(pattern=r"^tdP"))
async def tidal_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        await edit_message(
            cb.message,
            lang.s.TIDAL_PANEL,
            tidal_buttons()  # auth and quality button (quality button only if auth already done)
        )


@Client.on_callback_query(filters.regex(pattern=r"^toggleLegacyTidal"))
async def toggle_legacy_tidal_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        bot_set.tidal_legacy_enabled = not bot_set.tidal_legacy_enabled
        status = "ON" if bot_set.tidal_legacy_enabled else "OFF"
        await c.answer_callback_query(
            cb.id,
            f"Legacy Tidal is now {status}",
            show_alert=False
        )
        # Directly edit the message to refresh the buttons
        await edit_message(
            cb.message,
            lang.s.TIDAL_PANEL,
            tidal_buttons()
        )


@Client.on_callback_query(filters.regex(pattern=r"^tdQ"))
async def tidal_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        qualities = {
            'LOW': 'LOW',
            'HIGH': 'HIGH',
            'LOSSLESS': 'LOSSLESS'
        }
        if tidalapi.mobile_hires:
            qualities['HI_RES'] = 'MAX'
        qualities[tidalapi.quality] += '✅'

        await edit_message(
            cb.message,
            lang.s.TIDAL_PANEL,
            tidal_quality_button(qualities)
        )


@Client.on_callback_query(filters.regex(pattern=r"^tdSQ"))
async def tidal_set_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        to_set = cb.data.split('_')[1]

        if to_set == 'spatial':
            # options = ['OFF', 'ATMOS AC3 JOC', 'ATMOS AC4', 'Sony 360RA']
            # assuming atleast tv session is added
            options = ['OFF', 'ATMOS AC3 JOC']
            if tidalapi.mobile_atmos:
                options.append('ATMOS AC4')
            if tidalapi.mobile_atmos or tidalapi.mobile_hires:
                options.append('Sony 360RA')

            try:
                current = options.index(tidalapi.spatial)
            except:
                current = 0

            nexti = (current + 1) % 4
            tidalapi.spatial = options[nexti]
            set_db.set_variable('TIDAL_SPATIAL', options[nexti])
        else:
            qualities = {'LOW': 'LOW', 'HIGH': 'HIGH', 'LOSSLESS': 'LOSSLESS', 'HI_RES': 'MAX'}
            to_set = list(filter(lambda x: qualities[x] == to_set, qualities))[0]
            tidalapi.quality = to_set
            set_db.set_variable('TIDAL_QUALITY', to_set)

        await tidal_quality_cb(c, cb)


# show login button if not logged in
# show refresh button in case logged in exist (both tv and mobile)
@Client.on_callback_query(filters.regex(pattern=r"^tdAuth"))
async def tidal_auth_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        sub = tidalapi.sub_type
        hires = True if tidalapi.mobile_hires else False
        atmos = True if tidalapi.mobile_atmos else False
        tv = True if tidalapi.tv_session else False

        await edit_message(
            cb.message,
            lang.s.TIDAL_AUTH_PANEL.format(sub, hires, atmos, tv),
            tidal_auth_buttons()
        )


@Client.on_callback_query(filters.regex(pattern=r"^tdLogin"))
async def tidal_login_cb(c: Client, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        auth_url, err = await tidalapi.get_tv_login_url()
        if err:
            return await c.answer_callback_query(
                cb.id,
                err,
                True
            )

        await edit_message(
            cb.message,
            lang.s.TIDAL_AUTH_URL.format(auth_url),
            tidal_auth_buttons()
        )

        sub, err = await tidalapi.login_tv()
        if err:
            return await edit_message(
                cb.message,
                lang.s.ERR_LOGIN_TIDAL_TV_FAILED.format(err),
                tidal_auth_buttons()
            )
        if sub:
            bot_set.tidal = tidalapi
            bot_set.clients.append(tidalapi)

            await bot_set.save_tidal_login(tidalapi.tv_session)

            hires = True if tidalapi.mobile_hires else False
            atmos = True if tidalapi.mobile_atmos else False
            tv = True if tidalapi.tv_session else False
            await edit_message(
                cb.message,
                lang.s.TIDAL_AUTH_PANEL.format(sub, hires, atmos, tv) + '\n' + lang.s.TIDAL_AUTH_SUCCESSFULL,
                tidal_auth_buttons()
            )


@Client.on_callback_query(filters.regex(pattern=r"^tdRemove"))
async def tidal_remove_login_cb(c: Client, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        set_db.set_variable("TIDAL_AUTH_DATA", 0, True, None)

        tidalapi.tv_session = None
        tidalapi.mobile_atmos = None
        tidalapi.mobile_hires = None
        tidalapi.sub_type = None
        tidalapi.saved = []

        await tidalapi.session.close()
        bot_set.tidal = None

        await c.answer_callback_query(
            cb.id,
            lang.s.TIDAL_REMOVED_SESSION,
            True
        )

        await tidal_auth_cb(c, cb)


#--------------------
# TIDAL DL NG
#--------------------

# --- Helpers ---
def get_tidal_ng_setting(user_id, key, default_value, is_bool=False):
    val_str = user_set_db.get_user_setting(user_id, key)
    if val_str is None:
        return default_value
    if is_bool:
        return val_str == 'True'
    return val_str

def create_toggle_button(user_id, key, text, default_value, callback_data_prefix):
    is_on = get_tidal_ng_setting(user_id, key, default_value, is_bool=True)
    status = "✅ ON" if is_on else "❌ OFF"
    return [InlineKeyboardButton(f"{text}: {status}", callback_data=f"{callback_data_prefix}_toggle")]

async def handle_toggle_setting(cb, key, text, default_value, back_callback):
    user_id = cb.from_user.id
    current_status = get_tidal_ng_setting(user_id, key, default_value, is_bool=True)
    new_status = not current_status
    user_set_db.set_user_setting(user_id, key, new_status)
    status_text = "Enabled" if new_status else "Disabled"
    await cb.answer(f"{text} {status_text}", show_alert=False)
    await back_callback(None, cb)

# --- Main Menu ---
@Client.on_callback_query(filters.regex(pattern=r"^tidalNgP"))
async def tidal_ng_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        buttons = [
            [
                InlineKeyboardButton("🎧 Audio Settings", callback_data="tidalNg_audio"),
                InlineKeyboardButton("📝 Metadata Settings", callback_data="tidalNg_metadata")
            ],
            [
                InlineKeyboardButton("🗂️ File Settings", callback_data="tidalNg_file"),
                InlineKeyboardButton("🎬 Video Settings", callback_data="tidalNg_video")
            ],
            [
                InlineKeyboardButton("🔑 Login", callback_data="tidalNgLogin"),
                InlineKeyboardButton("🚨 Logout", callback_data="tidalNgLogout")
            ],
            [
                InlineKeyboardButton("📂 Import Config File", callback_data="tidalNg_importFile"),
                InlineKeyboardButton("⚙️ Execute cfg", callback_data="tidal_ng_execute_cfg")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="providerPanel")]
        ]
        await edit_message(
            cb.message,
            "**Tidal NG Settings**\n\n"
            "Configure your download settings for the Tidal NG provider.",
            InlineKeyboardMarkup(buttons)
        )


@Client.on_callback_query(filters.regex(pattern=r"^tidal_ng_execute_cfg$"))
async def tidal_ng_execute_cfg_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from bot.helpers.tidal_ng.handler import TIDAL_DL_NG_CLI_PATH
        msg = await edit_message(cb.message, "⚙️ Executing `tidal-dl-ng cfg`...")

        try:
            process = await asyncio.create_subprocess_exec(
                "python", TIDAL_DL_NG_CLI_PATH, "cfg",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode().strip()
            error = stderr.decode().strip()

            response_text = ""
            if output:
                response_text += f"**Output:**\n```{output}```\n\n"
            if error:
                response_text += f"**Errors:**\n```{error}```"

            if not response_text:
                response_text = "Command executed with no output."

            # Create a back button to return to the Tidal NG settings menu
            back_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]])
            await edit_message(msg, response_text, back_button)

        except Exception as e:
            back_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]])
            await edit_message(msg, f"❌ **An Error Occurred:**\n`{str(e)}`", back_button)


# --- Conversation Handlers ---
@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_importFile$"))
async def tidal_ng_import_file_cb(c, cb: CallbackQuery):
    if not await check_user(cb.from_user.id, restricted=True):
        return

    buttons = [
        [InlineKeyboardButton("main config (`tidal_dl_ng`)", callback_data="tidalNg_setImportDir|main")],
        [InlineKeyboardButton("dev config (`tidal_dl_ng-dev`)", callback_data="tidalNg_setImportDir|dev")],
        [InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]
    ]
    await edit_message(
        cb.message,
        "Please choose the destination directory for your configuration file.",
        InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setImportDir\|"))
async def tidal_ng_set_import_dir_cb(c, cb: CallbackQuery):
    if not await check_user(cb.from_user.id, restricted=True):
        return

    choice = cb.data.split("|")[1]
    if choice == "main":
        target_dir = "/root/.config/tidal_dl_ng/"
    else:
        target_dir = "/root/.config/tidal_dl_ng-dev/"

    if not os.path.exists(target_dir):
        await edit_message(
            cb.message,
            f"The destination directory (`{target_dir}`) does not exist. Shall I create it for you?",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, create it", callback_data=f"tidalNg_createDir|{choice}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="tidalNgP")]
            ])
        )
    else:
        await conversation_state.clear(cb.from_user.id)
        await conversation_state.start(cb.from_user.id, "awaiting_tidal_ng_file", {"target_dir": target_dir})
        await edit_message(
            cb.message,
            "Please upload the file you want to import. You can /cancel anytime.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="tidalNgP")]
            ])
        )

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_createDir\|"))
async def tidal_ng_create_dir_cb(c, cb: CallbackQuery):
    if not await check_user(cb.from_user.id, restricted=True):
        return

    choice = cb.data.split("|")[1]
    if choice == "main":
        target_dir = "/root/.config/tidal_dl_ng/"
    else:
        target_dir = "/root/.config/tidal_dl_ng-dev/"

    try:
        os.makedirs(target_dir, mode=0o777, exist_ok=True)
        await cb.answer("Directory created successfully!", show_alert=False)
        # Now ask for the file
        await conversation_state.clear(cb.from_user.id)
        await conversation_state.start(cb.from_user.id, "awaiting_tidal_ng_file", {"target_dir": target_dir})
        await edit_message(
            cb.message,
            "Please upload the file you want to import. You can /cancel anytime.",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="tidalNgP")]])
        )
    except Exception as e:
        await edit_message(
            cb.message,
            f"❌ **Failed to create directory:**\n`{str(e)}`",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]])
        )

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_tokenSwap$"))
async def tidal_ng_token_swap_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        await conversation_state.clear(cb.from_user.id)
        await conversation_state.start(cb.from_user.id, "awaiting_token_file", {"chat_id": cb.message.chat.id, "msg_id": cb.message.id})
        await edit_message(
            cb.message,
            "Please upload your `token.json` file now.\n\nThis will replace your current token. You can /cancel anytime.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]])
        )

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_settingsSwap$"))
async def tidal_ng_settings_swap_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        await conversation_state.clear(cb.from_user.id)
        await conversation_state.start(cb.from_user.id, "awaiting_settings_file", {"chat_id": cb.message.chat.id, "msg_id": cb.message.id})
        await edit_message(
            cb.message,
            "Please upload your `settings.json` file now.\n\nThis will replace your current base settings. You can /cancel anytime.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]])
        )

# --- Audio Settings ---
@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_audio$"))
async def tidal_ng_audio_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        quality = get_tidal_ng_setting(user_id, 'tidal_ng_quality', "HIGH")
        buttons = [
            [InlineKeyboardButton("Audio Quality", callback_data="tidalNg_qualitySel"), InlineKeyboardButton(f"{quality} ✅", callback_data="tidalNg_qualitySel")],
            create_toggle_button(user_id, 'tidal_ng_replay_gain', "Replay Gain", False, "tidalNg_setReplayGain"),
            [InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]
        ]
        await edit_message(cb.message, "🎧 **Audio Settings**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setReplayGain_"))
async def tidal_ng_set_replay_gain_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_replay_gain', "Replay Gain", False, tidal_ng_audio_cb)

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_qualitySel$"))
async def tidal_ng_quality_sel_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        current_quality = get_tidal_ng_setting(user_id, 'tidal_ng_quality', "HIGH")
        qualities = ["LOW", "HIGH", "LOSSLESS", "HI_RES_LOSSLESS"]
        buttons = []
        for q in qualities:
            buttons.append([InlineKeyboardButton(f"{q}{' ✅' if q == current_quality else ''}", callback_data=f"tidalNg_setQuality_{q}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="tidalNg_audio")])
        await edit_message(cb.message, "**Select Audio Quality**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setQuality_"))
async def tidal_ng_set_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        quality_to_set = "_".join(cb.data.split('_')[2:])
        user_set_db.set_user_setting(user_id, 'tidal_ng_quality', quality_to_set)
        await cb.answer(f"Audio quality set to {quality_to_set}", show_alert=False)
        await tidal_ng_audio_cb(c, cb)

# --- Metadata Settings ---
@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_metadata$"))
async def tidal_ng_metadata_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        cover_dim = get_tidal_ng_setting(user_id, 'tidal_ng_cover_dim', "320")
        buttons = [
            create_toggle_button(user_id, 'tidal_ng_lyrics', "Embed Lyrics", False, "tidalNg_setLyrics"),
            create_toggle_button(user_id, 'tidal_ng_lyrics_file', "Save Lyrics File", False, "tidalNg_setLyricsFile"),
            [InlineKeyboardButton("Cover Art Dimension", callback_data="tidalNg_coverDimSel"), InlineKeyboardButton(f"{cover_dim}px ✅", callback_data="tidalNg_coverDimSel")],
            [InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]
        ]
        await edit_message(cb.message, "📝 **Metadata Settings**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setLyrics_"))
async def tidal_ng_set_lyrics_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_lyrics', "Embed Lyrics", False, tidal_ng_metadata_cb)

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setLyricsFile_"))
async def tidal_ng_set_lyrics_file_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_lyrics_file', "Save Lyrics File", False, tidal_ng_metadata_cb)

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_coverDimSel$"))
async def tidal_ng_cover_dim_sel_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        current_dim = get_tidal_ng_setting(user_id, 'tidal_ng_cover_dim', "320")
        dims = ["320", "640", "1280"]
        buttons = []
        for d in dims:
            buttons.append([InlineKeyboardButton(f"{d}px{' ✅' if d == current_dim else ''}", callback_data=f"tidalNg_setCoverDim_{d}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="tidalNg_metadata")])
        await edit_message(cb.message, "**Select Cover Art Dimension**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setCoverDim_"))
async def tidal_ng_set_cover_dim_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        dim_to_set = cb.data.split('_')[-1]
        user_set_db.set_user_setting(user_id, 'tidal_ng_cover_dim', dim_to_set)
        await cb.answer(f"Cover dimension set to {dim_to_set}px", show_alert=False)
        await tidal_ng_metadata_cb(c, cb)

# --- File Settings ---
@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_file$"))
async def tidal_ng_file_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        buttons = [
            create_toggle_button(user_id, 'tidal_ng_playlist_create', "Create .m3u8 Playlist", False, "tidalNg_setPlaylistCreate"),
            create_toggle_button(user_id, 'tidal_ng_symlink', "Symlink to Track", False, "tidalNg_setSymlink"),
            [InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]
        ]
        await edit_message(cb.message, "🗂️ **File Settings**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setPlaylistCreate_"))
async def tidal_ng_set_playlist_create_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_playlist_create', "Create .m3u8 Playlist", False, tidal_ng_file_cb)

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setSymlink_"))
async def tidal_ng_set_symlink_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_symlink', "Symlink to Track", False, tidal_ng_file_cb)


# --- Video Settings ---
@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_video$"))
async def tidal_ng_video_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        buttons = [
            create_toggle_button(user_id, 'tidal_ng_video_download', "Download Videos", True, "tidalNg_setVideoDownload"),
            create_toggle_button(user_id, 'tidal_ng_video_convert', "Convert to MP4", True, "tidalNg_setVideoConvert"),
            [InlineKeyboardButton("Video Quality", callback_data="tidalNg_videoQualitySel")],
            [InlineKeyboardButton("🔙 Back", callback_data="tidalNgP")]
        ]
        await edit_message(cb.message, "🎬 **Video Settings**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_videoQualitySel$"))
async def tidal_ng_video_quality_sel_cb(c, cb: CallbackQuery):
     if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        current_quality = get_tidal_ng_setting(user_id, 'tidal_ng_video_quality', "480")
        qualities = ["360", "480", "720", "1080"]
        buttons = []
        for q in qualities:
            buttons.append([InlineKeyboardButton(f"{q}p{' ✅' if q == current_quality else ''}", callback_data=f"tidalNg_setVideoQuality_{q}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="tidalNg_video")])
        await edit_message(cb.message, "**Select Video Quality**", InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setVideoQuality_"))
async def tidal_ng_set_video_quality_cb(c, cb: CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        user_id = cb.from_user.id
        quality_to_set = cb.data.split('_')[-1]
        user_set_db.set_user_setting(user_id, 'tidal_ng_video_quality', quality_to_set)
        await cb.answer(f"Video quality set to {quality_to_set}p", show_alert=False)
        await tidal_ng_video_cb(c, cb)

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setVideoDownload_"))
async def tidal_ng_set_video_download_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_video_download', "Download Videos", True, tidal_ng_video_cb)

@Client.on_callback_query(filters.regex(pattern=r"^tidalNg_setVideoConvert_"))
async def tidal_ng_set_video_convert_cb(c, cb: CallbackQuery):
    await handle_toggle_setting(cb, 'tidal_ng_video_convert', "Convert to MP4", True, tidal_ng_video_cb)


@Client.on_callback_query(filters.regex(pattern=r"^tidalNgLogin"))
async def tidal_ng_login_cb(c, cb: CallbackQuery):
    if not await check_user(cb.from_user.id, restricted=True):
        return

    msg = await edit_message(
        cb.message,
        "⏳ **Attempting to log in to Tidal DL NG...**\n\n"
        "Please wait while the bot starts the login process."
    )

    try:
        command = "env PYTHONPATH=/usr/src/app/tidal-dl-ng python cli.py login"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd='/usr/src/app/tidal-dl-ng/tidal_dl_ng'
        )

        # Timeout for the entire login process
        try:
            # We will read stdout line by line
            url_found = False
            while True:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=305.0)
                if not line:
                    break

                output = line.decode().strip()
                if "https://link.tidal.com/" in output:
                    url_found = True
                    await edit_message(
                        msg,
                        f"🔗 **Login URL Detected**\n\n"
                        f"Please visit the following URL to log in. The code will expire in 5 minutes.\n\n"
                        f"`{output}`\n\n"
                        f"The bot is waiting for you to complete the login...",
                    )

                if "The login was successful" in output:
                    await edit_message(
                        msg,
                        f"✅ **Login Successful!**\n\n"
                        f"Your Tidal DL NG credentials have been stored."
                    )
                    await process.wait() # ensure process is finished
                    return

            # If loop breaks and we haven't returned, something went wrong
            stderr_output = await process.stderr.read()
            err_msg = stderr_output.decode().strip()
            await edit_message(
                msg,
                f"❌ **Login Failed**\n\n"
                f"The login process failed. Please try again.\n\n"
                f"**Error:**\n`{err_msg or 'No error message from script.'}`"
            )

        except asyncio.TimeoutError:
            process.kill()
            await edit_message(
                msg,
                "❌ **Login Timed Out**\n\n"
                "You did not complete the login within 5 minutes. Please try again."
            )

    except Exception as e:
        await edit_message(
            msg,
            f"❌ **An Error Occurred**\n\n"
            f"An unexpected error occurred while trying to log in.\n\n"
            f"`{str(e)}`"
        )


@Client.on_callback_query(filters.regex(pattern=r"^tidalNgLogout"))
async def tidal_ng_logout_cb(c, cb: CallbackQuery):
    if not await check_user(cb.from_user.id, restricted=True):
        return

    msg = await edit_message(
        cb.message,
        "⏳ **Attempting to log out from Tidal DL NG...**"
    )

    try:
        command = "env PYTHONPATH=/usr/src/app/tidal-dl-ng python cli.py logout"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd='/usr/src/app/tidal-dl-ng/tidal_dl_ng'
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)

        output = stdout.decode().strip()
        err_msg = stderr.decode().strip()

        if process.returncode == 0 and "successfully logged out" in output:
            await edit_message(
                msg,
                "✅ **Logout Successful!**\n\n"
                "You have been logged out from Tidal DL NG."
            )
        else:
            await edit_message(
                msg,
                f"❌ **Logout Failed**\n\n"
                f"The logout process failed. Please try again.\n\n"
                f"**Error:**\n`{err_msg or output or 'No error message from script.'}`"
            )

    except asyncio.TimeoutError:
        process.kill()
        await edit_message(
            msg,
            "❌ **Logout Timed Out**\n\nPlease try again."
        )
    except Exception as e:
        await edit_message(
            msg,
            f"❌ **An Error Occurred**\n\n"
            f"An unexpected error occurred while trying to log out.\n\n"
            f"`{str(e)}`"
        )
