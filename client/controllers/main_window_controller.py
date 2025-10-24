import logging
from PyQt5.QtCore import QObject, pyqtSignal

from client.managers.client_manager import ClientManager
from common.utils import format_numeric_id

logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """
    Controller chính cho ứng dụng - chỉ chứa logic, không tương tác trực tiếp với UI.
    """

    # --- Signals gửi đi cho View ---
    status_updated = pyqtSignal(str)
    id_updated = pyqtSignal(str)
    password_updated = pyqtSignal(str)
    tabs_state_changed = pyqtSignal(bool)
    notification_requested = pyqtSignal(
        str, str
    )  # message, type ('info', 'warning', 'error')

    connect_button_state_changed = pyqtSignal(bool, str)  # enabled, text
    text_copied_to_clipboard = pyqtSignal(str, str)  # type ('ID', 'Password'), content
    widget_creation_requested = pyqtSignal(
        str
    )  # session_id - for creating widgets in main thread

    def __init__(self):
        super().__init__()
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._running = False
        logger.debug("MainWindowController initialized.")

    def start(self):
        if self._running:
            return
        self._running = True
        logger.debug("MainWindowController started.")

    def stop(self):
        if not self._running:
            return
        self._running = False
        logger.debug("MainWindowController stopped.")

    # --- Xử lý sự kiện từ các thành phần khác của ứng dụng ---

    def on_connection_established(self):
        self.status_updated.emit("Connected to server")

    def on_connection_failed(self):
        self.status_updated.emit("Failed to connect to server")
        self.id_updated.emit("Connection Failed")
        self.notification_requested.emit(
            "Could not connect to the server. Please check your connection and restart.",
            "error",
        )

    def on_client_id_received(self):
        client_id = ClientManager.get_client_id()
        self.id_updated.emit(format_numeric_id(client_id))
        self.tabs_state_changed.emit(True)

    def on_ui_update_status(self, status: str):
        self.status_updated.emit(status)

    def on_ui_show_notification(self, message: str, type: str):
        self.notification_requested.emit(message, type)

    # --- Xử lý yêu cầu từ View ---

    def connect_to_partner(self, host_id: str, host_pass: str):
        """Xác thực đầu vào và gửi yêu cầu kết nối."""
        if not host_id or not host_pass:
            self.notification_requested.emit(
                "Host ID and Password cannot be empty.", "warning"
            )
            return

        if len(host_id) != 9 or not host_id.isdigit():
            self.notification_requested.emit("Host ID must be 9 digits.", "warning")
            return

        if host_id == ClientManager.get_client_id():
            self.notification_requested.emit(
                "You cannot connect to your own ID.", "warning"
            )
            return

        # Logic nghiệp vụ thành công, gửi yêu cầu và cập nhật UI
        from client.handlers.send_handler import SendHandler

        SendHandler.send_connection_request_packet(host_id, host_pass)

        self.connect_button_state_changed.emit(False, "🔄 Connecting...")
        self.status_updated.emit(f"Sending connection request to {host_id}...")

    def request_new_password(self):
        """Tạo mật khẩu mới và yêu cầu View cập nhật."""
        ClientManager.generate_new_password()
        password = ClientManager.get_password()
        self.password_updated.emit(password)
        self.status_updated.emit("New password generated.")

    def request_copy_id(self):
        """Lấy ID và yêu cầu View sao chép vào clipboard."""
        client_id = ClientManager.get_client_id()
        self.text_copied_to_clipboard.emit("ID", client_id)

    def request_copy_password(self):
        """Lấy mật khẩu và yêu cầu View sao chép vào clipboard."""
        password = ClientManager.get_password()
        self.text_copied_to_clipboard.emit("Password", password)

    def notify_session_ended(self, session_id: str):
        """Nhận thông báo từ View rằng một session đã kết thúc."""
        try:
            from client.handlers.send_handler import SendHandler

            SendHandler.send_end_session_packet(session_id)
            self.status_updated.emit(f"Session {session_id} ended.")
            logger.info(f"Notified server about ending session: {session_id}")
        except Exception as e:
            logger.error(
                f"Error notifying server about session end: {e}", exc_info=True
            )

    def end_all_sessions(self):
        """Kết thúc tất cả sessions - gọi khi đóng ứng dụng."""
        try:
            from client.managers.session_manager import SessionManager
            from client.handlers.send_handler import SendHandler

            session_ids = SessionManager.get_all_session_ids()
            if session_ids:
                logger.info(f"Ending all sessions: {session_ids}")
                for session_id in session_ids:
                    try:
                        SendHandler.send_end_session_packet(session_id)
                        logger.debug(f"Sent end session packet for: {session_id}")
                    except Exception as e:
                        logger.error(f"Error sending end session for {session_id}: {e}")

                # Dọn dẹp tất cả sessions locally
                SessionManager.cleanup_all_sessions()
                self.status_updated.emit("All sessions ended.")
            else:
                logger.debug("No active sessions to end")
        except Exception as e:
            logger.error(f"Error ending all sessions: {e}", exc_info=True)

    # --- Dọn dẹp ---
    def cleanup(self):
        """Dọn dẹp tài nguyên của controller."""
        try:
            # Kết thúc tất cả sessions trước khi dọn dẹp
            self.end_all_sessions()
            self.stop()
            logger.debug("MainWindowController cleanup completed")
        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}", exc_info=True)


main_window_controller = MainWindowController()
