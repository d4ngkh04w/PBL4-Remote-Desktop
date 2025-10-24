# remote_widget.py
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from client.controllers.remote_widget_controller import RemoteWidgetController

logger = logging.getLogger(__name__)


class RemoteWidget(QWidget):
    # --- Signals gửi đi cho Controller ---
    disconnect_requested = pyqtSignal(str)  # Yêu cầu ngắt kết nối
    fit_to_screen_requested = pyqtSignal()  # Yêu cầu fit to screen
    actual_size_requested = pyqtSignal()  # Yêu cầu kích thước thật
    fullscreen_requested = pyqtSignal()  # Yêu cầu fullscreen
    widget_focused = pyqtSignal()  # Widget được focus
    widget_unfocused = pyqtSignal()  # Widget mất focus
    key_event_occurred = pyqtSignal(object, str)  # Sự kiện phím (event, event_type)

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.controller = RemoteWidgetController(self, self.session_id)
        self._cleanup_done = False

        # Cho phép widget nhận focus để lắng nghe sự kiện bàn phím
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.create_control_toolbar(main_layout)
        self.create_screen_area(main_layout)
        self.create_status_area(main_layout)
        self.setWindowTitle(f"Remote Desktop - Session: {self.session_id}")

    def create_control_toolbar(self, parent_layout):
        toolbar_group = QGroupBox("Remote Control")
        toolbar_layout = QHBoxLayout(toolbar_group)

        self.status_label = QLabel("🔗 Connecting...")
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addStretch()

        self.fit_screen_btn = QPushButton("🔍 Fit to Window")
        # Kết nối sự kiện click tới signal
        self.fit_screen_btn.clicked.connect(self.fit_to_screen_requested.emit)
        toolbar_layout.addWidget(self.fit_screen_btn)

        self.actual_size_btn = QPushButton("📐 Actual Size")
        self.actual_size_btn.clicked.connect(self.actual_size_requested.emit)
        toolbar_layout.addWidget(self.actual_size_btn)

        self.fullscreen_btn = QPushButton("🔲 Fullscreen")
        self.fullscreen_btn.clicked.connect(self.fullscreen_requested.emit)
        toolbar_layout.addWidget(self.fullscreen_btn)

        self.disconnect_btn = QPushButton("❌ Disconnect")
        self.disconnect_btn.clicked.connect(
            lambda: self.disconnect_requested.emit(self.session_id)
        )
        toolbar_layout.addWidget(self.disconnect_btn)

        parent_layout.addWidget(toolbar_group)

    def create_screen_area(self, parent_layout):
        screen_group = QGroupBox("Remote Screen")
        screen_layout = QVBoxLayout(screen_group)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("🖥️ Waiting for remote screen...")
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Cho phép image_label nhận focus và click events
        self.image_label.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.image_label.mousePressEvent = self._image_label_mouse_press
        
        self.scroll_area.setWidget(self.image_label)
        screen_layout.addWidget(self.scroll_area)
        parent_layout.addWidget(screen_group)

    def create_status_area(self, parent_layout):
        status_layout = QHBoxLayout()
        self.info_label = QLabel("Resolution: N/A")
        status_layout.addWidget(self.info_label)
        status_layout.addStretch()
        parent_layout.addLayout(status_layout)

    # --- Slots để nhận dữ liệu từ Controller ---

    @pyqtSlot(QPixmap)
    def update_frame(self, pixmap: QPixmap):
        """Nhận và hiển thị frame đã được giải mã từ controller."""
        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())

    @pyqtSlot(str)
    def update_status_text(self, text: str):
        """Cập nhật text của status label."""
        self.status_label.setText(text)

    @pyqtSlot(str)
    def update_info_text(self, text: str):
        """Cập nhật text của info label."""
        self.info_label.setText(text)

    @pyqtSlot(str)
    def show_error(self, message: str):
        """Hiển thị thông báo lỗi."""
        self.image_label.clear()
        self.image_label.setText(f"❌ Error: {message}")
        self.status_label.setText("⚠️ Connection Error")

    @pyqtSlot()
    def toggle_fullscreen_ui(self):
        """Chuyển đổi chế độ toàn màn hình."""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("🔲 Fullscreen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("🔳 Exit Fullscreen")

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
        # Thông báo cho controller để fit lại ảnh nếu cần
        self.fit_to_screen_requested.emit()

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ."""
        if not self._cleanup_done:
            # Gửi end session trước khi đóng widget
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
