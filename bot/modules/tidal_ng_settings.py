from __future__ import annotations

import os
import shutil
import time
import json
from typing import Any

from pyrogram import Client, filters
from pyrogram.types import Message

from ..helpers.message import send_message, check_user
from bot.helpers.tidal_ng.handler import TIDAL_DL_NG_SETTINGS_PATH

# Use the same settings path as the handler
JSON_PATH = TIDAL_DL_NG_SETTINGS_PATH

# Define the schema for settings.json based on our analysis
SENSITIVE_KEYS = {} # No sensitive keys identified in settings.json
BOOLEAN_KEYS = {
    "skip_existing",
    "lyrics_embed",
    "lyrics_file",
    "video_download",
    "download_delay",
    "video_convert_mp4",
    "metadata_cover_embed",
    "cover_album_file",
    "extract_flac",
    "symlink_to_track",
    "playlist_create",
    "metadata_replay_gain",
}

CHOICE_KEYS: dict[str, list[str]] = {
    "quality_audio": ["LOW", "HIGH", "LOSSLESS", "HI_RES_LOSSLESS"],
    "quality_video": ["360", "480", "720", "1080"],
}

INTEGER_KEYS = {
    "metadata_cover_dimension",
    "downloads_simultaneous_per_track_max",
    "album_track_num_pad_min",
    "downloads_concurrent_max",
}

# Helper functions adapted for JSON
def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _write_json(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    # atomic replace
    os.replace(tmp_path, path)

def _backup(path: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup_path = f"{path}.bak.{ts}"
    try:
        if os.path.exists(path):
            shutil.copy2(path, backup_path)
    except Exception:
        pass
    return backup_path

# Command Handlers
@Client.on_message(filters.command(["tidal_ng_config", "tncfg"]))
async def tidal_ng_help(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    text = (
        "Tidal NG JSON config control\n\n"
        "Usage:\n"
        "- /tidal_ng_get <key>\n"
        "- /tidal_ng_set <key> <value>\n"
        "- /tidal_ng_toggle <key> (toggles true/false)\n"
        "- /tidal_ng_show [keys...] (space-separated)\n"
        f"Path: {JSON_PATH}\n\n"
        "Example Keys:\n"
        "- quality_audio\n"
        "- quality_video\n"
        "- lyrics_embed\n"
        "- download_base_path (use with quotes)\n"
    )
    await send_message(msg, text)

@Client.on_message(filters.command(["tidal_ng_get"]))
async def tidal_ng_get(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await send_message(msg, "Usage: /tidal_ng_get <key>")
        return
    key = parts[1].strip()
    data = _read_json(JSON_PATH)
    val = data.get(key)

    if val is None:
        await send_message(msg, f"`{key}`: <not set>")
    else:
        await send_message(msg, f"`{key}`: `{val}`")

@Client.on_message(filters.command(["tidal_ng_set"]))
async def tidal_ng_set(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await send_message(msg, "Usage: /tidal_ng_set <key> <value>")
        return
    key = parts[1].strip()
    value_str = parts[2].strip()
    value: Any = value_str

    # Normalize and validate
    key_l = key.lower()
    if key_l in BOOLEAN_KEYS:
        lv = value_str.lower()
        if lv in {"true", "1", "yes", "on"}:
            value = True
        elif lv in {"false", "0", "no", "off"}:
            value = False
        else:
            await send_message(msg, f"Invalid boolean for `{key}`. Use `true` or `false`.")
            return
    elif key_l in CHOICE_KEYS:
        choices = CHOICE_KEYS[key_l]
        if value_str not in choices:
            await send_message(msg, f"Invalid value for `{key}`. Allowed: `{', '.join(choices)}`")
            return
    elif key_l in INTEGER_KEYS:
        try:
            value = int(value_str)
        except ValueError:
            await send_message(msg, f"`{key}` must be an integer.")
            return

    data = _read_json(JSON_PATH)
    if not data:
        await send_message(msg, f"Config file not found at {JSON_PATH}. Please run a download or the `Execute cfg` command first to generate it.")
        return

    _backup(JSON_PATH)
    data[key] = value

    try:
        _write_json(JSON_PATH, data)
    except Exception as e:
        await send_message(msg, f"Failed to write config: {e}")
        return

    await send_message(msg, f"Updated `{key}` to `{value}`.")

@Client.on_message(filters.command(["tidal_ng_toggle"]))
async def tidal_ng_toggle(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await send_message(msg, "Usage: /tidal_ng_toggle <bool-key>")
        return
    key = parts[1].strip()
    key_l = key.lower()
    if key_l not in BOOLEAN_KEYS:
        await send_message(msg, f"`{key}` is not a known boolean key.")
        return

    data = _read_json(JSON_PATH)
    if not data:
        await send_message(msg, f"Config file not found at {JSON_PATH}. Please run a download or the `Execute cfg` command first to generate it.")
        return

    current_val = data.get(key, False)
    new_val = not current_val

    _backup(JSON_PATH)
    data[key] = new_val

    try:
        _write_json(JSON_PATH, data)
    except Exception as e:
        await send_message(msg, f"Failed to write config: {e}")
        return
    await send_message(msg, f"Toggled `{key}` -> `{new_val}`.")

@Client.on_message(filters.command(["tidal_ng_show"]))
async def tidal_ng_show(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return

    data = _read_json(JSON_PATH)
    if not data:
        await send_message(msg, f"Config file not found at {JSON_PATH}. Please run a download or the `Execute cfg` command first to generate it.")
        return

    keys_to_show = msg.text.split()[1:]

    output = ""
    if not keys_to_show:
        # Show all if no specific keys are requested
        output = json.dumps(data, indent=2)
    else:
        subset_data = {k: data.get(k, "<not set>") for k in keys_to_show}
        output = json.dumps(subset_data, indent=2)

    await send_message(msg, f"```json\n{output}\n```")
