import os
import json
import asyncio
import shutil
from config import Config
from ..message import edit_message, send_message
from bot.logger import LOGGER
from ..database.pg_impl import user_set_db, download_history
from bot.helpers.utils import (
    extract_audio_metadata,
    extract_video_metadata,
)
from bot.helpers.uploader import track_upload, album_upload, playlist_upload, music_video_upload
import re

# Define the path to the tidal-dl-ng CLI script
TIDAL_DL_NG_CLI_PATH = "/usr/src/app/tidal-dl-ng/tidal_dl_ng/cli.py"
# Define the path to the settings.json for the CLI tool
TIDAL_DL_NG_SETTINGS_PATH = "/root/.config/tidal_dl_ng/settings.json"

async def log_progress(stream, bot_msg, user):
    """
    Reads a stream (stdout/stderr) from the subprocess and updates the Telegram message.
    """
    while True:
        line = await stream.readline()
        if not line:
            break

        output = line.decode('utf-8').strip()
        LOGGER.info(f"[TidalDL-NG] {output}")

        if output:
            try:
                await edit_message(bot_msg, f"```\n{output}\n```")
            except Exception:
                pass

def get_content_id_from_url(url: str) -> str:
    """Extracts the content ID from a Tidal URL."""
    match = re.search(r'/(track|album|playlist|video)/(\d+)', url)
    return match.group(2) if match else "unknown"

