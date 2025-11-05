import logging

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QPainter, QPen
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QPoint

from client.controllers.remote_widget_controller import RemoteWidgetController

logger = logging.getLogger(__name__)


class RemoteWidget(QWidget):
    # --- Signals gửi đi cho Controller ---
    disconnect_requested = pyqtSignal(str)  # Yêu cầu ngắt kết nối
    fullscreen_requested = pyqtSignal()  # Yêu cầu fullscreen
    widget_focused = pyqtSignal()  # Widget được focus
    widget_unfocused = pyqtSignal()  # Widget mất focus
    key_event_occurred = pyqtSignal(object, str)  # Sự kiện phím (event, event_type)
    mouse_event_occurred = pyqtSignal(
        str, tuple, str, tuple
    )  # Sự kiện chuột (event_type, position, button, scroll_delta)

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.controller = RemoteWidgetController(self, self.session_id)
        self.__cleanup_done = False
        self.__current_pixmap = None  # Lưu pixmap gốc để re-scale khi resize
        self.__last_mouse_pos = (
            None  # Lưu vị trí chuột cuối cùng để tránh gửi duplicate
        )

        # Thông tin cursor từ server
        self.__cursor_type = "normal"
        self.__cursor_position = None  # (x, y) tương đối trên pixmap gốc
        self.__cursor_visible = True
        self.__cursor_pixmaps = {}  # Cache cursor images

        # Cho phép widget nhận focus để lắng nghe sự kiện bàn phím và chuột
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)  # Bật theo dõi di chuyển chuột

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

        # Cho phép image_label nhận focus và mouse events
        self.image_label.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.image_label.setMouseTracking(True)  # Bật theo dõi di chuyển chuột

        parent_layout.addWidget(self.image_label)

    # --- Slots để nhận dữ liệu từ Controller ---

    @pyqtSlot(QPixmap)
    def update_frame(self, pixmap: QPixmap):
        """Nhận và hiển thị frame đã được giải mã từ controller."""
        # Lưu pixmap gốc
        self.__current_pixmap = pixmap
        # Scale và hiển thị
        self.__scale_and_display()

    @pyqtSlot(str, tuple, bool)
    def update_cursor_overlay(self, cursor_type: str, position: tuple, visible: bool):
        """Cập nhật thông tin cursor và vẽ lại overlay."""
        self.__cursor_type = cursor_type
        self.__cursor_position = position
        self.__cursor_visible = visible
        # Vẽ lại frame với cursor mới
        self.__scale_and_display()

    @pyqtSlot(str)
    def show_error(self, message: str):
        """Hiển thị thông báo lỗi."""
        self.image_label.clear()
        self.image_label.setText(f"❌ Error: {message}")

    def __scale_and_display(self):
        """Scale pixmap gốc và hiển thị vừa với widget, vẽ cursor overlay."""
        if not self.__current_pixmap:
            return

        # Tạo bản sao của pixmap gốc để vẽ cursor lên
        pixmap_with_cursor = self.__current_pixmap.copy()

        # Vẽ cursor nếu có thông tin
        if self.__cursor_visible and self.__cursor_position:
            self.__draw_cursor_on_pixmap(pixmap_with_cursor)

        # Scale pixmap để vừa với label nhưng giữ aspect ratio
        scaled_pixmap = pixmap_with_cursor.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)

    def __draw_cursor_on_pixmap(self, pixmap: QPixmap):
        """Vẽ cursor lên pixmap."""
        if not self.__cursor_position:
            return

        cursor_x, cursor_y = self.__cursor_position

        # Load cursor image
        cursor_pixmap = self.__load_cursor_pixmap(self.__cursor_type)

        if cursor_pixmap:
            # Vẽ cursor image lên pixmap
            painter = QPainter(pixmap)
            painter.drawPixmap(cursor_x, cursor_y, cursor_pixmap)
            painter.end()
        else:
            # Fallback: vẽ hình tròn đỏ nếu không load được cursor
            painter = QPainter(pixmap)
            pen = QPen(Qt.GlobalColor.red, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.GlobalColor.red)
            radius = 8
            painter.drawEllipse(QPoint(cursor_x, cursor_y), radius, radius)
            painter.end()

    def __load_cursor_pixmap(self, cursor_type: str) -> QPixmap | None:
        """Load cursor pixmap từ file."""
        # Kiểm tra cache
        if cursor_type in self.__cursor_pixmaps:
            return self.__cursor_pixmaps[cursor_type]

        try:
            from common.utils import get_cursor_image_path, load_cursor_image

            cursor_path = get_cursor_image_path(cursor_type)
            if not cursor_path:
                return None

            cursor_img = load_cursor_image(cursor_path)
            if not cursor_img:
                return None

            # Convert PIL Image to QPixmap
            import io

            buffer = io.BytesIO()
            cursor_img.save(buffer, format="PNG")
            buffer.seek(0)
            cursor_pixmap = QPixmap()
            cursor_pixmap.loadFromData(buffer.read())

            # Resize cursor nếu quá lớn
            if cursor_pixmap.width() > 48 or cursor_pixmap.height() > 48:
                cursor_pixmap = cursor_pixmap.scaled(
                    48,
                    48,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            # Cache lại
            self.__cursor_pixmaps[cursor_type] = cursor_pixmap
            return cursor_pixmap

        except Exception as e:
            logger.debug(f"Error loading cursor pixmap for {cursor_type}: {e}")
            return None

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

    def leaveEvent(self, event):
        """Xử lý khi chuột rời khỏi widget - hiển thị lại con chuột."""
        super().leaveEvent(event)
        self.unsetCursor()
        self.__last_mouse_pos = None
        # Bỏ debug log để giảm overhead

    def mousePressEvent(self, event):
        """Xử lý sự kiện nhấn chuột."""
        self.setFocus()
        scaled_pos = self.__get_scaled_mouse_position(event.pos())
        if scaled_pos:
            button = self.__map_qt_button(event.button())
            self.mouse_event_occurred.emit("PRESS", scaled_pos, button, (0, 0))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Xử lý sự kiện nhả chuột."""
        scaled_pos = self.__get_scaled_mouse_position(event.pos())
        if scaled_pos:
            button = self.__map_qt_button(event.button())
            self.mouse_event_occurred.emit("RELEASE", scaled_pos, button, (0, 0))
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Xử lý sự kiện di chuyển chuột."""
        scaled_pos = self.__get_scaled_mouse_position(event.pos())

        # Bỏ qua nếu vị trí không thay đổi
        if scaled_pos == self.__last_mouse_pos:
            return

        if scaled_pos:
            # Ẩn con chuột khi di chuyển trên vùng màn hình share
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.mouse_event_occurred.emit("MOVE", scaled_pos, "UNKNOWN", (0, 0))
            self.__last_mouse_pos = scaled_pos
        else:
            # Hiển thị lại con chuột khi ra ngoài vùng màn hình share
            self.unsetCursor()
            self.__last_mouse_pos = None

        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        """Xử lý sự kiện cuộn chuột."""
        scaled_pos = self.__get_scaled_mouse_position(event.pos())
        if scaled_pos:
            # Qt5: angleDelta() trả về QPoint với x (horizontal) và y (vertical)
            delta = event.angleDelta()
            scroll_delta = (delta.x() // 120, delta.y() // 120)  # Chia 120 để chuẩn hóa
            self.mouse_event_occurred.emit(
                "SCROLL", scaled_pos, "UNKNOWN", scroll_delta
            )
        super().wheelEvent(event)

    def __get_scaled_mouse_position(self, pos):
        """Tính toán vị trí chuột theo tỉ lệ với kích thước ảnh gốc."""
        if not self.__current_pixmap:
            return None

        # Lấy kích thước của label và pixmap gốc
        label_size = self.image_label.size()
        pixmap_size = self.__current_pixmap.size()

        # Tính toán scaled size giữ aspect ratio - sử dụng FastTransformation cho tốc độ
        # Không cần scale pixmap thật, chỉ cần tính toán kích thước
        pixmap_width = pixmap_size.width()
        pixmap_height = pixmap_size.height()
        label_width = label_size.width()
        label_height = label_size.height()

        # Tính scale factor giữ aspect ratio
        scale_factor = min(label_width / pixmap_width, label_height / pixmap_height)
        scaled_width = int(pixmap_width * scale_factor)
        scaled_height = int(pixmap_height * scale_factor)

        # Tính offset để center image trong label
        offset_x = (label_width - scaled_width) // 2
        offset_y = (label_height - scaled_height) // 2

        # Chuyển đổi từ tọa độ widget sang tọa độ image_label
        label_pos = self.image_label.mapFrom(self, pos)
        x = label_pos.x() - offset_x
        y = label_pos.y() - offset_y

        # Kiểm tra xem chuột có nằm trong vùng ảnh không
        if x < 0 or y < 0 or x >= scaled_width or y >= scaled_height:
            return None

        # Tính toán tỉ lệ và chuyển đổi về tọa độ gốc
        scale_x = pixmap_width / scaled_width
        scale_y = pixmap_height / scaled_height

        original_x = int(x * scale_x)
        original_y = int(y * scale_y)

        return (original_x, original_y)

    def __map_qt_button(self, qt_button):
        """Chuyển đổi Qt button sang string button."""
        if qt_button == Qt.MouseButton.LeftButton:
            return "LEFT"
        elif qt_button == Qt.MouseButton.RightButton:
            return "RIGHT"
        elif qt_button == Qt.MouseButton.MiddleButton:
            return "MIDDLE"
        else:
            return "UNKNOWN"

    def _image_label_mouse_press(self, event):
        """Xử lý click vào image label để focus widget."""
        self.setFocus()
        # Gọi mousePressEvent gốc của QLabel nếu cần
        QLabel.mousePressEvent(self.image_label, event)

    def resizeEvent(self, event):
        """Xử lý sự kiện thay đổi kích thước cửa sổ."""
        super().resizeEvent(event)
        # Re-scale hình ảnh khi resize window
        self.__scale_and_display()

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ."""
        if not self.__cleanup_done:
            # Chỉ gửi disconnect request nếu chưa được cleanup từ bên ngoài
            self.disconnect_requested.emit(self.session_id)
            self.cleanup()
        event.accept()

    def cleanup(self):
        """Dọn dẹp tài nguyên."""
        if self.__cleanup_done:
            return
        self.__cleanup_done = True
        try:
            if self.controller:
                self.controller.cleanup()
            self.image_label.clear()
            logger.info(
                f"RemoteWidget cleanup completed for session: {self.session_id}"
            )
        except Exception as e:
            logger.error(f"Error during RemoteWidget cleanup: {e}", exc_info=True)
