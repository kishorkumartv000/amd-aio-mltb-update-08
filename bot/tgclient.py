from config import Config
from pyrogram import Client
from .logger import LOGGER
from .settings import bot_set
import subprocess
import os

# Explicitly import all modules to ensure handlers are registered
from .modules import (
    cancel,
    config_yaml,
    download,
    file_manager_callbacks,
    help,
    history,
    provider_settings,
    settings,
    start,
    telegram_setting,
    tidal_ng_settings,
)

# The plugins dict is kept for Pyrogram's internal use, but we rely on explicit imports.
plugins = dict(
    root="bot/modules"
)

# Import the mirror bot starter
from bot.mirror.starter import init_mirror_bot

class Bot(Client):
    def __init__(self):
        super().__init__(
            "Apple-Music-Bot",
            api_id=Config.APP_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.TG_BOT_TOKEN,
            plugins=plugins,
            workdir=Config.MUSIC_WORK_DIR, # Use MUSIC_ prefix
            workers=Config.MUSIC_MAX_WORKERS # Use MUSIC_ prefix
        )
        self.user_bot: Client | None = None

    async def start(self):
        await super().start()
        await bot_set.login_qobuz()
        await bot_set.login_deezer()
        await bot_set.login_tidal()
        
        # Initialize Apple Music downloader
        if not os.path.exists(Config.MUSIC_DOWNLOADER_PATH):
            LOGGER.error("Apple Music downloader not found! Running installer...")
            subprocess.run([Config.MUSIC_INSTALLER_PATH], check=True)
        
        # Initialize user bot for mirror if configured
        if Config.MIRROR_USER_SESSION_STRING:
            LOGGER.info("Starting user bot for mirror features...")
            self.user_bot = Client(
                name="mirror_user_bot",
                api_id=Config.APP_ID,
                api_hash=Config.API_HASH,
                session_string=Config.MIRROR_USER_SESSION_STRING,
                no_updates=True # Don't process incoming messages with the user bot
            )
            await self.user_bot.start()
            LOGGER.info("User bot started successfully.")

        # Initialize the mirror bot components
        try:
            await init_mirror_bot(self, self.user_bot)
        except Exception as e:
            LOGGER.error(f"Failed to initialize mirror bot: {e}")

        # Queue worker: start only if Queue Mode is enabled
        try:
            from .helpers.tasks import task_manager
            if getattr(bot_set, 'queue_mode', False):
                await task_manager.start_worker()
        except Exception:
            pass

        LOGGER.info("BOT : Started Successfully with Apple Music and Mirror support")

    async def stop(self, *args):
        await super().stop()
        if self.user_bot:
            await self.user_bot.stop()
        for client in bot_set.clients:
            await client.session.close()
        LOGGER.info('BOT : Exited Successfully!')

aio = Bot()
