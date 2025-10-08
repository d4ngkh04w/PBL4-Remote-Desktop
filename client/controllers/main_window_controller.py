import logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, Qt

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.core.callback_manager import callback_manager
from client.service.auth_service import get_auth_service
from common.utils import format_numeric_id
from common.enums import EventType

from client.service.connection_service import ConnectionService

logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """
    Main window controller focused on UI coordination.

    Responsibilities:
    - Handle UI events and user interactions
    - Subscribe to CallbackManager for service updates
    - Coordinate between UI and services
    - Manage UI state changes
    - Show dialogs and messages
    """

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

        self.host_pass: str = ""  # Store host password for connection requests

        # Connect internal signals to UI methods
        self.update_status.connect(self._update_status_ui)
        self.update_id_display.connect(self._update_id_display_ui)
        self.show_connection_request.connect(self._show_connection_request_dialog)
        self.enable_tabs.connect(self._enable_tabs_ui)
        self.show_notification.connect(self._show_notification_dialog)
        self.create_remote_widget.connect(self._create_remote_desktop_widget)

    def start(self):
        """Start the controller and subscribe to events"""
        if self._running:
            return

        self._running = True

        # Register callbacks
        callback_manager.register_callback(
            EventType.UI_UPDATE_STATUS.name, self._on_ui_update_status
        )
        callback_manager.register_callback(
            EventType.UI_SHOW_NOTIFICATION_SUGGESTION.name,
            self._on_ui_show_notification_suggestion,
        )
        callback_manager.register_callback(
            EventType.UI_SHOW_CLIENT_ID.name, self._on_client_id_received
        )
        callback_manager.register_callback(
            EventType.GET_HOST_PASSWORD_FROM_UI.name, self._on_request_host_password
        )
        callback_manager.register_callback(
            EventType.NETWORK_CONNECTED.name, self._on_connection_established
        )
        callback_manager.register_callback(
            EventType.NETWORK_CONNECTION_FAILED.name, self._on_connection_failed
        )
        callback_manager.register_callback(
            EventType.NETWORK_DISCONNECTED.name, self._on_connection_lost
        )
        callback_manager.register_callback(
            EventType.UI_SHOW_NOTIFICATION.name, self._on_ui_show_notification
        )
        callback_manager.register_callback(
            EventType.CONNECTED_TO_HOST.name, self._on_connected_to_host
        )
        callback_manager.register_callback(
            EventType.DISCONNECTED_WITH_HOST.name, self._on_disconnected_with_host
        )

        logger.info("MainWindowController started")

    def stop(self):
        """Stop the controller"""
        if not self._running:
            return

        self._running = False
        logger.info("MainWindowController stopped")

    # ====== USER ACTIONS ======

    def connect_to_server(self):
        """Handle connect to server button click"""
        success = ConnectionService.connect_to_server()
        if not success:
            self.update_status.emit("Failed to connect to server", "error")

    def _on_client_id_received(self, data):
        """Handle client ID received from server"""
        if isinstance(data, dict):
            client_id = data.get("client_id")
            if client_id:
                self.update_id_display.emit(format_numeric_id(client_id))
                self.enable_tabs.emit(True)
            else:
                logger.error("No client_id found in data: %s", data)
        else:
            logger.error("Expected dict but got: %s", type(data))

    def connect_to_partner(self, host_id: str, host_pass: str):
        """Handle connect to partner request"""
        # Validation
        if not host_id:
            QMessageBox.warning(self.main_window, "Input Error", "Please enter Host ID")
            return

        if len(host_id) != 9 or not host_id.isdigit():
            QMessageBox.warning(
                self.main_window, "Invalid ID", "Host ID must be exactly 9 digits"
            )
            return

        if not host_pass:
            QMessageBox.warning(
                self.main_window, "Input Error", "Please enter Host Password"
            )
            return

        # Update UI state
        if hasattr(self.main_window, "connect_btn"):
            self.main_window.connect_btn.setEnabled(False)
            self.main_window.connect_btn.setText("🔄 Connecting...")

        # Send connection request using ConnectionService
        success = ConnectionService.send_connection_request(host_id)
        if not success:
            self.reset_connect_button()
            QMessageBox.critical(
                self.main_window,
                "Connection Error",
                "Failed to send connection request",
            )

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
        auth_service = get_auth_service()
        if auth_service:
            new_password = auth_service.generate_new_password()

            # Update UI
            if hasattr(self.main_window, "password_display"):
                self.main_window.password_display.setText(new_password)

            self.update_status.emit("Password refreshed", "info")
            logger.info("Password refreshed")

    # ====== HOST ACTIONS ======

    def accept_connection_request(self, controller_id: str, host_id: str):
        """Accept incoming connection request"""
        # Publish acceptance event

    def reject_connection_request(self, controller_id: str, host_id: str):
        """Reject incoming connection request"""
        # Trigger rejection callback
        callback_manager.trigger_callbacks(EventType.REJECT_CONNECTION.name, {})

    # ====== CLIENT ACTIONS ======

    # ====== EVENT HANDLERS ======

    def _on_connection_established(self, data):
        """Handle connection established"""
        self.update_status.emit("Connected to server", "success")

    def _on_connection_failed(self, data):
        """Handle connection failed"""
        self.update_status.emit("Failed to connect to server", "error")
        self._show_connection_error()

    def _on_connection_lost(self, data):
        """Handle connection lost"""
        self.update_status.emit("Connection lost", "warning")
        self.reset_connect_button()

    def _on_ui_update_status(self, data):
        """Handle UI status update requests"""
        if isinstance(data, dict):
            message = data.get("message", "")
            status_type = data.get("type", "info")
            self.update_status.emit(message, status_type)

    def _on_ui_show_notification_suggestion(self, data):
        """Handle UI notification display requests"""
        if isinstance(data, dict):
            controller_id = str(data.get("controller_id", ""))
            host_id = str(data.get("host_id", ""))
            formatted_id = data.get("formatted_controller_id", controller_id)
            self.show_connection_request.emit(controller_id, host_id, formatted_id)

    def _on_ui_show_notification(self, data):
        """Handle UI notification display requests"""
        if isinstance(data, dict):
            message = data.get("message", "Notification")
            self.show_notification.emit(message, data.get("type", "info"))

    def _on_request_host_password(self, data):
        """Handle request for host password from ConnectionService"""
        if isinstance(data, dict):
            controller_id = data.get("controller_id")
            host_id = data.get("host_id")

            # Get password from UI input
            if hasattr(self.main_window, "host_pass_input"):
                password = self.main_window.host_pass_input.text().strip()

                # Send password back to ConnectionService
                callback_manager.trigger_callbacks(
                    EventType.UI_SEND_HOST_PASSWORD.name,
                    {
                        "controller_id": controller_id,
                        "host_id": host_id,
                        "password": password,
                    },
                )
            else:
                logger.error("No host_pass_input found in main_window")

    def _on_session_start(self, data):
        """Handle session start"""
        # Assume controller role if we have session data
        self._create_remote_desktop_widget()
        self.update_status.emit("✅ Connected - Remote desktop active", "success")

    def _on_session_end(self, data):
        """Handle session end"""
        self._close_remote_desktop()
        self.reset_connect_button()
        self.update_status.emit("Session ended", "info")

    def _on_ui_show_message(self, data):
        """Handle UI message display requests"""
        if isinstance(data, dict):
            message_type = data.get("type")

            if message_type == "connection_request":
                controller_id = str(data.get("controller_id", ""))
                host_id = str(data.get("host_id", ""))
                formatted_id = data.get("formatted_controller_id", controller_id)
                self.show_connection_request.emit(controller_id, host_id, formatted_id)

    def _on_connected_to_host(self, data):
        """Handle successful connection to host - show remote desktop"""
        logger.info("Connected to host successfully, creating remote desktop widget")
        # Use signal to create widget in main thread
        self.create_remote_widget.emit()
        self.update_status.emit("✅ Connected - Remote desktop active", "success")

    def _on_disconnected_with_host(self, data):
        """Handle disconnection from host - reset UI"""
        logger.info("Disconnected from host, resetting UI")
        self._close_remote_desktop()
        self.reset_connect_button()
        self.update_status.emit("Disconnected from host", "warning")

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
            ConnectionService._accept_connection_request(controller_id, host_id)
        else:
            ConnectionService._reject_connection_request(controller_id, host_id)

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

            # Get socket client from ConnectionService
            socket_client = ConnectionService._socket_client

            if not socket_client:
                logger.error("No socket client available for remote widget")
                self.reset_connect_button()
                return

            # Create remote widget as a standalone window (no parent)
            self.main_window.remote_widget = RemoteWidget(socket_client, None)

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
