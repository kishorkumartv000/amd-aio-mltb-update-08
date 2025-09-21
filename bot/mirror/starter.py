from asyncio import gather
from pyrogram import Client
from typing import Optional

from . import LOGGER
from .context import set_mirror_context
from .core.handlers import add_handlers
from .core.startup import (
    load_settings,
    load_configurations,
    save_settings,
    update_variables,
)
from .helper.ext_utils.files_utils import clean_all
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from .modules import (
    initiate_search_tools,
    get_packages_version,
    restart_notification,
    create_help_buttons,
)

async def init_mirror_bot(bot_client: Client, user_client: Optional[Client]):
    """
    Initializes all the components of the mirror bot.
    This function is designed to be called from the main bot's entry point.
    """
    LOGGER.info("Initializing Mirror Bot...")

    # Set the global context for the mirror bot to use
    set_mirror_context(bot_client, user_client)

    # Load database settings and other configurations
    await load_settings()
    await gather(load_configurations(), update_variables())

    # Initialize torrent manager and other helpers
    from .core.torrent_manager import TorrentManager
    await TorrentManager.initiate()

    await gather(
        save_settings(),
        clean_all(),
        initiate_search_tools(),
        get_packages_version(),
        restart_notification(),
        telegraph.create_account(),
        rclone_serve_booter(),
    )

    # Create help buttons and add all command handlers
    create_help_buttons()
    add_handlers(bot_client)

    LOGGER.info("Mirror Bot Initialized Successfully!")
