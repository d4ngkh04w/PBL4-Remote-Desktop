import logging

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal

from client.managers.client_manager import ClientManager
from common.utils import format_numeric_id

logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """
    Controller chính cho MainWindow (singleton)
    """

    _instance = None

    # Định nghĩa signals đúng kiểu
    update_status = pyqtSignal(str)  # message
    update_id_display = pyqtSignal(str)  # client_id
    update_password_display = pyqtSignal()  # không truyền gì
    enable_tabs = pyqtSignal(bool)
    show_notification = pyqtSignal(str, str)  # message, type
    create_remote_widget = pyqtSignal(str)  # session_id

    def __new__(cls, *args, **kwargs):
        """Đảm bảo chỉ có 1 instance (Singleton)"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            logging.error("MainWindowController instance is not created yet.")
        return cls._instance

    def __init__(self, main_window, config):
        super().__init__()

        if getattr(self, "_initialized", False):
            return  # Tránh init lại

        self._initialized = True

        self.main_window = main_window
        self.config = config
        self.connection_manager = None
        self._running = False

        # Dictionary to track active remote widgets by session_id
        self.active_remote_widgets = {}

        # Kết nối signal với UI
        self.update_status.connect(self._update_status_ui)
        self.update_id_display.connect(self._update_id_display_ui)
        self.enable_tabs.connect(self._enable_tabs_ui)
        self.show_notification.connect(self._show_notification_dialog)
        self.create_remote_widget.connect(self._create_remote_desktop_widget)
        self.update_password_display.connect(self._update_password_display_ui)

    # ----------------------------
    # Public interface
    # ----------------------------

    def start(self):
        if self._running:
            return
        self._running = True
        logger.info("MainWindowController started")

    def stop(self):
        if not self._running:
            return
        self._running = False
        logger.info("MainWindowController stopped")

    # ----------------------------
    # Connection event handlers
    # ----------------------------

    def on_connection_established(self):
        self.update_status.emit("Connected to server")

    def on_connection_failed(self):
        self.update_status.emit("Failed to connect to server", "error")
        self._show_connection_error()

    def on_connection_reconnecting(self, attempts: int):
        self.update_status.emit(f"Reconnecting... ({attempts})", "info")

    def on_client_id_received(self):
        self.update_id_display.emit(format_numeric_id(ClientManager.get_client_id()))
        self.enable_tabs.emit(True)

    def on_ui_show_notification(self, message: str, notif_type: str):
        self.show_notification.emit(message, notif_type)

    def on_ui_update_status(self, message: str):
        self.update_status.emit(message)

    def on_create_remote_widget(self, session_id: str):
        self.create_remote_widget.emit(session_id)

    # ----------------------------
    # UI actions
    # ----------------------------

    def connect_to_partner(self, host_id: str, host_pass: str):
        if not host_id:
            QMessageBox.warning(self.main_window, "Input Error", "Please enter Host ID")
            return False

        if len(host_id) != 9 or not host_id.isdigit():
            QMessageBox.warning(
                self.main_window, "Invalid ID", "Host ID must be 9 digits"
            )
            return False

        if host_id == ClientManager.get_client_id():
            QMessageBox.warning(
                self.main_window, "Invalid ID", "Host ID cannot be your own"
            )
            return False

        if not host_pass:
            QMessageBox.warning(
                self.main_window, "Input Error", "Please enter Host Password"
            )
            return False

        from client.handlers.send_handler import SendHandler

        SendHandler.send_connection_request(host_id, host_pass)

        if hasattr(self.main_window, "connect_btn"):
            self.main_window.connect_btn.setEnabled(False)
            self.main_window.connect_btn.setText("🔄 Connecting...")

        self.update_status.emit("Connection request sent")

    # ----------------------------
    # UI update slots
    # ----------------------------

    def _update_status_ui(self, message: str):
        if hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage(message)

    def _update_id_display_ui(self, client_id: str):
        if hasattr(self.main_window, "id_display"):
            self.main_window.id_display.setText(client_id)

    def _show_notification_dialog(self, message: str, notif_type: str):
        if notif_type == "error":
            QMessageBox.critical(self.main_window, "Error", message)
        elif notif_type == "warning":
            QMessageBox.warning(self.main_window, "Warning", message)
        else:
            QMessageBox.information(self.main_window, "Information", message)

    def _enable_tabs_ui(self, enable: bool):
        if hasattr(self.main_window, "tabs"):
            self.main_window.tabs.setTabEnabled(1, enable)

    def _update_password_display_ui(self):
        ClientManager.generate_new_password()
        if hasattr(self.main_window, "password_display"):
            self.main_window.password_display.setText(ClientManager.get_password())

    def _create_remote_desktop_widget(self, session_id: str):
        """Create remote desktop widget for controlling partner's screen"""
        try:
            # Check if widget for this session already exists
            if session_id in self.active_remote_widgets:
                # Bring existing widget to front
                existing_widget = self.active_remote_widgets[session_id]
                existing_widget.show()
                existing_widget.raise_()
                existing_widget.activateWindow()
                logger.debug(
                    f"Brought existing remote widget to front for session: {session_id}"
                )
                return

            # Create new remote widget
            from client.gui.remote_widget import RemoteWidget

            remote_widget = RemoteWidget(session_id)

            # Track the widget
            self.active_remote_widgets[session_id] = remote_widget

            # Connect disconnect signal
            remote_widget.disconnect_requested.connect(
                self._handle_remote_widget_disconnect
            )

            # Show the widget as a separate window
            remote_widget.show()

            logger.debug(f"Created new remote desktop widget for session: {session_id}")

            if hasattr(self.main_window, "status_bar"):
                self.main_window.status_bar.showMessage(
                    f"Remote session started: {session_id}", 5000
                )

        except Exception as e:
            logger.error(f"Error creating remote desktop widget: {e}")
            self.show_notification.emit(
                f"Failed to create remote desktop: {str(e)}", "error"
            )

    def _handle_remote_widget_disconnect(self, session_id: str):
        """Handle disconnect from remote widget"""
        try:
            # Remove from tracking
            if session_id in self.active_remote_widgets:
                widget = self.active_remote_widgets.pop(session_id)
                widget.cleanup()

            logger.debug(f"Remote widget disconnected for session: {session_id}")

            # Notify handlers about disconnection
            from client.handlers.send_handler import SendHandler

            SendHandler.send_end_session_packet(session_id)

        except Exception as e:
            logger.error(f"Error handling remote widget disconnect: {e}")

    # def get_remote_widget(self, session_id: str):
    #     """Get remote widget for a specific session"""
    #     return self.active_remote_widgets.get(session_id)

    def close_all_remote_widgets(self):
        """Close all active remote widgets"""
        try:
            for widget in list(self.active_remote_widgets.values()):
                widget.close()
            self.active_remote_widgets.clear()
            logger.info("All remote widgets closed")
        except Exception as e:
            logger.error(f"Error closing remote widgets: {e}")

    # ----------------------------
    # Helper
    # ----------------------------

    def copy_id_to_clipboard(self):
        """Copy ID to clipboard"""
        from client.managers.client_manager import ClientManager

        client_id = ClientManager.get_client_id()
        if client_id:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(client_id)
                if self.main_window.status_bar is not None:
                    self.main_window.status_bar.showMessage(
                        "ID copied to clipboard!", 2000
                    )

    def copy_password_to_clipboard(self):
        """Copy password to clipboard"""
        from client.managers.client_manager import ClientManager

        password = ClientManager.get_password()
        if password:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(password)
                if self.main_window.status_bar is not None:
                    self.main_window.status_bar.showMessage(
                        "Password copied to clipboard!", 2000
                    )

    def _show_connection_error(self):
        if hasattr(self.main_window, "id_display"):
            self.main_window.id_display.setText("Connection Failed")

    def cleanup(self):
        self.stop()

        # Close all remote widgets
        self.close_all_remote_widgets()
        logger.info("MainWindowController cleanup completed")
