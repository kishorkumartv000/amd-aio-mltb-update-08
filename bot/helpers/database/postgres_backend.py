# bot/helpers/database/postgres_backend.py

from .interface import (
    AbstractSettingsRepo,
    AbstractHistoryRepo,
    AbstractUserSettingsRepo,
    AbstractRcloneSessionsRepo,
    DatabaseInterface
)
from .pg_db import DataBaseHandle
import psycopg2
import datetime
import psycopg2.extras
from typing import Any, Dict, List, Optional, Tuple

# --- Repository Implementations ---

class PostgresSettingsRepo(AbstractSettingsRepo):
    def __init__(self, db_handle: DataBaseHandle):
        self._db = db_handle
        settings_schema = """CREATE TABLE IF NOT EXISTS bot_settings (
            id SERIAL PRIMARY KEY NOT NULL,
            var_name VARCHAR(50) NOT NULL UNIQUE,
            var_value VARCHAR(2000) DEFAULT NULL,
            vtype VARCHAR(20) DEFAULT NULL,
            blob_val BYTEA DEFAULT NULL,
            date_changed TIMESTAMP NOT NULL
        )"""
        cur = self._db.scur()
        try:
            cur.execute(settings_schema)
        except psycopg2.errors.UniqueViolation:
            pass # Table already exists
        finally:
            self._db.ccur(cur)

    def set_variable(self, var_name: str, var_value: Any, update_blob: bool = False, blob_val: Optional[bytes] = None) -> None:
        vtype = "str"
        if isinstance(var_value, bool):
            vtype = "bool"
        elif isinstance(var_value, int):
            vtype = "int"
        if update_blob:
            vtype = "blob"

        cur = self._db.scur()
        try:
            cur.execute("SELECT * FROM bot_settings WHERE var_name=%s", (var_name,))
            if cur.rowcount > 0:
                if not update_blob:
                    sql = "UPDATE bot_settings SET var_value=%s, vtype=%s, date_changed=%s WHERE var_name=%s"
                    cur.execute(sql, (str(var_value), vtype, datetime.datetime.now(), var_name))
                else:
                    sql = "UPDATE bot_settings SET blob_val=%s, vtype=%s, date_changed=%s WHERE var_name=%s"
                    cur.execute(sql, (blob_val, vtype, datetime.datetime.now(), var_name))
            else:
                if not update_blob:
                    sql = "INSERT INTO bot_settings(var_name, var_value, date_changed, vtype) VALUES(%s, %s, %s, %s)"
                    cur.execute(sql, (var_name, str(var_value), datetime.datetime.now(), vtype))
                else:
                    sql = "INSERT INTO bot_settings(var_name, blob_val, date_changed, vtype) VALUES(%s, %s, %s, %s)"
                    cur.execute(sql, (var_name, blob_val, datetime.datetime.now(), vtype))
        finally:
            self._db.ccur(cur)

    def get_variable(self, var_name: str) -> Tuple[Optional[Any], Optional[bytes]]:
        cur = self._db.scur(dictcur=True)
        val = None
        blob_val = None
        try:
            cur.execute("SELECT * FROM bot_settings WHERE var_name = %s", (var_name,))
            if cur.rowcount > 0:
                row = cur.fetchone()
                vtype = row['vtype']
                val = row['var_value']
                if vtype == "int":
                    val = int(val) if val is not None else None
                elif vtype == "bool":
                    val = str(val).strip().lower() in ("true", "1", "yes", "on")
                blob_val = row['blob_val']
        finally:
            self._db.ccur(cur)
        return val, blob_val

