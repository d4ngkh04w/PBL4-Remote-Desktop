import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SessionResources:
    """Lưu trữ tất cả tài nguyên của một session."""

    role: str
    decoder: Optional[Any] = None
    config: Optional[dict] = None
    widget: Optional[Any] = (
        None  # RemoteWidget (có controller bên trong) hoặc None cho host
    )
    screen_share_service: Optional[Any] = None

    def cleanup(self):
        """Dọn dẹp tất cả tài nguyên của session."""
        try:
            # Đóng decoder
            if self.decoder and hasattr(self.decoder, "close"):
                self.decoder.close()
                logger.debug("Decoder closed")

            # Dừng screen share service
            if self.screen_share_service and hasattr(self.screen_share_service, "stop"):
                self.screen_share_service.stop()
                logger.info("Screen share service stopped")

            # Đóng widget
            if self.widget and hasattr(self.widget, "close"):
                self.widget.close()
                logger.debug("Widget closed")

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}", exc_info=True)


class SessionManager:
    """Quản lý các phiên làm việc của client (controller / host)."""

    _sessions: Dict[str, SessionResources] = {}

    @classmethod
    def create_session(cls, session_id: str, role: str):
        """Tạo session mới và khởi tạo các resources cần thiết."""
        # Tạo session
        cls._sessions[session_id] = SessionResources(role=role)

        try:
            if role == "controller":
                cls._create_controller_session(session_id)
            elif role == "host":
                cls._create_host_session(session_id)
            else:
                logger.warning(f"Unknown role: {role} for session: {session_id}")

        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}", exc_info=True)
            # Cleanup nếu có lỗi
            cls.remove_session(session_id)
            raise

    @classmethod
    def _create_controller_session(cls, session_id: str):
        """Tạo controller session - yêu cầu MainWindowController tạo widget."""
        from client.controllers.main_window_controller import MainWindowController

        main_controller = MainWindowController.get_instance()
        if main_controller:
            main_controller.widget_creation_requested.emit(session_id)
        else:
            logger.error("MainWindowController not found")

    @classmethod
    def _create_host_session(cls, session_id: str):
        """Tạo host session - thêm vào centralized screen share service."""
        from client.services.centralized_screen_share_service import (
            centralized_screen_share_service,
        )

        # Thêm session vào centralized service
        centralized_screen_share_service.add_session(session_id)
        logger.info(f"Added session to centralized screen sharing: {session_id}")

    @classmethod
    def remove_session(cls, session_id: str):
        """Xóa phiên làm việc và dọn dẹp tài nguyên."""
        if session_id in cls._sessions:
            session_resource = cls._sessions[session_id]
            logger.info(
                f"Removing session: {session_id} (role: {session_resource.role})"
            )

            # Nếu là host session, xóa khỏi centralized service
            if session_resource.role == "host":
                from client.services.centralized_screen_share_service import (
                    centralized_screen_share_service,
                )

                centralized_screen_share_service.remove_session(session_id)

            # Dọn dẹp tài nguyên
            session_resource.cleanup()

            # Xóa session
            del cls._sessions[session_id]
            logger.info(f"Session removed: {session_id}")

    # ---------------------------
    # Quản lý Decoder
    # ---------------------------

    @classmethod
    def set_session_decoder(cls, session_id: str, decoder):
        """Đặt decoder cho session."""
        if session_id in cls._sessions:
            cls._sessions[session_id].decoder = decoder
            logger.debug(f"Set decoder for session: {session_id}")

    @classmethod
    def get_session_decoder(cls, session_id: str):
        """Lấy decoder cho session."""
        session = cls._sessions.get(session_id)
        return session.decoder if session else None

    # ---------------------------
    # Quản lý Config
    # ---------------------------

    @classmethod
    def set_session_config(cls, session_id: str, config: dict):
        """Đặt config cho session."""
        if session_id in cls._sessions:
            cls._sessions[session_id].config = config
            logger.debug(f"Set config for session: {session_id}")

    # @classmethod
    # def get_session_config(cls, session_id: str):
    #     """Lấy config cho session."""
    #     session = cls._sessions.get(session_id)
    #     return session.config if session else None

    # ---------------------------
    # Quản lý Screen Share Service
    # ---------------------------

    @classmethod
    def set_screen_share_service(cls, session_id: str, service):
        """Đặt screen share service cho session."""
        if session_id in cls._sessions:
            cls._sessions[session_id].screen_share_service = service
            logger.info(f"Set screen share service for session: {session_id}")

    # @classmethod
    # def get_screen_share_service(cls, session_id: str):
    #     """Lấy screen share service cho session."""
    #     session = cls._sessions.get(session_id)
    #     return session.screen_share_service if session else None

    # ---------------------------
    # Quản lý Widget
    # ---------------------------

    @classmethod
    def get_session_widget(cls, session_id: str):
        """Lấy widget cho session."""
        session = cls._sessions.get(session_id)
        return session.widget if session else None

    # ---------------------------
    # Các hàm kiểm tra trạng thái
    # ---------------------------

    # @classmethod
    # def is_in_session(cls) -> bool:
    #     """Kiểm tra có đang trong bất kỳ phiên làm việc nào không."""
    #     return bool(cls._sessions)

    # @classmethod
    # def is_in_hosting_session(cls) -> bool:
    #     """Kiểm tra có đang trong phiên làm việc với vai trò host không."""
    #     return any(session.role == "host" for session in cls._sessions.values())

    # @classmethod
    # def is_in_controlling_session(cls) -> bool:
    #     """Kiểm tra có đang trong phiên làm việc với vai trò controller không."""
    #     return any(session.role == "controller" for session in cls._sessions.values())

    # ---------------------------
    # Hàm lấy thông tin vai trò
    # ---------------------------

    # @classmethod
    # def get_roles(cls) -> set[str]:
    #     """Lấy danh sách vai trò hiện có (ví dụ: {'host', 'controller'})."""
    #     return {session.role for session in cls._sessions.values()}

    # @classmethod
    # def get_role(cls, session_id: str) -> str | None:
    #     """Lấy vai trò của client trong một phiên cụ thể."""
    #     session = cls._sessions.get(session_id)
    #     return session.role if session else None

    # @classmethod
    # def get_all_sessions(cls) -> Dict[str, str]:
    #     """Lấy tất cả sessions hiện có dưới dạng dict {session_id: role}."""
    #     return {
    #         session_id: session.role for session_id, session in cls._sessions.items()
    #     }

    @classmethod
    def session_exists(cls, session_id: str) -> bool:
        """Kiểm tra session có tồn tại không."""
        return session_id in cls._sessions
