import logging
from PyQt5.QtCore import QObject, pyqtSignal
from common.packets import VideoStreamPacket, KeyboardPacket, MousePacket

logger = logging.getLogger(__name__)


class RemoteWidgetController(QObject):
    """
    Controller for RemoteWidget - handles communication and events for a specific session
    """

    # Signals for UI updates
    update_status = pyqtSignal(str)  # status message
    show_error = pyqtSignal(str)  # error message

    def __init__(self, remote_widget, session_id: str):
        super().__init__()
        self.remote_widget = remote_widget
        self.session_id = session_id
        self._running = False

        # Connect signals
        self.update_status.connect(self._update_status_ui)
        self.show_error.connect(self._show_error_ui)

        # Connect widget signals
        self.remote_widget.disconnect_requested.connect(self.handle_disconnect_request)

        logger.info(f"RemoteWidgetController initialized for session: {session_id}")

    def handle_video_stream_packet(self, packet: VideoStreamPacket):
        """Handle incoming video stream packet"""
        try:
            self.remote_widget.handle_video_stream_packet(packet)
            logger.debug(f"Video packet processed for session {self.session_id}")
        except Exception as e:
            logger.error(
                f"Error handling video packet for session {self.session_id}: {e}"
            )
            self.show_error.emit(f"Video processing error: {str(e)}")

    def send_keyboard_event(self, event_data):
        """Send keyboard event to the remote host"""
        try:
            # Create keyboard packet and send
            from client.handlers.controller_handler import ControllerHandler

            ControllerHandler.send_keyboard_event(self.session_id, event_data)
        except Exception as e:
            logger.error(f"Error sending keyboard event: {e}")

    def send_mouse_event(self, event_data):
        """Send mouse event to the remote host"""
        try:
            # Create mouse packet and send
            from client.handlers.controller_handler import ControllerHandler

            ControllerHandler.send_mouse_event(self.session_id, event_data)
        except Exception as e:
            logger.error(f"Error sending mouse event: {e}")

    def handle_disconnect_request(self, session_id: str):
        """Handle disconnect request from widget"""
        if session_id == self.session_id:
            logger.info(f"Disconnect requested for session: {session_id}")
            self.disconnect_session()

    def disconnect_session(self):
        """Disconnect this session"""
        try:
            from client.handlers.controller_handler import ControllerHandler

            ControllerHandler.disconnect_session(self.session_id)

            # Close the widget
            if self.remote_widget:
                self.remote_widget.close()

            self.cleanup()
        except Exception as e:
            logger.error(f"Error disconnecting session {self.session_id}: {e}")

    def start(self):
        """Start the controller"""
        if self._running:
            return
        self._running = True
        logger.info(f"RemoteWidgetController started for session: {self.session_id}")

    def stop(self):
        """Stop the controller"""
        if not self._running:
            return
        self._running = False
        logger.info(f"RemoteWidgetController stopped for session: {self.session_id}")

    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop()

            # Unregister from packet handler
            from client.handlers.controller_handler import ControllerHandler

            ControllerHandler.unregister_session_handler(self.session_id)

            logger.info(
                f"RemoteWidgetController cleanup completed for session: {self.session_id}"
            )
        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}")

    # UI update slots
    def _update_status_ui(self, message: str):
        """Update status in the widget"""
        if hasattr(self.remote_widget, "status_label"):
            self.remote_widget.status_label.setText(message)

    def _show_error_ui(self, message: str):
        """Show error in the widget"""
        if self.remote_widget:
            self.remote_widget.show_error(message)
