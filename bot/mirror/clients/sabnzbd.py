from pysabnzbd import SabnzbdClient
from ...core.config_manager import Config
from ... import LOGGER

sabnzbd_client = None

if Config.MIRROR_SAB_URL:
    try:
        sabnzbd_client = SabnzbdClient(
            base_url=Config.MIRROR_SAB_URL,
            api_key=Config.MIRROR_SAB_API_KEY
        )
        LOGGER.info("SABnzbd client initialized.")
    except Exception as e:
        LOGGER.error(f"Failed to initialize SABnzbd client: {e}")
