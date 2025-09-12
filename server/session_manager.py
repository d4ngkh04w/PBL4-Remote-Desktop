import logging
import threading
import time

from common.utils import generate_numeric_id, format_numeric_id
from server.client_manager import ClientManager

logger = logging.getLogger(__name__)


class SessionManager:
    __active_session: dict[str, dict[str, str | float]] = {}
    _lock = threading.Lock()
    _cleanup_thread_started = False

    @classmethod
    def start_cleanup(cls, interval: int = 30):
        if cls._cleanup_thread_started:
            return
        cls._cleanup_thread_started = True

        def _cleanup_loop():
            while True:
                time.sleep(interval)
                cls._cleanup_expired_sessions()

        t = threading.Thread(target=_cleanup_loop, daemon=True)
        t.start()
        logger.info("Session cleanup started")

    @classmethod
    def _cleanup_expired_sessions(cls):
        with cls._lock:
            now = time.time()
            expired_sessions = [
                sid
                for sid, info in cls.__active_session.items()
                if info["expires_at"] < now
            ]
            for sid in expired_sessions:
                logger.info(f"Session {sid} expired, removing...")
                cls.end_session(sid)

    @classmethod
    def create_session(cls, controller_id: str, host_id: str):
        """Tạo session mới"""
        with cls._lock:
            try:
                if not ClientManager.is_client_online(controller_id):
                    raise ValueError(f"Controller {controller_id} is not online")
                if not ClientManager.is_client_online(host_id):
                    raise ValueError(f"Host {host_id} is not online")

                session_id = format_numeric_id(generate_numeric_id(9)).replace(" ", "-")

                ClientManager.update_client_status(controller_id, "IN_SESSION")
                ClientManager.update_client_status(host_id, "IN_SESSION")

                cls.__active_session[session_id] = {
                    "controller_id": controller_id,
                    "host_id": host_id,
                    "status": "ACTIVE",
                    "expires_at": time.time() + 3600,
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
        with cls._lock:
            try:
                if session_id in cls.__active_session:
                    session_info = cls.__active_session[session_id]

                    ClientManager.update_client_status(
                        str(session_info["controller_id"]), "ONLINE"
                    )
                    ClientManager.update_client_status(
                        str(session_info["host_id"]), "ONLINE"
                    )

                    del cls.__active_session[session_id]

                    logger.info(f"Session {session_id} ended")
                    return True
            except Exception as e:
                logger.error(f"Failed to end session {session_id}: {e}")
                return False

    @classmethod
    def get_client_sessions(
        cls, client_id: str
    ) -> tuple[str, dict[str, str | float]] | tuple[None, None]:
        """Lấy session của một client"""
        with cls._lock:
            return next(
                (
                    (session_id, info)
                    for session_id, info in cls.__active_session.items()
                    if info["controller_id"] == client_id
                    or info["host_id"] == client_id
                ),
                (None, None),
            )

    @classmethod
    def is_client_in_session(cls, client_id: str) -> bool:
        """Kiểm tra xem client có đang trong session không"""
        with cls._lock:
            for session in cls.__active_session.values():
                if (
                    session["controller_id"] == client_id
                    or session["host_id"] == client_id
                ):
                    return True
            return False
