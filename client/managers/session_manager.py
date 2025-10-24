import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SessionResources:
    """Lưu trữ tất cả tài nguyên của một session."""

    role: str
    decoder: Optional[Any] = None
    widget: Optional[Any] = (
        None  # RemoteWidget (có controller bên trong) hoặc None cho host
    )
    keyboard_executor: Optional[Any] = None  # KeyboardExecutorService cho host

    def cleanup(self):
        """Dọn dẹp tất cả tài nguyên của session."""
        try:
            # Đóng decoder
            if self.decoder and hasattr(self.decoder, "close"):
                self.decoder.close()
                logger.debug("Decoder closed")

            # Đóng widget
            if self.widget and hasattr(self.widget, "close"):
                self.widget.close()
                logger.debug("Widget closed")

            # Dừng keyboard executor
            if self.keyboard_executor and hasattr(self.keyboard_executor, "stop"):
                self.keyboard_executor.stop()
                logger.debug("Keyboard executor stopped")

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}", exc_info=True)


class SessionManager:
    """Quản lý các phiên làm việc của client (controller / host)."""

    _sessions: Dict[str, SessionResources] = {}

    @classmethod
    def create_session(cls, session_id: str, role: str):
        """Tạo session mới và khởi tạo các resources cần thiết."""
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
            cls.remove_session(session_id)
            raise

    @classmethod
    def _create_controller_session(cls, session_id: str):
        """Tạo controller session - yêu cầu MainWindowController tạo widget."""
        from client.controllers.main_window_controller import main_window_controller

        main_window_controller.widget_creation_requested.emit(session_id)

    @classmethod
    def _create_host_session(cls, session_id: str):
        """Tạo host session - thêm vào screen share service và khởi tạo keyboard executor."""
        from client.services.screen_share_service import screen_share_service
        from client.services.keyboard_executor_service import KeyboardExecutorService

        # Thêm session vào screen share service
        screen_share_service.add_session(session_id)
        logger.info(f"Added session to screen sharing: {session_id}")

        # Khởi tạo keyboard executor cho host session
        keyboard_executor = KeyboardExecutorService()
        keyboard_executor.start()
        cls._sessions[session_id].keyboard_executor = keyboard_executor
        logger.info(f"Created keyboard executor for host session: {session_id}")

    @classmethod
    def remove_session(cls, session_id: str):
        """Xóa phiên làm việc và dọn dẹp tài nguyên."""
        if session_id in cls._sessions:
            session_resource = cls._sessions[session_id]
            logger.info(
                f"Removing session: {session_id} (role: {session_resource.role})"
            )

            # Nếu là host session, xóa khỏi screen share service
            if session_resource.role == "host":
                from client.services.screen_share_service import screen_share_service

                screen_share_service.remove_session(session_id)

            # Dọn dẹp tài nguyên
            session_resource.cleanup()

            # Xóa session
            del cls._sessions[session_id]  # ---------------------------

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
    # Quản lý Keyboard Executor
    # ---------------------------

    @classmethod
    def get_session_keyboard_executor(cls, session_id: str):
        """Lấy keyboard executor cho session."""
        session = cls._sessions.get(session_id)
        return session.keyboard_executor if session else None

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

    @classmethod
    def session_exists(cls, session_id: str) -> bool:
        """Kiểm tra session có tồn tại không."""
        return session_id in cls._sessions

    @classmethod
    def get_all_session_ids(cls) -> list[str]:
        """Lấy danh sách tất cả session IDs hiện tại."""
        return list(cls._sessions.keys())

    @classmethod
    def get_session_role(cls, session_id: str) -> Optional[str]:
        """Lấy role của session."""
        session = cls._sessions.get(session_id)
        return session.role if session else None

    @classmethod
    def cleanup_all_sessions(cls):
        """Dọn dẹp tất cả sessions - dùng khi đóng ứng dụng."""
        session_ids = list(cls._sessions.keys())
        for session_id in session_ids:
            cls.remove_session(session_id)
        logger.info("All sessions cleaned up")
