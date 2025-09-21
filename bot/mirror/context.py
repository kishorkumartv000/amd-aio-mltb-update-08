from pyrogram import Client
from typing import Optional

class _MirrorBotContext:
    """
    A class to hold the context for the mirror bot, including the bot and user clients.
    This acts as a replacement for the old TgClient singleton. The main bot will
    inject the clients into this context upon startup.
    """
    bot: Optional[Client] = None
    user: Optional[Client] = None
    IS_PREMIUM_USER: bool = False
    MAX_SPLIT_SIZE: int = 2097152000

# Global instance of the context
g_context = _MirrorBotContext()

def set_mirror_context(bot_client: Client, user_client: Optional[Client]):
    """
    Sets the global context for the mirror bot.
    This should be called once from the main application's entry point.
    """
    g_context.bot = bot_client
    g_context.user = user_client
    if user_client and user_client.is_initialized:
        try:
            g_context.IS_PREMIUM_USER = user_client.me.is_premium
            if g_context.IS_PREMIUM_USER:
                g_context.MAX_SPLIT_SIZE = 4194304000
        except Exception:
            # In case the user session is invalid
            g_context.IS_PREMIUM_USER = False
    else:
        g_context.IS_PREMIUM_USER = False
