import logging
import threading
import time
import uuid
from typing import TypedDict
import queue
import heapq

from server.client_manager import ClientManager
from common.packets import SessionPacket
from common.enums import Status

logger = logging.getLogger(__name__)

SessionInfo = TypedDict(
    "SessionInfo",
    {
        "controller_id": str,
        "host_id": str,
        "status": str,
        "expires_at": float,
    },
)


class SessionManager:
    __active_session: dict[str, SessionInfo] = {}
    __client_to_sessions: dict[str, set[str]] = {}
    __expiry_heap: list[tuple[float, str]] = []
    __lock = threading.Lock()
    __cleanup_thread = None
    __stop_cleanup = threading.Event()

    @classmethod
    def start_cleanup(cls, interval: int = 30):
        if cls.__cleanup_thread and cls.__cleanup_thread.is_alive():
            return

        def __cleanup_loop():
            while not cls.__stop_cleanup.is_set():
                with cls.__lock:
                    if cls.__expiry_heap:
                        next_expiry = cls.__expiry_heap[0][0]
                        sleep_time = max(1, min(interval, next_expiry - time.time()))
                    else:
                        sleep_time = interval

                cls.__stop_cleanup.wait(timeout=max(1, sleep_time))

                if cls.__stop_cleanup.is_set():
                    break

                cls.__cleanup_expired_sessions()

        cls.__cleanup_thread = threading.Thread(target=__cleanup_loop, daemon=True)
        cls.__cleanup_thread.start()
        logger.info("Session cleanup started")

    @classmethod
    def __cleanup_expired_sessions(cls):
        now = time.time()
        expired = []

        with cls.__lock:
            while cls.__expiry_heap and cls.__expiry_heap[0][0] < now:
                _, sid = heapq.heappop(cls.__expiry_heap)

                if sid in cls.__active_session:
                    session_info = cls.__active_session[sid]
                    expired.append((sid, session_info))

        if expired:
            for sid, session_info in expired:
                controller_id = session_info["controller_id"]
                host_id = session_info["host_id"]

                response = SessionPacket(
                    status=Status.SESSION_TIMEOUT,
                    session_id=sid,
                )

                for client_id in [controller_id, host_id]:
                    client_queue = ClientManager.get_client_queue(client_id)
                    if client_queue:
                        try:
                            client_queue.put_nowait(response)
                        except queue.Full:
                            logger.warning(
                                f"Queue full for {client_id}, dropping timeout notification"
                            )

                cls.end_session(sid)

    @classmethod
    def shutdown(cls):
        """Shutdown cleanup thread"""
        if cls.__stop_cleanup.is_set():
            return

        cls.__stop_cleanup.set()

        if cls.__cleanup_thread is not None:
            cls.__cleanup_thread.join(timeout=5)

        with cls.__lock:
            cls.__active_session.clear()
            cls.__client_to_sessions.clear()
            cls.__expiry_heap.clear()
            logger.info("All active sessions cleared")

    @classmethod
    def create_session(
        cls, controller_id: str, host_id: str, timeout: float = 3600
    ) -> str:
        """Tạo session mới"""
        with cls.__lock:
            session_id = str(uuid.uuid4())
            expires_at = time.time() + timeout

            cls.__active_session[session_id] = {
                "controller_id": controller_id,
                "host_id": host_id,
                "status": "ACTIVE",
                "expires_at": expires_at,
            }

            heapq.heappush(cls.__expiry_heap, (expires_at, session_id))

            if controller_id not in cls.__client_to_sessions:
                cls.__client_to_sessions[controller_id] = set()
            if host_id not in cls.__client_to_sessions:
                cls.__client_to_sessions[host_id] = set()

            cls.__client_to_sessions[controller_id].add(session_id)
            cls.__client_to_sessions[host_id].add(session_id)

            logger.debug(
                f"Session {session_id} created between controller {controller_id} and host {host_id}"
            )

            return session_id

    @classmethod
    def end_session(cls, session_id: str):
        """Kết thúc session"""
        with cls.__lock:
            try:
                session_info = cls.__active_session.pop(session_id)
            except KeyError:
                logger.warning(f"Attempted to end non-existent session {session_id}")
                return

            controller_id = session_info["controller_id"]
            host_id = session_info["host_id"]

            for client_id in [controller_id, host_id]:
                client_sessions = cls.__client_to_sessions.get(client_id)
                if client_sessions:
                    client_sessions.discard(session_id)
                    if not client_sessions:
                        del cls.__client_to_sessions[client_id]

            logger.info(f"Session {session_id} ended")

    @classmethod
    def get_session(cls, session_id: str) -> SessionInfo | None:
        """Lấy thông tin session"""
        with cls.__lock:
            return cls.__active_session.get(session_id)

    @classmethod
    def get_all_sessions(cls, client_id: str) -> dict[str, SessionInfo]:
        """Lấy tất cả session của một client"""
        with cls.__lock:
            session_ids = cls.__client_to_sessions.get(client_id, set())
            return {
                session_id: cls.__active_session[session_id]
                for session_id in session_ids
                if session_id in cls.__active_session
            }

    @classmethod
    def is_client_in_session(cls, client_id: str, session_id: str) -> bool:
        """Kiểm tra xem client có đang trong session không"""
        with cls.__lock:
            return session_id in cls.__client_to_sessions.get(client_id, set())
