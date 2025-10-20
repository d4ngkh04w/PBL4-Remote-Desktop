# remote_widget_controller.py
import logging

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QPixmap

logger = logging.getLogger(__name__)


class RemoteWidgetController(QObject):
    """Controller cho RemoteWidget - xử lý logic, giao tiếp và giải mã video."""

    # --- Signals gửi đi cho View (RemoteWidget) ---
    frame_decoded = pyqtSignal(QPixmap)
    status_updated = pyqtSignal(str)
    info_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    disconnected = pyqtSignal()
    toggle_fullscreen = pyqtSignal()

    def __init__(self, remote_widget, session_id: str):
        super().__init__()
        self.remote_widget = remote_widget
        self.session_id = session_id

        self.original_width = 0
        self.original_height = 0
        self.full_screen_pixmap: QPixmap | None = None
        self._is_fitting_screen = True  # Mặc định là fit to screen

        self._running = False
        self._cleanup_done = False

        self._connect_signals()

        logger.info(f"RemoteWidgetController initialized for session: {session_id}")
        self.start()

    def _connect_signals(self):
        """Kết nối signals từ View đến slots của Controller và ngược lại."""
        # Controller -> View
        self.frame_decoded.connect(self.remote_widget.update_frame)
        self.status_updated.connect(self.remote_widget.update_status_text)
        self.info_updated.connect(self.remote_widget.update_info_text)
        self.error_occurred.connect(self.remote_widget.show_error)
        self.toggle_fullscreen.connect(self.remote_widget.toggle_fullscreen_ui)

        # View -> Controller
        self.remote_widget.disconnect_requested.connect(self.handle_disconnect_request)
        self.remote_widget.fit_to_screen_requested.connect(self.fit_to_screen)
        self.remote_widget.actual_size_requested.connect(self.actual_size)
        self.remote_widget.fullscreen_requested.connect(self.toggle_fullscreen.emit)

    def handle_video_config_received(
        self, width: int, height: int, fps: int, codec: str
    ):
        """Xử lý thông tin config video từ ReceiveHandler."""
        try:
            logger.debug(
                f"Received config for session {self.session_id}: "
                f"{width}x{height}@{fps}fps"
            )
            self.original_width = width
            self.original_height = height

            info_text = (
                f"Resolution: {width}x{height} | "
                f"FPS: {fps} | Codec: {codec.upper()}"
            )
            self.info_updated.emit(info_text)
            self.status_updated.emit("🎥 Streaming")

        except Exception as e:
            logger.error(f"Error handling config: {e}", exc_info=True)
            self.error_occurred.emit(f"Config error: {str(e)}")

    def handle_decoded_frame(self, pixmap: QPixmap):
        """Xử lý frame đã được decode từ ReceiveHandler."""
        try:
            self.full_screen_pixmap = pixmap
            # Cập nhật hiển thị
            self._update_display()

        except Exception as e:
            logger.error(f"Error handling decoded frame: {e}", exc_info=True)
            self.error_occurred.emit(f"Display error: {str(e)}")

    def handle_decode_error(self, error_message: str):
        """Xử lý lỗi decode từ ReceiveHandler."""
        logger.error(f"Decode error for session {self.session_id}: {error_message}")
        self.error_occurred.emit(error_message)

    def _update_display(self):
        """Cập nhật pixmap trên UI theo chế độ hiển thị hiện tại."""
        if not self.full_screen_pixmap:
            return
        if self._is_fitting_screen:
            self.fit_to_screen()
        else:
            self.actual_size()

    @pyqtSlot()
    def fit_to_screen(self):
        """Thay đổi kích thước pixmap để vừa với cửa sổ."""
        self._is_fitting_screen = True
        if not self.full_screen_pixmap:
            return

        # Lấy kích thước của scroll_area từ widget
        scroll_area_size = self.remote_widget.scroll_area.size()
        scroll_area_size.setWidth(scroll_area_size.width() - 20)
        scroll_area_size.setHeight(scroll_area_size.height() - 20)

        scaled_pixmap = self.full_screen_pixmap.scaled(
            scroll_area_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.frame_decoded.emit(scaled_pixmap)

    @pyqtSlot()
    def actual_size(self):
        """Hiển thị pixmap với kích thước gốc."""
        self._is_fitting_screen = False
        if not self.full_screen_pixmap:
            return
        self.frame_decoded.emit(self.full_screen_pixmap)

    @pyqtSlot(str)
    def handle_disconnect_request(self, session_id: str):
        """Xử lý yêu cầu ngắt kết nối từ widget."""
        if session_id == self.session_id:
            logger.info(f"Disconnect requested for session: {session_id}")
            from client.managers.session_manager import SessionManager

            SessionManager.remove_session(self.session_id)

            from client.handlers.send_handler import SendHandler
            SendHandler.send_end_session_packet(session_id)
            self.cleanup()
            

    def start(self):
        if self._running:
            return
        self._running = True
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
