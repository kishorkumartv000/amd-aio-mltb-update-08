import os
from config import Config

def get_tidal_ng_download_base_path(user: dict, original_settings: dict) -> (str, bool):
    """
    Determines the download path for Tidal NG downloads.
    Returns the final download path and a boolean indicating if it's a temporary path.
    """
    task_specific_path = os.path.join(Config.DOWNLOAD_BASE_DIR, str(user.get('user_id')), user.get('task_id'))
    is_temp_path = False

    if Config.TIDAL_NG_DOWNLOAD_PATH:
        final_download_path = Config.TIDAL_NG_DOWNLOAD_PATH
    elif original_settings.get('download_base_path') and original_settings['download_base_path'] != '~/download':
        final_download_path = original_settings['download_base_path']
    else:
        final_download_path = task_specific_path
        is_temp_path = True

    os.makedirs(final_download_path, exist_ok=True)

    return final_download_path, is_temp_path