async def start_tidal_ng(link: str, user: dict, options: dict = None):
    """
    Handles downloads using the tidal-dl-ng CLI tool, and then uploads the result.
    """
    bot_msg = user.get('bot_msg')
    original_settings = None
    final_download_path = None
    is_temp_path = False

    try:
        # --- One-time setup & Initial Read ---
        if not os.path.exists(TIDAL_DL_NG_SETTINGS_PATH):
            LOGGER.info("Tidal NG settings file not found. Running one-time setup...")
            await edit_message(bot_msg, "Tidal NG not yet configured. Performing one-time setup...")
            setup_cmd = ["python", TIDAL_DL_NG_CLI_PATH, "cfg"]
            process = await asyncio.create_subprocess_exec(*setup_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Tidal NG one-time setup failed.")
            LOGGER.info("Tidal NG one-time setup successful.")
            await asyncio.sleep(1)

        with open(TIDAL_DL_NG_SETTINGS_PATH, 'r') as f:
            original_settings = json.load(f)

        # --- Determine Download Path ---
        task_specific_path = os.path.join(Config.DOWNLOAD_BASE_DIR, str(user.get('user_id')), user.get('task_id'))
        if Config.TIDAL_NG_DOWNLOAD_PATH:
            final_download_path = Config.TIDAL_NG_DOWNLOAD_PATH
        elif original_settings.get('download_base_path') and original_settings['download_base_path'] != '~/download':
            final_download_path = original_settings['download_base_path']
        else:
            final_download_path = task_specific_path
            is_temp_path = True

        os.makedirs(final_download_path, exist_ok=True)

        # --- Apply Settings ---
        new_settings = original_settings.copy()
        new_settings['download_base_path'] = final_download_path

        def apply_user_setting(settings_dict, user_id, db_key, json_key, is_bool=False, is_int=False):
            value_str = user_set_db.get_user_setting(user_id, db_key)
            if value_str is not None:
                value = value_str
                if is_bool: value = value_str == 'True'
                elif is_int:
                    try: value = int(value_str)
                    except ValueError: return
                settings_dict[json_key] = value
                LOGGER.info(f"Applying user setting for {user_id}: {json_key} = {value}")

        user_id = user.get('user_id')
        if user_id:
            # Apply all settings...
            apply_user_setting(new_settings, user_id, 'tidal_ng_quality', 'quality_audio')
            apply_user_setting(new_settings, user_id, 'tidal_ng_lyrics', 'lyrics_embed', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_replay_gain', 'metadata_replay_gain', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_lyrics_file', 'lyrics_file', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_playlist_create', 'playlist_create', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_cover_dim', 'metadata_cover_dimension', is_int=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_video_quality', 'quality_video')
            apply_user_setting(new_settings, user_id, 'tidal_ng_symlink', 'symlink_to_track', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_video_convert', 'video_convert_mp4', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_video_download', 'video_download', is_bool=True)

        with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
            json.dump(new_settings, f, indent=4)

        # --- Execute Download ---
        await edit_message(bot_msg, "🚀 Starting Tidal NG download...")
        cmd = ["python", TIDAL_DL_NG_CLI_PATH, "dl", link]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await asyncio.gather(log_progress(process.stdout, bot_msg, user), log_progress(process.stderr, bot_msg, user))
        await process.wait()

        # --- DIAGNOSTIC LOGGING ---
        LOGGER.info(f"Tidal-NG: Download process finished. Checking for files in path: {final_download_path}")
        try:
            ls_proc = await asyncio.create_subprocess_shell(
                f"ls -lR '{final_download_path}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await ls_proc.communicate()
            LOGGER.info(f"Tidal-NG: Directory listing for '{final_download_path}':\n{stdout.decode().strip()}")
            if stderr:
                LOGGER.error(f"Tidal-NG: Error listing directory: {stderr.decode().strip()}")
        except Exception as ls_err:
            LOGGER.error(f"Tidal-NG: Failed to list directory contents: {ls_err}")
        # --- END DIAGNOSTIC LOGGING ---

        if process.returncode != 0:
            raise Exception("Tidal-NG download process failed.")

        # --- Process and Upload ---
        await edit_message(bot_msg, "📥 Download complete. Processing files...")

        downloaded_files = []
        for root, _, files in os.walk(final_download_path):
            for file in files:
                downloaded_files.append(os.path.join(root, file))

        if not downloaded_files:
            raise Exception("No files were downloaded.")

        items = []
        for file_path in downloaded_files:
            try:
                if file_path.lower().endswith(('.mp4', '.m4v')):
                    metadata = await extract_video_metadata(file_path)
                else:
                    metadata = await extract_audio_metadata(file_path)
                metadata['filepath'] = file_path
                metadata['provider'] = 'Tidal NG'
                items.append(metadata)
            except Exception as e:
                LOGGER.error(f"Metadata extraction failed for {file_path}: {str(e)}")

        if not items:
            raise Exception("Metadata extraction failed for all downloaded files.")

        # Determine content type
        content_type = "track" # Default
        if len(items) > 1:
            if any(item.get('album') for item in items) and len(set(item.get('album') for item in items)) == 1:
                content_type = "album"
            else:
                content_type = "playlist"
        elif items[0]['filepath'].lower().endswith(('.mp4', '.m4v')):
            content_type = "video"

        # Prepare metadata for uploader functions
        upload_meta = {
            'success': True, 'type': content_type, 'items': items,
            'folderpath': final_download_path, 'provider': 'Tidal NG',
            'title': items[0].get('album') if content_type == 'album' else items[0].get('title'),
            'artist': items[0].get('artist'), 'poster_msg': bot_msg
        }

        # Record in history
        content_id = get_content_id_from_url(link)
        download_history.record_download(
            user_id=user_id, provider='Tidal NG', content_type=content_type,
            content_id=content_id, title=upload_meta['title'],
            artist=upload_meta['artist'], quality=new_settings.get('quality_audio', 'N/A')
        )

        # Call the appropriate uploader
        if content_type == 'track':
            await track_upload(items[0], user)
        elif content_type == 'video':
            await music_video_upload(items[0], user)
        elif content_type == 'album':
            await album_upload(upload_meta, user)
        elif content_type == 'playlist':
            await playlist_upload(upload_meta, user)

        # If a temporary, task-specific directory was used, clean it up.
        # For albums/playlists, the uploader already deleted the folder.
        # For single tracks/videos, the uploader only deleted the file, so we delete the folder here.
        if is_temp_path and content_type in ['track', 'video']:
            if os.path.exists(final_download_path):
                LOGGER.info(f"Tidal NG: Cleaning up temporary task folder: {final_download_path}")
                shutil.rmtree(final_download_path, ignore_errors=True)

    except Exception as e:
        LOGGER.error(f"An error occurred in start_tidal_ng: {e}", exc_info=True)
        await edit_message(bot_msg, f"❌ **Fatal Error:** An unexpected error occurred: {e}")
        # Final cleanup attempt only on temporary directories
        if is_temp_path and final_download_path and os.path.exists(final_download_path):
            shutil.rmtree(final_download_path, ignore_errors=True)

    finally:
        if original_settings:
            try:
                with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
                    json.dump(original_settings, f, indent=4)
                LOGGER.info("Tidal-NG settings.json restored to original state.")
            except Exception as e:
                LOGGER.error(f"Failed to restore Tidal-NG settings.json: {e}")
