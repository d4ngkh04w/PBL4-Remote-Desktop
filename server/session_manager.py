import logging
import threading
import time
import uuid
from typing import Union, Optional

from server.client_manager import ClientManager
from common.packets import SessionPacket
from common.enums import Status

logger = logging.getLogger(__name__)


class SessionManager:
    __active_session: dict[str, dict[str, str | float]] = {}
    __lock = threading.Lock()
    __cleanup_thread = None
    __stop_cleanup = threading.Event()

    @classmethod
    def start_cleanup(cls, interval: int = 30):
        if cls.__cleanup_thread and cls.__cleanup_thread.is_alive():
            return

        def __cleanup_loop():
            while not cls.__stop_cleanup.is_set():
                cls.__stop_cleanup.wait(timeout=interval)
                if cls.__stop_cleanup.is_set():
                    break
                cls.__cleanup_expired_sessions()

        cls.__cleanup_thread = threading.Thread(target=__cleanup_loop, daemon=True)
        cls.__cleanup_thread.start()
        logger.info("Session cleanup started")

    @classmethod
    def __cleanup_expired_sessions(cls):
        with cls.__lock:
            now = time.time()
            expired_sessions = [
                sid
                for sid, info in cls.__active_session.items()
                if float(info["expires_at"]) < now
            ]
            for sid in expired_sessions:
                logger.info(f"Session {sid} expired")
                controller_id = str(cls.__active_session[sid]["controller_id"])
                host_id = str(cls.__active_session[sid]["host_id"])

                response = SessionPacket(
                    status=Status.SESSION_TIMEOUT,
                    session_id=sid,
                )
                controller_queue = ClientManager.get_client_queue(controller_id)
                host_queue = ClientManager.get_client_queue(host_id)
                if controller_queue:
                    controller_queue.put(response)
                if host_queue:
                    host_queue.put(response)
                cls.end_session(sid)

    @classmethod
    def shutdown(cls):
        if cls.__stop_cleanup.is_set():
            return
        cls.__stop_cleanup.set()
        if cls.__cleanup_thread is not None:
            cls.__cleanup_thread.join(timeout=5)
        with cls.__lock:
            session_ids = list(cls.__active_session.keys())
            for sid in session_ids:
                cls.end_session(sid)

            cls.__active_session.clear()
            logger.info("All active sessions cleared")

    @classmethod
    def create_session(
        cls, controller_id: str, host_id: str, timeout: float = 3600
    ) -> str:
        """Tạo session mới"""
        with cls.__lock:
            try:
                session_id = str(uuid.uuid4())

                cls.__active_session[session_id] = {
                    "controller_id": controller_id,
                    "host_id": host_id,
                    "status": "ACTIVE",
                    "expires_at": time.time() + timeout,
                }

                logger.debug(
                    f"Session {session_id} created between controller {controller_id} and host {host_id}"
                )

                return session_id

            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                raise e

    @classmethod
    def end_session(cls, session_id: str):
        """Kết thúc session"""
        with cls.__lock:
            try:
                if session_id in cls.__active_session:
                    del cls.__active_session[session_id]

                    logger.info(f"Session {session_id} ended")
                    return True
            except Exception as e:
                logger.error(f"Failed to end session {session_id}: {e}")
                return False

    @classmethod
    def get_session(cls, session_id: str) -> Optional[dict[str, Union[str, float]]]:
        """Lấy thông tin session"""
        with cls.__lock:
            return cls.__active_session.get(session_id)

    # @classmethod
    # def get_client_session(
    #     cls,
    #     client_id: str,
    # ) -> tuple[Optional[str], Optional[dict[str, Union[str, float]]]]:
    #     """Lấy session của một client"""
    #     with cls.__lock:
    #         return next(
    #             (
    #                 (session_id, info)
    #                 for session_id, info in cls.__active_session.items()
    #                 if info["controller_id"] == client_id
    #                 or info["host_id"] == client_id
    #             ),
    #             (None, None),
    #         )

    @classmethod
    def get_all_sessions(
        cls, client_id: str
    ) -> dict[str, dict[str, Union[str, float]]]:
        """Lấy tất cả session của một client"""
        with cls.__lock:
            return {
                session_id: info
                for session_id, info in cls.__active_session.items()
                if info["controller_id"] == client_id or info["host_id"] == client_id
            }

    @classmethod
    def is_client_in_session(cls, client_id: str, session_id: str) -> bool:
        """Kiểm tra xem client có đang trong session không"""
        with cls.__lock:
            if session_id in cls.__active_session:
                session_info = cls.__active_session[session_id]
                return (
                    session_info["controller_id"] == client_id
                    or session_info["host_id"] == client_id
                )
            return False
