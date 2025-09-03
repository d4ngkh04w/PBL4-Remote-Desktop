import datetime
import sqlite3

from common.logger import logger


class Database:
    def __init__(self, __db_path="app.db"):
        self.__db_path = __db_path
        self.__conn = None
        try:
            self.__conn = sqlite3.connect(
                self.__db_path, check_same_thread=False)
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
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK(status IN ('ONLINE', 'IN_SESSION_HOST', 'IN_SESSION_CONTROLLER')),
                    ip_address TEXT,
                    connected_at TEXT NOT NULL
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    controller_client_id TEXT NOT NULL,
                    host_client_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'ENDED', 'FAILED_AUTH')),
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    FOREIGN KEY (controller_client_id) REFERENCES clients (client_id),
                    FOREIGN KEY (host_client_id) REFERENCES clients (client_id)
                );
                """
            )

    def add_client(self, client_id: str, ip_address: str):
        """Thêm một client mới vào DB khi họ kết nối"""
        sql = """
            INSERT INTO clients (client_id, status, ip_address, connected_at)
            VALUES (?, 'ONLINE', ?, ?)
        """
        now = datetime.datetime.now().isoformat()
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (client_id, ip_address, now))
                self.__conn.commit()
                logger.info(f"Added new client {client_id} to database")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def remove_client(self, client_id: str):
        """Xóa một client khỏi DB khi họ ngắt kết nối"""
        sql = "DELETE FROM clients WHERE client_id = ?"
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (client_id,))
                self.__conn.commit()
                logger.info(f"Removed client {client_id} from database")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def update_client_status(self, client_id: str, new_status: str):
        """Cập nhật trạng thái của một client trong DB"""
        valid_statuses = ['ONLINE', 'IN_SESSION_HOST', 'IN_SESSION_CONTROLLER']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Valid statuses are: {valid_statuses}")

        sql = "UPDATE clients SET status = ? WHERE client_id = ?"
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (new_status, client_id))
                self.__conn.commit()
                logger.info(f"Updated client {client_id} status to {new_status}")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e

    def is_client_online(self, client_id: str) -> bool:
        """Kiểm tra xem một client có đang trực tuyến hay không"""
        sql = "SELECT status FROM clients WHERE client_id = ?"
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (client_id,))
                result = cursor.fetchone()
                if result:
                    return result[0] == 'ONLINE'
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e
        return False
    
    def create_session(self, controller_id: str, host_id: str):
        """Tạo session mới"""
        sql = """
            INSERT INTO sessions (controller_client_id, host_client_id, status, started_at)
            VALUES (?, ?, 'ACTIVE', ?)
        """
        now = datetime.datetime.now().isoformat()
        try:
            if self.__conn:
                cursor = self.__conn.cursor()
                cursor.execute(sql, (controller_id, host_id, now))
                self.__conn.commit()
                logger.info(f"Created new session between controller {controller_id} and host {host_id}")
                return cursor.lastrowid
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
