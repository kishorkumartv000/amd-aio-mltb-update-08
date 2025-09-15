import psycopg2
import datetime
import psycopg2.extras
from .pg_db import DataBaseHandle
from config import Config

class BotSettings(DataBaseHandle):
    def __init__(self, dburl=None):
        if dburl is None:
            dburl = Config.DATABASE_URL
        super().__init__(dburl)

        settings_schema = """CREATE TABLE IF NOT EXISTS bot_settings (
            id SERIAL PRIMARY KEY NOT NULL,
            var_name VARCHAR(50) NOT NULL UNIQUE,
            var_value VARCHAR(2000) DEFAULT NULL,
            vtype VARCHAR(20) DEFAULT NULL,
            blob_val BYTEA DEFAULT NULL,
            date_changed TIMESTAMP NOT NULL
        )"""

        cur = self.scur()
        try:
            cur.execute(settings_schema)
        except psycopg2.errors.UniqueViolation:
            pass

        self._conn.commit()
        self.ccur(cur)

    def set_variable(self, var_name, var_value, update_blob=False, blob_val=None):
        vtype = "str"
        if isinstance(var_value, bool):
            vtype = "bool"
        elif isinstance(var_value, int):
            vtype = "int"

        if update_blob:
            vtype = "blob"

        sql = "SELECT * FROM bot_settings WHERE var_name=%s"
        cur = self.scur()

        cur.execute(sql, (var_name,))
        if cur.rowcount > 0:
            if not update_blob:
                sql = "UPDATE bot_settings SET var_value=%s , vtype=%s WHERE var_name=%s"
            else:
                sql = "UPDATE bot_settings SET blob_val=%s , vtype=%s WHERE var_name=%s"
                var_value = blob_val

            cur.execute(sql, (var_value, vtype, var_name))
        else:
            if not update_blob:
                sql = "INSERT INTO bot_settings(var_name,var_value,date_changed,vtype) VALUES(%s,%s,%s,%s)"
            else:
                sql = "INSERT INTO bot_settings(var_name,blob_val,date_changed,vtype) VALUES(%s,%s,%s,%s)"
                var_value = blob_val

            cur.execute(sql, (var_name, var_value, datetime.datetime.now(), vtype))

        self.ccur(cur)

    def get_variable(self, var_name):
        sql = "SELECT * FROM bot_settings WHERE var_name=%s"
        cur = self.scur()

        cur.execute(sql, (var_name,))
        if cur.rowcount > 0:
            row = cur.fetchone()
            vtype = row[3]
            val = row[2]
            if vtype == "int":
                val = int(row[2])
            elif vtype == "str":
                val = str(row[2])
            elif vtype == "bool":
                # Accept different representations (True/true/1/yes/on)
                sval = str(row[2]).strip().lower()
                val = sval in ("true", "1", "yes", "on")

            return val, row[4]
        else:
            return None, None

        self.ccur(cur)

    def __del__(self):
        super().__del__()

class DownloadHistory(DataBaseHandle):
    def __init__(self, dburl=None):
        if dburl is None:
            dburl = Config.DATABASE_URL
        super().__init__(dburl)
        
        # Create download history table
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
        cur = self.scur()
        cur.execute(schema)
        self._conn.commit()
        self.ccur(cur)
    
    def record_download(self, user_id, provider, content_type, content_id, title, artist, quality):
        sql = """
        INSERT INTO download_history 
        (user_id, provider, content_type, content_id, title, artist, quality) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        attempts = 0
        while attempts < 2:
            cur = self.scur()
            try:
                cur.execute(sql, (user_id, provider, content_type, content_id, title, artist, quality))
                self._conn.commit()
                self.ccur(cur)
                return
            except psycopg2.Error as e:
                try:
                    cur.close()
                except Exception:
                    pass
                self.re_establish()
                attempts += 1
                if attempts >= 2:
                    raise e
    
    def get_user_history(self, user_id, limit=10):
        sql = "SELECT * FROM download_history WHERE user_id = %s ORDER BY download_time DESC LIMIT %s"
        attempts = 0
        while attempts < 2:
            cur = self.scur(dictcur=True)
            try:
                cur.execute(sql, (user_id, limit))
                results = cur.fetchall()
                self.ccur(cur)
                return results
            except psycopg2.Error as e:
                try:
                    cur.close()
                except Exception:
                    pass
                self.re_establish()
                attempts += 1
                if attempts >= 2:
                    raise e

# Initialize database handlers
set_db = BotSettings()
download_history = DownloadHistory()

class UserSettings(DataBaseHandle):
    def __init__(self, dburl=None):
        if dburl is None:
            dburl = Config.DATABASE_URL
        super().__init__(dburl)

        schema = """CREATE TABLE IF NOT EXISTS user_settings (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            setting_name VARCHAR(50) NOT NULL,
            setting_value VARCHAR(2000),
            UNIQUE(user_id, setting_name)
        )"""
        cur = self.scur()
        cur.execute(schema)
        self._conn.commit()
        self.ccur(cur)

    def set_user_setting(self, user_id, setting_name, setting_value):
        sql = """
        INSERT INTO user_settings (user_id, setting_name, setting_value)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, setting_name)
        DO UPDATE SET setting_value = EXCLUDED.setting_value;
        """
        cur = self.scur()
        cur.execute(sql, (user_id, setting_name, str(setting_value)))
        self._conn.commit()
        self.ccur(cur)

    def get_user_setting(self, user_id, setting_name):
        sql = "SELECT setting_value FROM user_settings WHERE user_id = %s AND setting_name = %s"
        cur = self.scur()
        cur.execute(sql, (user_id, setting_name))
        if cur.rowcount > 0:
            val = cur.fetchone()[0]
            self.ccur(cur)
            return val
        self.ccur(cur)
        return None

user_set_db = UserSettings()


class RcloneSessionsDB(DataBaseHandle):
    def __init__(self, dburl=None):
        if dburl is None:
            dburl = Config.DATABASE_URL
        super().__init__(dburl)

        schema = """
        CREATE TABLE IF NOT EXISTS rclone_sessions (
            token VARCHAR(20) PRIMARY KEY,
            user_id BIGINT NOT NULL,
            context JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_rclone_sessions_created_at ON rclone_sessions(created_at);
        """
        cur = self.scur()
        cur.execute(schema)
        self._conn.commit()
        self.ccur(cur)

    def add_session(self, token: str, user_id: int, context: dict):
        sql = "INSERT INTO rclone_sessions (token, user_id, context) VALUES (%s, %s, %s)"
        cur = self.scur()
        cur.execute(sql, (token, user_id, psycopg2.extras.Json(context)))
        self._conn.commit()
        self.ccur(cur)

    def get_session(self, token: str):
        sql = "SELECT context FROM rclone_sessions WHERE token = %s"
        cur = self.scur(dictcur=True)
        cur.execute(sql, (token,))
        if cur.rowcount > 0:
            val = cur.fetchone()
            self.ccur(cur)
            return val['context']
        self.ccur(cur)
        return None

    def delete_session(self, token: str):
        sql = "DELETE FROM rclone_sessions WHERE token = %s"
        cur = self.scur()
        cur.execute(sql, (token,))
        self._conn.commit()
        self.ccur(cur)

rclone_sessions_db = RcloneSessionsDB()
