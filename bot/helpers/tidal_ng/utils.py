import os
import json
from bot.logger import LOGGER

SETTINGS_PATH = "/root/.config/tidal_dl_ng/settings.json"

def get_tidal_ng_download_base_path() -> str:
    """
    Reads the current download_base_path from Tidal DL NG settings.json.
    - Expands ~ to full user directory
    - Falls back to ~/download if missing or error
    """
    try:
        # Environment override for Docker-based deployments (supports legacy name)
        override = os.environ.get("TIDAL_NG_DOWNLOAD_BASE_PATH") or os.environ.get("TIDAL_NG_DOWNLOAD_PATH")
        if override:
            return os.path.expanduser(override)
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)

        raw_path = settings.get("download_base_path", "~/download")
        return os.path.expanduser(raw_path)

    except FileNotFoundError:
        LOGGER.error(f"Tidal NG settings.json not found at {SETTINGS_PATH}. Using fallback '~/download'.")
        return os.path.expanduser("~/download")

    except json.JSONDecodeError as e:
        LOGGER.error(f"Error parsing Tidal NG settings.json: {e}")
        return os.path.expanduser("~/download")

    except Exception as e:
        LOGGER.error(f"Unexpected error reading Tidal NG settings.json: {e}")
        return os.path.expanduser("~/download")
