import logging

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from client.controllers.remote_widget_controller import RemoteWidgetController

logger = logging.getLogger(__name__)


class RemoteWidget(QWidget):
    # --- Signals gửi đi cho Controller ---
    disconnect_requested = pyqtSignal(str)  # Yêu cầu ngắt kết nối
    fullscreen_requested = pyqtSignal()  # Yêu cầu fullscreen
    widget_focused = pyqtSignal()  # Widget được focus
    widget_unfocused = pyqtSignal()  # Widget mất focus
    key_event_occurred = pyqtSignal(object, str)  # Sự kiện phím (event, event_type)

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.controller = RemoteWidgetController(self, self.session_id)
        self._cleanup_done = False
        self._current_pixmap = None  # Lưu pixmap gốc để re-scale khi resize

        # Cho phép widget nhận focus để lắng nghe sự kiện bàn phím
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.create_screen_area(main_layout)
        self.setWindowTitle(f"PBL4 Remote Desktop")

        # Tự động maximize window khi khởi tạo
        self.showMaximized()

    def create_screen_area(self, parent_layout):
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("🖥️ Waiting for remote screen...")
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")

        # Cho phép image_label nhận focus và click events
        self.image_label.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.image_label.mousePressEvent = self._image_label_mouse_press

        parent_layout.addWidget(self.image_label)

    # --- Slots để nhận dữ liệu từ Controller ---

    @pyqtSlot(QPixmap)
    def update_frame(self, pixmap: QPixmap):
        """Nhận và hiển thị frame đã được giải mã từ controller."""
        # Lưu pixmap gốc
        self._current_pixmap = pixmap
        # Scale và hiển thị
        self._scale_and_display()

    @pyqtSlot(str)
    def show_error(self, message: str):
        """Hiển thị thông báo lỗi."""
        self.image_label.clear()
        self.image_label.setText(f"❌ Error: {message}")

    def _scale_and_display(self):
        """Scale pixmap gốc và hiển thị vừa với widget."""
        if not self._current_pixmap:
            return

        # Scale pixmap để vừa với label nhưng giữ aspect ratio
        scaled_pixmap = self._current_pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)

    @pyqtSlot()
    def toggle_fullscreen_ui(self):
        """Chuyển đổi chế độ toàn màn hình."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # --- Xử lý sự kiện UI ---

    def keyPressEvent(self, event):
        """Xử lý phím tắt và gửi sự kiện cho controller."""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen_ui()
            else:
                self.close()
        elif event.key() == Qt.Key.Key_F11:
            self.fullscreen_requested.emit()
        else:
            # Gửi sự kiện phím cho controller xử lý
            self.key_event_occurred.emit(event, "press")
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Xử lý sự kiện nhả phím."""
        # Gửi sự kiện nhả phím cho controller xử lý
        self.key_event_occurred.emit(event, "release")
        super().keyReleaseEvent(event)

    def focusInEvent(self, event):
        """Widget được focus - bắt đầu lắng nghe bàn phím."""
        super().focusInEvent(event)
        self.widget_focused.emit()
        logger.debug(f"RemoteWidget focused for session: {self.session_id}")

    def focusOutEvent(self, event):
        """Widget mất focus - dừng lắng nghe bàn phím."""
        super().focusOutEvent(event)
        self.widget_unfocused.emit()
        logger.debug(f"RemoteWidget unfocused for session: {self.session_id}")

    def mousePressEvent(self, event):
        """Đảm bảo widget nhận focus khi click."""
        self.setFocus()
        super().mousePressEvent(event)

    def _image_label_mouse_press(self, event):
        """Xử lý click vào image label để focus widget."""
        self.setFocus()
        # Gọi mousePressEvent gốc của QLabel nếu cần
        QLabel.mousePressEvent(self.image_label, event)

    def resizeEvent(self, event):
        """Xử lý sự kiện thay đổi kích thước cửa sổ."""
        super().resizeEvent(event)
        # Re-scale hình ảnh khi resize window
        self._scale_and_display()

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ."""
        if not self._cleanup_done:
            # Chỉ gửi disconnect request nếu chưa được cleanup từ bên ngoài
            self.disconnect_requested.emit(self.session_id)
            self.cleanup()
        event.accept()

    def cleanup(self):
        """Dọn dẹp tài nguyên."""
        if self._cleanup_done:
            return
        self._cleanup_done = True
        try:
            if self.controller:
                self.controller.cleanup()
            self.image_label.clear()
            logger.info(
                f"RemoteWidget cleanup completed for session: {self.session_id}"
            )
        except Exception as e:
            logger.error(f"Error during RemoteWidget cleanup: {e}", exc_info=True)
