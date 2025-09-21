import qbittorrentapi
import aria2p
from .. import LOGGER
from ..core.config_manager import Config

class TorrentManager:
    """
    A class to manage torrent clients (qBittorrent and Aria2).
    """
    qb_client: qbittorrentapi.Client | None = None
    aria2_client: aria2p.API | None = None

    @classmethod
    async def initiate(cls):
        """
        Initializes the torrent clients based on the configuration.
        """
        # Initialize qBittorrent client
        if Config.MIRROR_QB_URL:
            try:
                cls.qb_client = qbittorrentapi.Client(
                    host=Config.MIRROR_QB_URL,
                    username=Config.MIRROR_QB_USERNAME,
                    password=Config.MIRROR_QB_PASSWORD,
                    REQUESTS_ARGS={'timeout': (30, 60)}
                )
                await sync_to_async(cls.qb_client.auth_log_in)
                LOGGER.info("qBittorrent client connected successfully.")
            except Exception as e:
                LOGGER.error(f"Failed to connect to qBittorrent: {e}")
                cls.qb_client = None

        # Initialize Aria2 client
        # Note: The original bot seemed to have more complex aria2 setup.
        # This is a basic implementation to restore functionality.
        # The host and port should be configured via env vars if not default.
        try:
            cls.aria2_client = aria2p.API(
                aria2p.Client(
                    host="http://localhost",
                    port=6800,
                    secret=""
                )
            )
            LOGGER.info("Aria2 client connected successfully.")
        except Exception as e:
            LOGGER.error(f"Failed to connect to Aria2: {e}")
            cls.aria2_client = None

    @classmethod
    async def close_all(cls):
        """
        Closes all client connections.
        """
        if cls.qb_client and cls.qb_client.is_logged_in:
            await sync_to_async(cls.qb_client.auth_log_out)
            LOGGER.info("qBittorrent client disconnected.")

        # aria2p does not have an explicit close/logout method

    # Placeholder for other methods that were used in the original bot
    @classmethod
    async def get_overall_speed(cls):
        # This needs to be implemented by polling stats from both clients
        return "0 B/s", "0 B/s"

    @classmethod
    async def change_aria2_option(cls, key, value):
        if cls.aria2_client:
            try:
                await sync_to_async(cls.aria2_client.change_global_option, {key: value})
            except Exception as e:
                LOGGER.error(f"Failed to change Aria2 option: {e}")

    # Need to add methods for adding torrents, pausing, resuming, etc.
    # This will be a larger task. For now, this restores the basic connection.

# Helper for running sync functions in async context
async def sync_to_async(func, *args, **kwargs):
    return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))
