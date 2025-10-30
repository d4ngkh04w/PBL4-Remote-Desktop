import logging

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap

from client.services.keyboard_listener_service import KeyboardListenerService

logger = logging.getLogger(__name__)


class RemoteWidgetController(QObject):
    """Controller cho RemoteWidget - xử lý logic, giao tiếp và giải mã video."""

    # --- Signals gửi đi cho View (RemoteWidget) ---
    frame_decoded = pyqtSignal(QPixmap)
    error_occurred = pyqtSignal(str)
    disconnected = pyqtSignal()
    toggle_fullscreen = pyqtSignal()

    def __init__(self, remote_widget, session_id: str):
        super().__init__()
        self.remote_widget = remote_widget
        self.session_id = session_id

        self.full_screen_pixmap: QPixmap | None = None

        self._running = False
        self._cleanup_done = False

        self._connect_signals()

        logger.info("RemoteWidgetController initialized")
        self.start()

    def _connect_signals(self):
        """Kết nối signals từ View đến slots của Controller và ngược lại."""
        # Controller -> View
        self.frame_decoded.connect(self.remote_widget.update_frame)
        self.error_occurred.connect(self.remote_widget.show_error)
        self.toggle_fullscreen.connect(self.remote_widget.toggle_fullscreen_ui)

        # View -> Controller
        self.remote_widget.disconnect_requested.connect(self.handle_disconnect_request)
        self.remote_widget.fullscreen_requested.connect(self.toggle_fullscreen.emit)
        self.remote_widget.widget_focused.connect(self.on_widget_focused)
        self.remote_widget.widget_unfocused.connect(self.on_widget_unfocused)
        self.remote_widget.key_event_occurred.connect(self.on_key_event)

    def handle_video_config_received(
        self, width: int, height: int, fps: int, codec: str
    ):
        """Xử lý thông tin config video từ ReceiveHandler."""
        try:
            logger.debug(
                f"Received config for session {self.session_id}: "
                f"{width}x{height}@{fps}fps"
            )
        except Exception as e:
            logger.error(f"Error handling config: {e}", exc_info=True)
            self.error_occurred.emit(f"Config error: {str(e)}")

    def handle_decoded_frame(self, pixmap: QPixmap):
        """Xử lý frame đã được decode từ ReceiveHandler."""
        try:
            self.full_screen_pixmap = pixmap
            # Gửi trực tiếp pixmap gốc, QLabel với ScaledContents sẽ tự động scale
            self.frame_decoded.emit(pixmap)

        except Exception as e:
            logger.error(f"Error handling decoded frame: {e}", exc_info=True)
            self.error_occurred.emit(f"Display error: {str(e)}")

    def handle_decode_error(self, error_message: str):
        """Xử lý lỗi decode từ ReceiveHandler."""
        logger.error(f"Decode error for session {self.session_id}: {error_message}")
        self.error_occurred.emit(error_message)

    @pyqtSlot(str)
    def handle_disconnect_request(self, session_id: str):
        """Xử lý yêu cầu ngắt kết nối từ widget."""
        if session_id == self.session_id and not self._cleanup_done:
            from client.managers.session_manager import SessionManager

            SessionManager.remove_widget_session(self.session_id)
            self.cleanup()

    @pyqtSlot()
    def on_widget_focused(self):
        """Xử lý khi widget được focus - bắt đầu lắng nghe bàn phím."""
        KeyboardListenerService.start_listening(self.session_id)
        logger.debug(f"Started keyboard listening for session: {self.session_id}")

    @pyqtSlot()
    def on_widget_unfocused(self):
        """Xử lý khi widget mất focus - dừng lắng nghe bàn phím."""
        KeyboardListenerService.stop_listening(self.session_id)
        logger.debug(f"Stopped keyboard listening for session: {self.session_id}")

    @pyqtSlot(object, str)
    def on_key_event(self, event, event_type: str):
        """Xử lý sự kiện bàn phím từ widget."""
        KeyboardListenerService.handle_key_event(event, event_type, self.session_id)

    def start(self):
        if self._running:
            return
        self._running = True
        # Keyboard listener sẽ được start khi widget focus
        logger.debug(f"RemoteWidgetController started for session: {self.session_id}")

    def stop(self):
        if not self._running:
            return
        self._running = False

        logger.info(f"RemoteWidgetController stopped for session: {self.session_id}")

    def cleanup(self):
        """Dọn dẹp tài nguyên của controller."""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        try:
            self.stop()
            logger.info(f"RemoteWidgetController cleanup completed: {self.session_id}")
        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}", exc_info=True)
