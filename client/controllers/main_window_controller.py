import logging
import os

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QIcon

from client.managers.client_manager import ClientManager
from common.utils import format_numeric_id

logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """
    Controller chính cho ứng dụng - chỉ chứa logic, không tương tác trực tiếp với UI.
    """

    # --- Signals gửi đi cho View ---
    id_updated = pyqtSignal(str)
    password_updated = pyqtSignal(str)
    notification_requested = pyqtSignal(
        str, str
    )  # message, type ('info', 'warning', 'error')
    custom_password_changed = pyqtSignal()  # Thông báo khi custom password thay đổi

    connect_button_state_changed = pyqtSignal(bool, str)  # enabled, text
    text_copied_to_clipboard = pyqtSignal(str, str)  # type ('ID', 'Password'), content
    widget_creation_requested = pyqtSignal(
        str
    )  # session_id - for creating widgets in main thread

    def __init__(self):
        super().__init__()
        self.__running = False
        logger.debug("MainWindowController initialized.")

    def start(self):
        if self.__running:
            return
        self.__running = True
        logger.debug("MainWindowController started.")

    def stop(self):
        if not self.__running:
            return
        self.__running = False
        logger.debug("MainWindowController stopped.")

    # --- Xử lý sự kiện từ các thành phần khác của ứng dụng ---

    def on_connection_failed(self):
        self.id_updated.emit("Connection Failed")
        self.notification_requested.emit(
            "Could not connect to the server. Please check your connection and restart.",
            "error",
        )

    def on_client_id_received(self):
        client_id = ClientManager.get_client_id()
        self.id_updated.emit(format_numeric_id(client_id))
        # Sau khi load client ID, custom password cũng đã được load, cần cập nhật UI
        self.custom_password_changed.emit()

    def on_connection_rejected(self):
        """Re-enable connect button when connection is rejected"""
        self.connect_button_state_changed.emit(True, "")

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

        from client.handlers.send_handler import SendHandler

        SendHandler.send_connection_request_packet(host_id, host_pass)

        self.connect_button_state_changed.emit(False, "Connecting...")

    def request_new_password(self):
        """Tạo mật khẩu mới và yêu cầu View cập nhật."""
        ClientManager.generate_new_password()
        password = ClientManager.get_password()
        self.password_updated.emit(password)

    def request_copy_id(self):
        """Lấy ID và yêu cầu View sao chép vào clipboard."""
        client_id = ClientManager.get_client_id()
        self.text_copied_to_clipboard.emit("ID", client_id)

    def request_copy_password(self):
        """Lấy mật khẩu và yêu cầu View sao chép vào clipboard."""
        password = ClientManager.get_password()
        self.text_copied_to_clipboard.emit("Password", password)

    def request_set_custom_password(self):
        """Yêu cầu View hiển thị dialog để đặt mật khẩu tự đặt."""
        from client.gui.password_dialog import PasswordDialog

        # Tạo dialog
        dialog = PasswordDialog()

        # Hiển thị dialog và chờ kết quả
        if dialog.exec_() == PasswordDialog.Accepted:
            password = dialog.get_password()

            # Set mật khẩu
            ClientManager.set_custom_password(password)
            self.notification_requested.emit(
                "Custom password has been set successfully!", "info"
            )
            self.custom_password_changed.emit()  # Thông báo UI cập nhật

    def request_remove_custom_password(self):
        """Yêu cầu xóa mật khẩu tự đặt."""
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtCore import Qt

        # Kiểm tra xem có mật khẩu tự đặt không
        if ClientManager.get_custom_password() is None:
            self.notification_requested.emit(
                "No custom password is currently set", "info"
            )
            return

        # Xác nhận xóa
        msg_box = QMessageBox()
        msg_box.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        msg_box.setText("Are you sure you want to remove your custom password?")
        msg_box.setIconPixmap(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "info.png",
                )
            ).pixmap(64, 64)
        )
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        # Apply dark theme styling
        msg_box.setStyleSheet(
            """
            QMessageBox {
                background-color: #1a1a1a;
                color: #e8e8e8;
                border: 2px solid #2d2d2d;
                border-radius: 10px;
            }
            QMessageBox QLabel {
                color: #e8e8e8;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px 24px;
                color: #e8e8e8;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #242424;
            }
        """
        )

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            ClientManager.set_custom_password(None)
            self.notification_requested.emit(
                "Custom password has been removed.", "info"
            )
            self.custom_password_changed.emit()  # Thông báo UI cập nhật

    # --- Dọn dẹp ---
    def cleanup(self):
        """Dọn dẹp tài nguyên của controller."""
        try:
            # Kết thúc tất cả sessions trước khi dọn dẹp
            from client.managers.session_manager import SessionManager

            SessionManager.cleanup_all_sessions()

            self.stop()
            logger.debug("MainWindowController cleanup completed")
        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}", exc_info=True)


main_window_controller = MainWindowController()
