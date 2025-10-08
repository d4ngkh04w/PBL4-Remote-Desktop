import logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, Qt

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.service.auth_service import AuthService
from common.utils import format_numeric_id


logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """
    Main window controller focused on UI coordination.

    Responsibilities:
    - Handle UI events and user interactions
    - Coordinate between UI and services (direct calls)
    - Manage UI state changes
    - Show dialogs and messages
    """

    # Class variable to store the current instance
    _instance = None

    # Signals for UI updates (run in main thread)
    update_status = pyqtSignal(str, str)  # message, type
    update_id_display = pyqtSignal(str)  # client_id
    show_connection_request = pyqtSignal(
        str, str, str
    )  # controller_id, host_id, formatted_id
    enable_tabs = pyqtSignal(bool)  # enable controller tab
    show_notification = pyqtSignal(str, str)  # message, type
    create_remote_widget = pyqtSignal()  # signal to create remote widget

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._running = False

        # Set as singleton instance
        MainWindowController._instance = self

        self.host_pass: str = ""  # Store host password for connection requests

        # Connect internal signals to UI methods
        self.update_status.connect(self._update_status_ui)
        self.update_id_display.connect(self._update_id_display_ui)
        self.show_connection_request.connect(self._show_connection_request_dialog)
        self.enable_tabs.connect(self._enable_tabs_ui)
        self.show_notification.connect(self._show_notification_dialog)
        self.create_remote_widget.connect(self._create_remote_desktop_widget)

    def start(self):
        """Start the controller"""
        if self._running:
            return

        self._running = True
        logger.info("MainWindowController started")

    def stop(self):
        """Stop the controller"""
        if not self._running:
            return

        self._running = False
        logger.info("MainWindowController stopped")

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
    def on_connection_disconnected(cls):
        """Handle connection disconnected"""
        if cls._instance:
            cls._instance.update_status.emit("Disconnected from server", "warning")
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
    def on_client_id_received(cls, data):
        """Handle client ID received from server"""
        if not cls._instance:
            return

        if isinstance(data, dict):
            client_id = data.get("client_id")
            if client_id:
                cls._instance.update_id_display.emit(format_numeric_id(client_id))
                cls._instance.enable_tabs.emit(True)
            else:
                logger.error("No client_id found in data: %s", data)
        else:
            logger.error("Expected dict but got: %s", type(data))

    @classmethod
    def on_ui_update_status(cls, data):
        """Handle UI status update requests"""
        if not cls._instance:
            return

        if isinstance(data, dict):
            message = data.get("message", "")
            status_type = data.get("type", "info")
            cls._instance.update_status.emit(message, status_type)

    @classmethod
    def on_ui_show_notification_suggestion(cls, data):
        """Handle UI notification display requests"""
        if not cls._instance:
            return

        if isinstance(data, dict):
            controller_id = str(data.get("controller_id", ""))
            host_id = str(data.get("host_id", ""))
            formatted_id = data.get("formatted_controller_id", controller_id)
            cls._instance.show_connection_request.emit(
                controller_id, host_id, formatted_id
            )

    @classmethod
    def on_ui_show_notification(cls, data):
        """Handle UI notification display requests"""
        if not cls._instance:
            return

        if isinstance(data, dict):
            message = data.get("message", "Notification")
            cls._instance.show_notification.emit(message, data.get("type", "info"))

    # ====== CONTROLLER ACTIONS ======
    @classmethod
    def on_connected_to_host(cls, data):
        """Handle successful connection to host - show remote desktop"""
        if cls._instance:
            logger.info(
                "Connected to host successfully, creating remote desktop widget"
            )
            cls._instance.create_remote_widget.emit()
            cls._instance.update_status.emit(
                "✅ Connected - Remote desktop active", "success"
            )

    @classmethod
    def on_disconnected_with_host(cls, data):
        """Handle disconnection from host - reset UI"""
        if cls._instance:
            logger.info("Disconnected from host, resetting UI")
            cls._instance._close_remote_desktop()
            cls._instance.reset_connect_button()
            cls._instance.update_status.emit("Disconnected from host", "warning")

    @classmethod
    def get_host_password(cls):
        """Handle request for host password"""
        if not cls._instance:
            return ""

        # Get password from UI input
        if hasattr(cls._instance.main_window, "host_pass_input"):
            password = cls._instance.main_window.host_pass_input.text().strip()
            return password
        else:
            logger.error("No host_pass_input found in main_window")
            return ""

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

        if not host_pass:
            QMessageBox.warning(
                self.main_window, "Input Error", "Please enter Host Password"
            )
            return False

        # Update UI state
        if hasattr(self.main_window, "connect_btn"):
            self.main_window.connect_btn.setEnabled(False)
            self.main_window.connect_btn.setText("🔄 Connecting...")

        from client.service.connection_service import send_connection_request

        success = send_connection_request(host_id)
        if not success:
            self.update_status.emit("Failed to send connection request", "error")
            self.reset_connect_button()
        else:
            self.update_status.emit("Connection request sent", "info")
            # Store password for later use
            self.host_pass = host_pass

    def disconnect_from_partner(self):
        """Handle disconnect from partner"""
        # Close remote desktop widget if open
        if (
            hasattr(self.main_window, "remote_widget")
            and self.main_window.remote_widget
        ):
            self._close_remote_desktop()

        # Reset UI
        self.reset_connect_button()
        self.update_status.emit("Disconnected from partner", "info")

        logger.info("Disconnected from partner")

    def refresh_password(self):
        """Generate new password"""
        if AuthService:
            new_password = AuthService.generate_new_password()

            # Update UI
            if hasattr(self.main_window, "password_display"):
                self.main_window.password_display.setText(new_password)

            self.update_status.emit("Password refreshed", "info")
            logger.info("Password refreshed")

    # ====== UI UPDATE METHODS (THREAD-SAFE) ======

    def _update_status_ui(self, message: str, status_type: str):
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

    def _show_connection_request_dialog(
        self, controller_id: str, host_id: str, formatted_id: str
    ):
        """Show connection request dialog in main thread"""
        reply = QMessageBox.question(
            self.main_window,
            "Connection Request",
            f"Controller with ID {formatted_id} wants to connect. Accept?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Lazy import để tránh circular import
            from client.service.connection_service import accept_connection_request

            accept_connection_request(controller_id, host_id)
        else:
            # Lazy import để tránh circular import
            from client.service.connection_service import reject_connection_request

            reject_connection_request(controller_id, host_id)

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
            # Enable controller tab (usually index 1)
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

            logger.info("MainWindowController cleanup completed")

        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}")
