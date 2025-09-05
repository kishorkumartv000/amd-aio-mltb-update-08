import os
import json

SETTINGS_PATH = "/root/.config/tidal_dl_ng/settings.json"

def get_tidal_ng_download_base_path():
    """
    Read the current download_base_path from Tidal DL NG settings.json and expand ~.
    Returns the absolute download base path used by Tidal DL NG.
    """
    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)
    return os.path.expanduser(settings.get("download_base_path", "~/download"))
