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
from bot.helpers.tidal_ng.utils import get_tidal_ng_download_base_path
import re

# Define the path to the tidal-dl-ng CLI script
TIDAL_DL_NG_CLI_PATH = "/usr/src/app/tidal-dl-ng/tidal_dl_ng/cli.py"
# Define the path to the settings.json for the CLI tool
TIDAL_DL_NG_SETTINGS_PATH = "/root/.config/tidal_dl_ng/settings.json"


async def log_progress(stream, bot_msg, user):
    """Reads a stream (stdout/stderr) from the subprocess and updates the Telegram message."""
    while True:
        line = await stream.readline()
        if not line:
            break
        output = line.decode("utf-8").strip()
        LOGGER.info(f"[TidalDL-NG] {output}")
        if output:
            try:
                await edit_message(bot_msg, f"```\n{output}\n```")
            except Exception:
                pass


def get_content_id_from_url(url: str) -> str:
    """Extracts the content ID from a Tidal URL."""
    match = re.search(r"/(track|album|playlist|video)/(\d+)", url)
    return match.group(2) if match else "unknown"


async def start_tidal_ng(link: str, user: dict, options: dict = None):
    """
    Handles downloads using the tidal-dl-ng CLI tool, and then uploads the result.
    """
    bot_msg = user.get("bot_msg")
    original_settings = None
    is_temp_path = False

    try:
        # Read the user's settings file. If it doesn't exist, start with an empty dict.
        try:
            with open(TIDAL_DL_NG_SETTINGS_PATH, "r") as f:
                original_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            original_settings = {}

        # --- Determine Download Path ---
        task_specific_path = os.path.join(
            Config.DOWNLOAD_BASE_DIR, str(user.get("user_id")), user.get("task_id")
        )
        if Config.TIDAL_NG_DOWNLOAD_PATH:
            final_download_path = Config.TIDAL_NG_DOWNLOAD_PATH
        elif original_settings.get("download_base_path") and original_settings["download_base_path"] != "~/download":
            final_download_path = original_settings["download_base_path"]
        else:
            final_download_path = task_specific_path
            is_temp_path = True

        os.makedirs(final_download_path, exist_ok=True)

        # --- Apply Temporary Settings ---
        # The user now controls the settings.json file directly via commands.
        # We only need to inject the per-task download path and the ffmpeg path.
        new_settings = original_settings.copy()
        new_settings["download_base_path"] = final_download_path
        new_settings["path_binary_ffmpeg"] = "/usr/bin/ffmpeg"

        with open(TIDAL_DL_NG_SETTINGS_PATH, "w") as f:
            json.dump(new_settings, f, indent=4)

        # --- Execute Download ---
        await edit_message(bot_msg, "🚀 Starting Tidal NG download...")
        cmd = ["python", TIDAL_DL_NG_CLI_PATH, "dl", link]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.gather(
            log_progress(process.stdout, bot_msg, user),
            log_progress(process.stderr, bot_msg, user),
        )
        await process.wait()

        if process.returncode != 0:
            raise Exception("Tidal-NG download process failed.")

        # --- Smart Path: Always re-read from settings.json after download ---
        final_download_path = get_tidal_ng_download_base_path()
        LOGGER.info(f"Tidal-NG: Using download path {final_download_path}")

        # --- Collect Files ---
        await edit_message(bot_msg, "📥 Download complete. Processing files...")
        downloaded_files = []
        for root, _, files in os.walk(final_download_path):
            for file in files:
                downloaded_files.append(os.path.join(root, file))

        if not downloaded_files:
            raise Exception("No files were downloaded.")

        # --- Metadata Extraction ---
        items = []
        for file_path in downloaded_files:
            try:
                if file_path.lower().endswith((".mp4", ".m4v")):
                    metadata = await extract_video_metadata(file_path)
                else:
                    metadata = await extract_audio_metadata(file_path)
                metadata["filepath"] = file_path
                metadata["provider"] = "Tidal NG"
                items.append(metadata)
            except Exception as e:
                LOGGER.error(f"Metadata extraction failed for {file_path}: {str(e)}")

        if not items:
            raise Exception("Metadata extraction failed for all downloaded files.")

        # --- Determine Content Type ---
        content_type = "track"
        if len(items) > 1:
            if any(item.get("album") for item in items) and len(set(item.get("album") for item in items)) == 1:
                content_type = "album"
            else:
                content_type = "playlist"
        elif items[0]["filepath"].lower().endswith((".mp4", ".m4v")):
            content_type = "video"

        # --- Prepare Metadata for Uploader ---
        upload_meta = {
            "success": True,
            "type": content_type,
            "items": items,
            "folderpath": final_download_path,
            "provider": "Tidal NG",
            "title": items[0].get("album") if content_type == "album" else items[0].get("title"),
            "artist": items[0].get("artist"),
            "poster_msg": bot_msg,
        }

        # --- Record History ---
        content_id = get_content_id_from_url(link)
        download_history.record_download(
            user_id=user_id,
            provider="Tidal NG",
            content_type=content_type,
            content_id=content_id,
            title=upload_meta["title"],
            artist=upload_meta["artist"],
            quality=new_settings.get("quality_audio", "N/A"),
        )

        # --- Upload ---
        if content_type == "track":
            await track_upload(items[0], user)
        elif content_type == "video":
            await music_video_upload(items[0], user)
        elif content_type == "album":
            await album_upload(upload_meta, user)
        elif content_type == "playlist":
            await playlist_upload(upload_meta, user)

        # --- Cleanup ---
        if is_temp_path and content_type in ["track", "video"]:
            if os.path.exists(final_download_path):
                LOGGER.info(f"Tidal NG: Cleaning up temporary task folder: {final_download_path}")
                shutil.rmtree(final_download_path, ignore_errors=True)

    except Exception as e:
        LOGGER.error(f"An error occurred in start_tidal_ng: {e}", exc_info=True)
        await edit_message(bot_msg, f"❌ **Fatal Error:** {e}")
        if is_temp_path and os.path.exists(final_download_path):
            shutil.rmtree(final_download_path, ignore_errors=True)

    finally:
        if original_settings:
            try:
                with open(TIDAL_DL_NG_SETTINGS_PATH, "w") as f:
                    json.dump(original_settings, f, indent=4)
                LOGGER.info("Tidal-NG settings.json restored to original state.")
            except Exception as e:
                LOGGER.error(f"Failed to restore Tidal-NG settings.json: {e}")
