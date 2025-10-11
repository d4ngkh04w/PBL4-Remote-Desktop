import logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, Qt
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.managers.client_manager import ClientManager
from client.managers.connection_manager import ConnectionManager
from common.utils import format_numeric_id


logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """
    Điều khiển chính cho cửa sổ chính.
    """

    _instance = None

    # Signals for UI updates (run in main thread)
    update_status = pyqtSignal(str)  # message
    update_id_display = pyqtSignal(str)  # client_id
    update_password_display = pyqtSignal(str)  # new_password
    enable_tabs = pyqtSignal(bool)  # enable controller tab
    show_notification = pyqtSignal(str, str)  # message, type
    create_remote_widget = pyqtSignal(str)  # session_id - signal to create remote widget

    def __init__(self, main_window, config):
        super().__init__()
        self.main_window = main_window
        self._running = False

        self.config = config
        self.connection_manager = None

        # Set as singleton instance
        MainWindowController._instance = self

        # Connect internal signals to UI methods
        self.update_status.connect(self._update_status_ui)
        self.update_id_display.connect(self._update_id_display_ui)
        self.enable_tabs.connect(self._enable_tabs_ui)
        self.show_notification.connect(self._show_notification_dialog)
        self.create_remote_widget.connect(self._create_remote_desktop_widget)
        self.update_password_display.connect(self._update_password_display_ui)

    def start(self):
        """Bắt đầu điều khiển"""
        if self._running:
            return

        self._running = True
        logger.info("MainWindowController started")

        self.__initialize_network_connection__()

    def stop(self):
        """Dừng điều khiển"""
        if not self._running:
            return

        self._running = False
        logger.info("MainWindowController stopped")

    def __initialize_network_connection__(self):
        """
        Khởi tạo và kết nối ConnectionManager.
        """
        self.connection_manager = ConnectionManager(
            self.config.get("server_host", "localhost"),
            self.config.get("server_port", 12345),
            self.config.get("use_ssl", False),
            self.config.get("cert_file", None),
        )
        self.connection_manager.connect()
        logger.debug("ConnectionManager initialized and connecting")

    # ====== METHODS FOR SIGNALS ======
    @classmethod
    def on_connection_established(cls):
        """Handle connection established"""
        if cls._instance:
            cls._instance.update_status.emit("Connected to server", "success")

    @classmethod
    def on_connection_failed(cls):
        """Handle connection failed"""
        if cls._instance:
            cls._instance.update_status.emit("Failed to connect to server", "error")
            cls._instance._show_connection_error()

    @classmethod
    def on_connection_reconnecting(cls, data):
        """Handle reconnecting to server"""
        if cls._instance:
            attempts = data.get("attempt", 0) if data else 0
            cls._instance.update_status.emit(
                f"Reconnecting to server... ({attempts})", "info"
            )

    @classmethod
    def on_client_id_received(cls):
        """Handle client ID received from server"""
        if not cls._instance:
            return

        cls._instance.update_id_display.emit(
            format_numeric_id(ClientManager.get_client_id())
        )
        cls._instance.enable_tabs.emit(True)

    @classmethod
    def on_ui_update_status(cls, message: str):
        """Handle UI status update requests"""
        if not cls._instance:
            return

        cls._instance.update_status.emit(message)

    @classmethod
    def on_ui_show_notification(cls, message: str, notif_type: str = "info"):
        """Handle UI notification display requests"""
        if not cls._instance:
            return

        cls._instance.show_notification.emit(message, notif_type)

    # ====== CONTROLLER ACTIONS ======
    @classmethod
    def on_create_remote_widget(cls, session_id: str):
        """Handle successful connection to host - show remote desktop"""
        if cls._instance:
            logger.info(
                "Connected to host successfully, creating remote desktop widget"
            )
            cls._instance.create_remote_widget.emit()

    def connect_to_partner(self, host_id: str, host_pass: str):
        """Handle connect to partner request"""
        # Validation
        if not host_id:
            QMessageBox.warning(self.main_window, "Input Error", "Please enter Host ID")
            return False

        if len(host_id) != 9 or not host_id.isdigit():
            QMessageBox.warning(
                self.main_window, "Invalid ID", "Host ID must be exactly 9 digits"
            )
            return False

        if host_id == ClientManager.get_client_id():
            QMessageBox.warning(
                self.main_window, "Invalid ID", "Host ID cannot be your own ID"
            )
            return False

        if not host_pass:
            QMessageBox.warning(
                self.main_window, "Input Error", "Please enter Host Password"
            )
            return False

        # Update UI state
        if hasattr(self.main_window, "connect_btn"):
            self.main_window.connect_btn.setEnabled(False)
            self.main_window.connect_btn.setText("🔄 Connecting...")

        from client.handlers.controller_handle import ControllerHandler

        ControllerHandler.send_connection_request(host_id, host_pass)

        self.update_status.emit("Connection request sent", "info")

    # ====== UI UPDATE METHODS (THREAD-SAFE) ======

    def _update_status_ui(self, message: str):
        """Update status bar in main thread"""
        if hasattr(self.main_window, "status_bar"):
            self.main_window.status_bar.showMessage(message)
        elif hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage(message)

    def _update_id_display_ui(self, client_id: str):
        """Update ID display in main thread"""
        logger.debug("_update_id_display_ui called with client_id: %s", client_id)
        if hasattr(self.main_window, "id_display"):
            self.main_window.id_display.setText(client_id)
            logger.debug("ID display updated to: %s", client_id)
            # Keep the original styling (don't clear it)
            self.main_window.id_display.setStyleSheet(
                """
                QLabel {
                    font-size: 28px;
                    font-weight: bold;
                    color: #0066cc;
                    background-color: #f8f9fa;
                    border: 2px dashed #0066cc;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 5px;
                }
                """
            )
        else:
            logger.error("main_window does not have id_display attribute")

    def _show_notification_dialog(self, message: str, notif_type: str):
        """Show notification message in main thread"""
        if notif_type == "error":
            QMessageBox.critical(self.main_window, "Error", message)
        elif notif_type == "warning":
            QMessageBox.warning(self.main_window, "Warning", message)
        else:
            QMessageBox.information(self.main_window, "Information", message)

    def _enable_tabs_ui(self, enable: bool):
        """Enable/disable tabs in main thread"""
        if hasattr(self.main_window, "tabs"):
            self.main_window.tabs.setTabEnabled(1, enable)

    def _show_connection_error(self):
        """Show connection error in UI"""
        if hasattr(self.main_window, "id_display"):
            self.main_window.id_display.setText("Connection Failed")
            self.main_window.id_display.setStyleSheet(
                """
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #dc3545;
                    background-color: #f8d7da;
                    border: 2px dashed #dc3545;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 5px;
                }
                """
            )
        self.enable_tabs.emit(False)

    def _create_remote_desktop_widget(self):
        """Create remote desktop widget for controller in a new resizable window"""
        try:
            # Import RemoteWidget
            from client.gui.remote_widget import RemoteWidget

            # Since we now use SocketClient as singleton, RemoteWidget can access it directly
            # No need to pass socket_client instance anymore
            self.main_window.remote_widget = RemoteWidget(None, None)

            # Set window properties for resizable window
            self.main_window.remote_widget.setWindowTitle("Remote Desktop - PBL4")
            self.main_window.remote_widget.resize(1024, 768)  # Set initial size

            # Make it a normal resizable window - just use default window flags
            # The default flags already provide minimize, maximize, close buttons

            # Connect disconnect signal from remote widget
            self.main_window.remote_widget.disconnect_requested.connect(
                self.disconnect_from_partner
            )

            # Show as normal window
            self.main_window.remote_widget.show()

            # Update connect button
            if hasattr(self.main_window, "connect_btn"):
                self.main_window.connect_btn.setText("🔌 Disconnect")
                self.main_window.connect_btn.clicked.disconnect()
                self.main_window.connect_btn.clicked.connect(
                    self.disconnect_from_partner
                )
                self.main_window.connect_btn.setEnabled(True)

            logger.info(
                "Remote desktop widget created successfully as resizable window"
            )

        except Exception as e:
            logger.error(f"Error creating remote widget: {e}")
            self.reset_connect_button()

    def _update_password_display_ui(self):
        """Update password display in main thread"""
        if hasattr(self.main_window, "password_display"):
            ClientManager.generate_new_password()
            self.main_window.password_display.setText(ClientManager.get_password())

    def _close_remote_desktop(self):
        """Close remote desktop widget"""
        if (
            hasattr(self.main_window, "remote_widget")
            and self.main_window.remote_widget
        ):
            # Close the fullscreen window
            self.main_window.remote_widget.close()

            # Cleanup widget
            if hasattr(self.main_window.remote_widget, "cleanup"):
                self.main_window.remote_widget.cleanup()
            self.main_window.remote_widget = None

    def reset_connect_button(self):
        """Reset connect button state"""
        if hasattr(self.main_window, "connect_btn"):
            self.main_window.connect_btn.setText("🔗 Connect to Partner")
            self.main_window.connect_btn.setEnabled(True)

            # Reconnect to controller connect method
            try:
                self.main_window.connect_btn.clicked.disconnect()
            except:
                pass

            self.main_window.connect_btn.clicked.connect(
                lambda: self.connect_to_partner(
                    (
                        self.main_window.host_id_input.text().strip()
                        if hasattr(self.main_window, "host_id_input")
                        else ""
                    ),
                    (
                        self.main_window.host_pass_input.text().strip()
                        if hasattr(self.main_window, "host_pass_input")
                        else ""
                    ),
                )
            )

    # ====== CLEANUP ======

    def cleanup(self):
        """Clean up controller resources"""
        try:
            self.stop()

            if (
                hasattr(self.main_window, "remote_widget")
                and self.main_window.remote_widget
            ):
                self._close_remote_desktop()

            if self.connection_manager:
                self.connection_manager.disconnect

            logger.info("MainWindowController cleanup completed")

        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}")
