# bot/mirror/helper/ext_utils/db_handler.py
# This file is an adapter to map the mirror bot's data access needs
# to the main bot's unified database interface.

from bot.database import db  # Import the global DB instance
from typing import Dict, Any, List

# Note: The original DbManager class and its direct pymongo logic have been removed.
# All database operations are now delegated to the unified database interface.

async def get_all_rss_feeds() -> List[Dict[str, Any]]:
    """Gets all RSS feeds from the database."""
    return db.rss.get_all_feeds()

async def update_rss_feed(user_id: int, feed_name: str, feed_data: Dict[str, Any]) -> None:
    """Updates or creates an RSS feed."""
    db.rss.update_feed(user_id, feed_name, feed_data)

async def delete_rss_feed(user_id: int, feed_name: str) -> None:
    """Deletes an RSS feed."""
    db.rss.delete_feed(user_id, feed_name)

async def get_all_incomplete_tasks() -> List[Dict[str, Any]]:
    """Gets all incomplete tasks."""
    return db.tasks.get_all_tasks()

async def add_incomplete_task(task_id: str, chat_id: int, message_id: int, tag: str) -> None:
    """Adds an incomplete task."""
    db.tasks.add_task(task_id, chat_id, message_id, tag)

async def remove_incomplete_task(task_id: str) -> None:
    """Removes an incomplete task."""
    db.tasks.remove_task(task_id)

async def clear_all_incomplete_tasks() -> None:
    """Clears all incomplete tasks from the database."""
    db.tasks.clear_all_tasks()

# User settings are now handled by the main UserSettings repository.
# The mirror bot's user settings can be get/set using db.user_settings.
# Example: db.user_settings.set_user_setting(user_id, 'mirror_leech_type', 'media')

# Bot-wide settings are handled by the main Settings repository.
# Example: db.settings.set_variable('mirror_status_update_interval', 10)

# The concept of storing private files (rclone.conf, tokens.pickle) in the database
# will be mapped to the user_settings repository, likely storing them as base64
# encoded strings or using the blob storage mechanism if available. This will be
# handled during the core logic migration phase.
