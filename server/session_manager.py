import logging

from common.utils import generate_numeric_id, format_numeric_id
from server.client_manager import ClientManager

logger = logging.getLogger(__name__)


class SessionManager:
    __active_session: dict[str, dict[str, str]] = {}

    @classmethod
    def create_session(cls, controller_id: str, host_id: str):
        """Tạo session mới"""
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
        try:
            if session_id in cls.__active_session:
                session_info = cls.__active_session[session_id]

                ClientManager.update_client_status(
                    session_info["controller_id"], "ONLINE"
                )
                ClientManager.update_client_status(session_info["host_id"], "ONLINE")

                del cls.__active_session[session_id]

                logger.info(f"Session {session_id} ended")
                return True
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False

    @classmethod
    def get_session_info(cls, session_id: str):
        """Lấy thông tin session"""
        logger.debug(f"Getting info for session {cls.__active_session}")
        return cls.__active_session.get(session_id)

    @classmethod
    def get_client_sessions(
        cls, client_id: str
    ) -> tuple[str, dict[str, str]] | tuple[None, None]:
        """Lấy session của một client"""
        return next(
            (
                (session_id, info)
                for session_id, info in cls.__active_session.items()
                if info["controller_id"] == client_id or info["host_id"] == client_id
            ),
            (None, None),
        )

    @classmethod
    def is_client_in_session(cls, client_id: str) -> bool:
        """Kiểm tra xem client có đang trong session không"""
        for session in cls.__active_session.values():
            if session["controller_id"] == client_id or session["host_id"] == client_id:
                return True
        return False
