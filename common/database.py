import datetime
import sqlite3

from common.logger import logger


class Database:
    def __init__(self, __db_path="app.db"):
        self.__db_path = __db_path
        self.__conn = None
        try:
            self.__conn = sqlite3.connect(self.__db_path, check_same_thread=False)
            self.__conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to database")
            self._create_tables()
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")

    def _create_tables(self):
        if self.__conn:
            cursor = self.__conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS connection_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    event TEXT NOT NULL CHECK (event IN ('CONNECTED', 'DISCONNECTED')),
                    connected_at INTEGER NOT NULL,
                    disconnected_at INTEGER
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    controller_id TEXT NOT NULL,  -- client_id của máy điều khiển
                    host_id TEXT NOT NULL,  -- client_id của máy bị điều khiển
                    status TEXT NOT NULL CHECK (
                        status IN ('ACTIVE', 'ENDED', 'FAILED_AUTH')
                    ),
                    started_at INTEGER NOT NULL,
                    ended_at INTEGER
                );
                """
            )

    def add_connection_log(self, client_id: str, ip_address: str):
        """Thêm một bản ghi kết nối vào DB"""
        sql = """
            INSERT INTO connection_logs (client_id, ip_address, event, connected_at)
            VALUES (?, ?, 'CONNECTED', ?)
        """
        now = int(datetime.datetime.now().timestamp())
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (client_id, ip_address, now))
                self.__conn.commit()
                logger.info(f"Added connection log for client {client_id}")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def update_connection_disconnected(self, client_id: str):
        """Cập nhật thời gian ngắt kết nối"""
        sql = """
            UPDATE connection_logs
            SET event = 'DISCONNECTED', disconnected_at = ?
            WHERE log_id = (
                SELECT log_id
                FROM connection_logs
                WHERE client_id = ? AND event = 'CONNECTED'
                ORDER BY log_id DESC
                LIMIT 1
            )
        """
        now = int(datetime.datetime.now().timestamp())
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (now, client_id))
                self.__conn.commit()
                logger.info(f"Updated connection log for client {client_id}")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def add_session_log(self, session_id: str, controller_id: str, host_id: str):
        """Thêm một bản ghi phiên vào DB"""
        sql = """
            INSERT INTO session_logs (session_id, controller_id, host_id, status, started_at)
            VALUES (?, ?, ?, 'ACTIVE', ?)
        """
        now = int(datetime.datetime.now().timestamp())
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (session_id, controller_id, host_id, now))
                self.__conn.commit()
                logger.info(
                    f"Added session log for controller {controller_id} and host {host_id}"
                )
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def end_session_log(self, session_id: str, status: str):
        """Kết thúc một phiên làm việc"""
        sql = """
            UPDATE session_logs
            SET status = ?, ended_at = ?
            WHERE session_id = ?
        """
        now = int(datetime.datetime.now().timestamp())
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (status, now, session_id))
                self.__conn.commit()
                logger.info(f"Ended session {session_id} with status {status}")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def close(self):
        if self.__conn:
            self.__conn.close()


_db_instance = None


def get_db_instance():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
