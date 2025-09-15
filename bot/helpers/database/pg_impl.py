# bot/helpers/database/db_init.py (formerly pg_impl.py)
# This file is responsible for initializing the correct database backend
# based on the bot's configuration.

from config import Config
from .interface import DatabaseInterface

def get_db() -> DatabaseInterface:
    """Factory function to get the configured database backend."""
    db_type = Config.DATABASE_TYPE
    
    if db_type == 'mongodb':
        from .mongodb_backend import MongoDatabase
        db_instance = MongoDatabase()
    elif db_type == 'postgres':
        from .postgres_backend import PostgresDatabase
        db_instance = PostgresDatabase()
    else:
        # We'll log an error and exit if the DB type is unsupported.
        from bot.logger import LOGGER
        LOGGER.critical(f"Unsupported DATABASE_TYPE: '{db_type}'. Please use 'postgres' or 'mongodb'.")
        exit(1)
    
    # Establish the connection
    db_instance.connect(Config.DATABASE_URL)
    return db_instance

# Initialize the database. This will be imported by other parts of the app.
db = get_db()

# For backward compatibility, we expose the repository instances under the old
# variable names that are used throughout the application.
# This avoids having to refactor every single file that uses the database.
set_db = db.settings
download_history = db.history
user_set_db = db.user_settings
rclone_sessions_db = db.rclone_sessions