class PostgresHistoryRepo(AbstractHistoryRepo):
    def __init__(self, db_handle: DataBaseHandle):
        self._db = db_handle
        schema = """
        CREATE TABLE IF NOT EXISTS download_history (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            provider VARCHAR(20) NOT NULL,
            content_type VARCHAR(10) NOT NULL,
            content_id VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            artist VARCHAR(255) NOT NULL,
            quality VARCHAR(20),
            download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_user_downloads ON download_history(user_id);
        """
        cur = self._db.scur()
        try:
            cur.execute(schema)
        finally:
            self._db.ccur(cur)

    def record_download(self, user_id: int, provider: str, content_type: str, content_id: str, title: str, artist: str, quality: str) -> None:
        sql = """
        INSERT INTO download_history (user_id, provider, content_type, content_id, title, artist, quality)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur = self._db.scur()
        try:
            cur.execute(sql, (user_id, provider, content_type, content_id, title, artist, quality))
        finally:
            self._db.ccur(cur)

    def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM download_history WHERE user_id = %s ORDER BY download_time DESC LIMIT %s"
        cur = self._db.scur(dictcur=True)
        results = []
        try:
            cur.execute(sql, (user_id, limit))
            results = cur.fetchall()
        finally:
            self._db.ccur(cur)
        return [dict(row) for row in results]

class PostgresUserSettingsRepo(AbstractUserSettingsRepo):
    def __init__(self, db_handle: DataBaseHandle):
        self._db = db_handle
        schema = """CREATE TABLE IF NOT EXISTS user_settings (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            setting_name VARCHAR(50) NOT NULL,
            setting_value VARCHAR(2000),
            UNIQUE(user_id, setting_name)
        )"""
        cur = self._db.scur()
        try:
            cur.execute(schema)
        finally:
            self._db.ccur(cur)

    def set_user_setting(self, user_id: int, setting_name: str, setting_value: Any) -> None:
        sql = """
        INSERT INTO user_settings (user_id, setting_name, setting_value)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, setting_name)
        DO UPDATE SET setting_value = EXCLUDED.setting_value;
        """
        cur = self._db.scur()
        try:
            cur.execute(sql, (user_id, setting_name, str(setting_value)))
        finally:
            self._db.ccur(cur)

    def get_user_setting(self, user_id: int, setting_name: str) -> Optional[Any]:
        sql = "SELECT setting_value FROM user_settings WHERE user_id = %s AND setting_name = %s"
        cur = self._db.scur()
        val = None
        try:
            cur.execute(sql, (user_id, setting_name))
            if cur.rowcount > 0:
                val = cur.fetchone()[0]
        finally:
            self._db.ccur(cur)
        return val

class PostgresRcloneSessionsRepo(AbstractRcloneSessionsRepo):
    def __init__(self, db_handle: DataBaseHandle):
        self._db = db_handle
        schema = """
        CREATE TABLE IF NOT EXISTS rclone_sessions (
            token VARCHAR(20) PRIMARY KEY,
            user_id BIGINT NOT NULL,
            context JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_rclone_sessions_created_at ON rclone_sessions(created_at);
        """
        cur = self._db.scur()
        try:
            cur.execute(schema)
        finally:
            self._db.ccur(cur)

    def add_session(self, token: str, user_id: int, context: Dict[str, Any]) -> None:
        sql = "INSERT INTO rclone_sessions (token, user_id, context) VALUES (%s, %s, %s)"
        cur = self._db.scur()
        try:
            cur.execute(sql, (token, user_id, psycopg2.extras.Json(context)))
        finally:
            self._db.ccur(cur)

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT context FROM rclone_sessions WHERE token = %s"
        cur = self._db.scur(dictcur=True)
        val = None
        try:
            cur.execute(sql, (token,))
            if cur.rowcount > 0:
                val = cur.fetchone()['context']
        finally:
            self._db.ccur(cur)
        return val

    def delete_session(self, token: str) -> None:
        sql = "DELETE FROM rclone_sessions WHERE token = %s"
        cur = self._db.scur()
        try:
            cur.execute(sql, (token,))
        finally:
            self._db.ccur(cur)

# --- Main Backend Class ---

class PostgresRssRepo(AbstractRssRepo):
    def __init__(self, db_handle: DataBaseHandle):
        self._db = db_handle
        schema = """
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            feed_name VARCHAR(255) NOT NULL,
            feed_data JSONB NOT NULL,
            UNIQUE(user_id, feed_name)
        );
        """
        cur = self._db.scur()
        try:
            cur.execute(schema)
        finally:
            self._db.ccur(cur)

    def update_feed(self, user_id: int, feed_name: str, feed_data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO rss_feeds (user_id, feed_name, feed_data)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, feed_name)
        DO UPDATE SET feed_data = EXCLUDED.feed_data;
        """
        cur = self._db.scur()
        try:
            cur.execute(sql, (user_id, feed_name, psycopg2.extras.Json(feed_data)))
        finally:
            self._db.ccur(cur)

    def get_feed(self, user_id: int, feed_name: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT feed_data FROM rss_feeds WHERE user_id = %s AND feed_name = %s"
        cur = self._db.scur(dictcur=True)
        val = None
        try:
            cur.execute(sql, (user_id, feed_name))
            if cur.rowcount > 0:
                val = cur.fetchone()['feed_data']
        finally:
            self._db.ccur(cur)
        return val

    def get_all_feeds(self) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM rss_feeds"
        cur = self._db.scur(dictcur=True)
        results = []
        try:
            cur.execute(sql)
            results = cur.fetchall()
        finally:
            self._db.ccur(cur)
        return [dict(row) for row in results]

    def delete_feed(self, user_id: int, feed_name: str) -> None:
        sql = "DELETE FROM rss_feeds WHERE user_id = %s AND feed_name = %s"
        cur = self._db.scur()
        try:
            cur.execute(sql, (user_id, feed_name))
        finally:
            self._db.ccur(cur)

class PostgresTasksRepo(AbstractTasksRepo):
    def __init__(self, db_handle: DataBaseHandle):
        self._db = db_handle
        schema = """
        CREATE TABLE IF NOT EXISTS incomplete_tasks (
            task_id VARCHAR(255) PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            message_id BIGINT NOT NULL,
            tag VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur = self._db.scur()
        try:
            cur.execute(schema)
        finally:
            self._db.ccur(cur)

    def add_task(self, task_id: str, chat_id: int, message_id: int, tag: str) -> None:
        sql = "INSERT INTO incomplete_tasks (task_id, chat_id, message_id, tag) VALUES (%s, %s, %s, %s)"
        cur = self._db.scur()
        try:
            cur.execute(sql, (task_id, chat_id, message_id, tag))
        finally:
            self._db.ccur(cur)

    def remove_task(self, task_id: str) -> None:
        sql = "DELETE FROM incomplete_tasks WHERE task_id = %s"
        cur = self._db.scur()
        try:
            cur.execute(sql, (task_id,))
        finally:
            self._db.ccur(cur)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM incomplete_tasks"
        cur = self._db.scur(dictcur=True)
        results = []
        try:
            cur.execute(sql)
            results = cur.fetchall()
        finally:
            self._db.ccur(cur)
        return [dict(row) for row in results]

    def clear_all_tasks(self) -> None:
        sql = "TRUNCATE TABLE incomplete_tasks"
        cur = self._db.scur()
        try:
            cur.execute(sql)
        finally:
            self._db.ccur(cur)

# --- Main Backend Class ---

class PostgresDatabase(DatabaseInterface):
    """PostgreSQL implementation of the database interface."""

    def __init__(self):
        super().__init__()
        self._db_handle: Optional[DataBaseHandle] = None

    def connect(self, db_url: str, **kwargs) -> None:
        """Connect to the database and initialize repositories."""
        if self._db_handle:
            return

        self._db_handle = DataBaseHandle(db_url)
        self.settings = PostgresSettingsRepo(self._db_handle)
        self.history = PostgresHistoryRepo(self._db_handle)
        self.user_settings = PostgresUserSettingsRepo(self._db_handle)
        self.rclone_sessions = PostgresRcloneSessionsRepo(self._db_handle)
        self.rss = PostgresRssRepo(self._db_handle)
        self.tasks = PostgresTasksRepo(self._db_handle)

    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self._db_handle:
            # The __del__ method of DataBaseHandle handles closing
            self._db_handle = None
