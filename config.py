import os
import logging
from os import getenv
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger(__name__)

if not os.environ.get("ENV"):
    load_dotenv('.env', override=True)

class Config:
    # =====================================================================================
    #                                 SHARED CONFIGURATION
    # =====================================================================================
    # Telegram Configuration
    TG_BOT_TOKEN      = getenv("TG_BOT_TOKEN")
    APP_ID            = int(getenv("APP_ID"))
    API_HASH          = getenv("API_HASH")
    BOT_USERNAME      = getenv("BOT_USERNAME")
    OWNER_ID          = int(getenv("OWNER_ID")) # Both bots used this, so it's shared
    
    # Database Configuration
    DATABASE_URL      = getenv("DATABASE_URL")
    DATABASE_TYPE     = getenv("DATABASE_TYPE", "postgres").lower()
    MONGODB_DATABASE  = getenv("MONGODB_DATABASE", None)

    # User Management
    ADMINS            = set(int(x) for x in getenv("ADMINS", "").replace(",", " ").split()) if getenv("ADMINS") else set()
    SUDO_USERS        = set(int(x) for x in getenv("SUDO_USERS", "").replace(",", " ").split()) if getenv("SUDO_USERS") else set()

    # =====================================================================================
    #                                 MUSIC BOT CONFIGURATION
    # =====================================================================================
    MUSIC_UPLOAD_MODE       = getenv("MUSIC_UPLOAD_MODE", "Telegram")
    MUSIC_WORK_DIR          = getenv("MUSIC_WORK_DIR", "./bot/")
    MUSIC_DOWNLOADS_FOLDER  = getenv("MUSIC_DOWNLOADS_FOLDER", "DOWNLOADS")
    MUSIC_DOWNLOAD_BASE_DIR = getenv("MUSIC_DOWNLOAD_BASE_DIR", os.path.join(MUSIC_WORK_DIR, MUSIC_DOWNLOADS_FOLDER))
    MUSIC_PLAYLIST_NAME_FORMAT = getenv("MUSIC_PLAYLIST_NAME_FORMAT", "{title} - Playlist")
    MUSIC_TRACK_NAME_FORMAT    = getenv("MUSIC_TRACK_NAME_FORMAT", "{title} - {artist}")
    MUSIC_RCLONE_CONFIG     = getenv("MUSIC_RCLONE_CONFIG")
    MUSIC_RCLONE_DEST       = getenv("MUSIC_RCLONE_DEST")
    MUSIC_INDEX_LINK        = getenv("MUSIC_INDEX_LINK")
    MUSIC_MAX_WORKERS       = int(getenv("MUSIC_MAX_WORKERS", 5))
    MUSIC_BOT_PUBLIC        = getenv("MUSIC_BOT_PUBLIC", "False").lower() == 'true'
    MUSIC_ANTI_SPAM         = getenv("MUSIC_ANTI_SPAM", "OFF")
    MUSIC_ART_POSTER        = getenv("MUSIC_ART_POSTER", "False").lower() == 'true'
    MUSIC_PLAYLIST_SORT     = getenv("MUSIC_PLAYLIST_SORT", "False").lower() == 'true'
    MUSIC_ARTIST_BATCH_UPLOAD = getenv("MUSIC_ARTIST_BATCH_UPLOAD", "False").lower() == 'true'
    MUSIC_PLAYLIST_CONCURRENT = getenv("MUSIC_PLAYLIST_CONCURRENT", "False").lower() == 'true'
    MUSIC_PLAYLIST_LINK_DISABLE = getenv("MUSIC_PLAYLIST_LINK_DISABLE", "False").lower() == 'true'
    MUSIC_ALBUM_ZIP         = getenv("MUSIC_ALBUM_ZIP", "False").lower() == 'true'
    MUSIC_PLAYLIST_ZIP      = getenv("MUSIC_PLAYLIST_ZIP", "False").lower() == 'true'
    MUSIC_ARTIST_ZIP        = getenv("MUSIC_ARTIST_ZIP", "False").lower() == 'true'
    MUSIC_RCLONE_LINK_OPTIONS = getenv("MUSIC_RCLONE_LINK_OPTIONS", "Index")
    MUSIC_EXTRACT_EMBEDDED_COVER = getenv("MUSIC_EXTRACT_EMBEDDED_COVER", "False").lower() == 'true'

    # --- Provider Specific ---
    MUSIC_QOBUZ_EMAIL       = getenv("MUSIC_QOBUZ_EMAIL")
    MUSIC_QOBUZ_PASSWORD    = getenv("MUSIC_QOBUZ_PASSWORD")
    MUSIC_QOBUZ_USER        = int(getenv("MUSIC_QOBUZ_USER", 0))
    MUSIC_QOBUZ_TOKEN       = getenv("MUSIC_QOBUZ_TOKEN")
    MUSIC_QOBUZ_QUALITY     = int(getenv("MUSIC_QOBUZ_QUALITY", 0))
    MUSIC_DEEZER_EMAIL      = getenv("MUSIC_DEEZER_EMAIL")
    MUSIC_DEEZER_PASSWORD   = getenv("MUSIC_DEEZER_PASSWORD")
    MUSIC_DEEZER_BF_SECRET  = getenv("MUSIC_DEEZER_BF_SECRET")
    MUSIC_DEEZER_ARL        = getenv("MUSIC_DEEZER_ARL")
    MUSIC_ENABLE_TIDAL      = getenv("MUSIC_ENABLE_TIDAL", "False").lower() == 'true'
    MUSIC_TIDAL_MOBILE      = getenv("MUSIC_TIDAL_MOBILE", "False").lower() == 'true'
    MUSIC_TIDAL_MOBILE_TOKEN = getenv("MUSIC_TIDAL_MOBILE_TOKEN")
    MUSIC_TIDAL_ATMOS_MOBILE_TOKEN = getenv("MUSIC_TIDAL_ATMOS_MOBILE_TOKEN")
    MUSIC_TIDAL_TV_TOKEN    = getenv("MUSIC_TIDAL_TV_TOKEN")
    MUSIC_TIDAL_TV_SECRET   = getenv("MUSIC_TIDAL_TV_SECRET")
    MUSIC_TIDAL_CONVERT_M4A = getenv("MUSIC_TIDAL_CONVERT_M4A", "False").lower() == 'true'
    MUSIC_TIDAL_REFRESH_TOKEN = getenv("MUSIC_TIDAL_REFRESH_TOKEN")
    MUSIC_TIDAL_COUNTRY_CODE = getenv("MUSIC_TIDAL_COUNTRY_CODE", "US")
    MUSIC_TIDAL_QUALITY     = getenv("MUSIC_TIDAL_QUALITY")
    MUSIC_TIDAL_SPATIAL     = getenv("MUSIC_TIDAL_SPATIAL")
    MUSIC_TIDAL_NG_DOWNLOAD_PATH = getenv("MUSIC_TIDAL_NG_DOWNLOAD_PATH")
    MUSIC_TIDAL_NG_DOWNLOAD_BASE_PATH = getenv("MUSIC_TIDAL_NG_DOWNLOAD_BASE_PATH")
    MUSIC_DOWNLOADER_PATH   = getenv("MUSIC_DOWNLOADER_PATH", "/usr/src/app/downloader/am_downloader.sh")
    MUSIC_INSTALLER_PATH    = getenv("MUSIC_INSTALLER_PATH", "/usr/src/app/downloader/install_am_downloader.sh")
    MUSIC_APPLE_DEFAULT_FORMAT = getenv("MUSIC_APPLE_DEFAULT_FORMAT", "alac")
    MUSIC_APPLE_ALAC_QUALITY = int(getenv("MUSIC_APPLE_ALAC_QUALITY", 192000))
    MUSIC_APPLE_ATMOS_QUALITY = int(getenv("MUSIC_APPLE_ATMOS_QUALITY", 2768))
    MUSIC_APPLE_CONFIG_YAML_PATH = getenv("MUSIC_APPLE_CONFIG_YAML_PATH", "/root/amalac/config.yaml")
    MUSIC_APPLE_WRAPPER_SETUP_PATH = getenv("MUSIC_APPLE_WRAPPER_SETUP_PATH", "/usr/src/app/downloader/setup_wrapper.sh")
    MUSIC_APPLE_WRAPPER_STOP_PATH  = getenv("MUSIC_APPLE_WRAPPER_STOP_PATH", "/usr/src/app/downloader/stop_wrapper.sh")

    # =====================================================================================
    #                                 MIRROR BOT CONFIGURATION
    # =====================================================================================
    MIRROR_AS_DOCUMENT = getenv("MIRROR_AS_DOCUMENT", "False").lower() == 'true'
    MIRROR_AUTHORIZED_CHATS = getenv("MIRROR_AUTHORIZED_CHATS", "")
    MIRROR_CMD_SUFFIX = getenv("MIRROR_CMD_SUFFIX", "")
    MIRROR_DEFAULT_UPLOAD = getenv("MIRROR_DEFAULT_UPLOAD", "rc")
    MIRROR_EQUAL_SPLITS = getenv("MIRROR_EQUAL_SPLITS", "False").lower() == 'true'
    MIRROR_EXCLUDED_EXTENSIONS = getenv("MIRROR_EXCLUDED_EXTENSIONS", "")
    MIRROR_FFMPEG_CMDS = getenv("MIRROR_FFMPEG_CMDS", "{}")
    MIRROR_FILELION_API = getenv("MIRROR_FILELION_API", "")
    MIRROR_GDRIVE_ID = getenv("MIRROR_GDRIVE_ID", "")
    MIRROR_INCOMPLETE_TASK_NOTIFIER = getenv("MIRROR_INCOMPLETE_TASK_NOTIFIER", "False").lower() == 'true'
    MIRROR_INDEX_URL = getenv("MIRROR_INDEX_URL", "")
    MIRROR_IS_TEAM_DRIVE = getenv("MIRROR_IS_TEAM_DRIVE", "False").lower() == 'true'
    MIRROR_LEECH_DUMP_CHAT = getenv("MIRROR_LEECH_DUMP_CHAT", "")
    MIRROR_LEECH_FILENAME_PREFIX = getenv("MIRROR_LEECH_FILENAME_PREFIX", "")
    MIRROR_LEECH_SPLIT_SIZE = int(getenv("MIRROR_LEECH_SPLIT_SIZE", 2097152000))
    MIRROR_MEDIA_GROUP = getenv("MIRROR_MEDIA_GROUP", "False").lower() == 'true'
    MIRROR_HYBRID_LEECH = getenv("MIRROR_HYBRID_LEECH", "False").lower() == 'true'
    MIRROR_NAME_SUBSTITUTE = getenv("MIRROR_NAME_SUBSTITUTE", "")
    MIRROR_QUEUE_ALL = int(getenv("MIRROR_QUEUE_ALL", 0))
    MIRROR_QUEUE_DOWNLOAD = int(getenv("MIRROR_QUEUE_DOWNLOAD", 0))
    MIRROR_QUEUE_UPLOAD = int(getenv("MIRROR_QUEUE_UPLOAD", 0))
    MIRROR_RCLONE_FLAGS = getenv("MIRROR_RCLONE_FLAGS", "")
    MIRROR_RCLONE_PATH = getenv("MIRROR_RCLONE_PATH", "")
    MIRROR_RCLONE_SERVE_URL = getenv("MIRROR_RCLONE_SERVE_URL", "")
    MIRROR_RCLONE_SERVE_USER = getenv("MIRROR_RCLONE_SERVE_USER", "")
    MIRROR_RCLONE_SERVE_PASS = getenv("MIRROR_RCLONE_SERVE_PASS", "")
    MIRROR_RCLONE_SERVE_PORT = int(getenv("MIRROR_RCLONE_SERVE_PORT", 8080))
    MIRROR_RSS_CHAT = getenv("MIRROR_RSS_CHAT", "")
    MIRROR_RSS_DELAY = int(getenv("MIRROR_RSS_DELAY", 600))
    MIRROR_RSS_SIZE_LIMIT = int(getenv("MIRROR_RSS_SIZE_LIMIT", 0))
    MIRROR_SEARCH_API_LINK = getenv("MIRROR_SEARCH_API_LINK", "")
    MIRROR_SEARCH_LIMIT = int(getenv("MIRROR_SEARCH_LIMIT", 0))
    MIRROR_STATUS_LIMIT = int(getenv("MIRROR_STATUS_LIMIT", 4))
    MIRROR_STATUS_UPDATE_INTERVAL = int(getenv("MIRROR_STATUS_UPDATE_INTERVAL", 15))
    MIRROR_STOP_DUPLICATE = getenv("MIRROR_STOP_DUPLICATE", "False").lower() == 'true'
    MIRROR_STREAMWISH_API = getenv("MIRROR_STREAMWISH_API", "")
    MIRROR_TG_PROXY = getenv("MIRROR_TG_PROXY", "{}")
    MIRROR_THUMBNAIL_LAYOUT = getenv("MIRROR_THUMBNAIL_LAYOUT", "")
    MIRROR_UPLOAD_PATHS = getenv("MIRROR_UPLOAD_PATHS", "{}")
    MIRROR_UPSTREAM_REPO = getenv("MIRROR_UPSTREAM_REPO", "")
    MIRROR_UPSTREAM_BRANCH = getenv("MIRROR_UPSTREAM_BRANCH", "master")
    MIRROR_USER_SESSION_STRING = getenv("MIRROR_USER_SESSION_STRING", "")
    MIRROR_USER_TRANSMISSION = getenv("MIRROR_USER_TRANSMISSION", "False").lower() == 'true'
    MIRROR_USE_SERVICE_ACCOUNTS = getenv("MIRROR_USE_SERVICE_ACCOUNTS", "False").lower() == 'true'

    # --- qBittorrent Configuration ---
    MIRROR_QB_URL = getenv("MIRROR_QB_URL", None)
    MIRROR_QB_USERNAME = getenv("MIRROR_QB_USERNAME", None)
    MIRROR_QB_PASSWORD = getenv("MIRROR_QB_PASSWORD", None)

    # --- SABnzbd Configuration ---
    MIRROR_SAB_URL = getenv("MIRROR_SAB_URL", None)
    MIRROR_SAB_API_KEY = getenv("MIRROR_SAB_API_KEY", None)
