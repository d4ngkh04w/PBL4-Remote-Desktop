import logging

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QPixmap, QKeyEvent

from client.services.keyboard_listener_service import KeyboardListenerService
from client.handlers.send_handler import SendHandler
from common.enums import KeyBoardEventType, KeyBoardType

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

        self.keyboard_listener = KeyboardListenerService()
        self._keyboard_listening = False

        self._connect_signals()

        logger.info("RemoteWidgetController initialized")
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
        self.remote_widget.widget_focused.connect(self.start_keyboard_listening)
        self.remote_widget.widget_unfocused.connect(self.stop_keyboard_listening)
        self.remote_widget.key_event_occurred.connect(self.handle_key_event)

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
            from client.managers.session_manager import SessionManager
            SessionManager.remove_widget_session(self.session_id)            
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
        # Dừng lắng nghe sự kiện bàn phím khi stop
        self.keyboard_listener.stop()
        logger.info(f"RemoteWidgetController stopped for session: {self.session_id}")
    
    def start_keyboard_listening(self):
        """Bắt đầu lắng nghe bàn phím khi widget được focus."""
        if self._running and not self._keyboard_listening:
            self._keyboard_listening = True
            logger.debug(f"Keyboard listening started for session: {self.session_id}")
    
    def stop_keyboard_listening(self):
        """Dừng lắng nghe bàn phím khi widget mất focus."""
        if self._keyboard_listening:
            self._keyboard_listening = False
            logger.debug(f"Keyboard listening stopped for session: {self.session_id}")

    @pyqtSlot(object, str)
    def handle_key_event(self, qt_event: QKeyEvent, event_type: str):
        """Xử lý sự kiện phím từ widget."""
        if not self._keyboard_listening:
            return
            
        try:
            # Chuyển đổi Qt key event thành format của ứng dụng
            key_name = None
            key_vk = None
            key_type = None
            
            # Lấy thông tin từ QKeyEvent
            qt_key = qt_event.key()
            qt_text = qt_event.text()
            
            # Kiểm tra xem có phải là ký tự in được không
            if qt_text and qt_text.isprintable() and len(qt_text) == 1:
                # Phím ký tự (a, b, 1, 2, ...)
                key_type = KeyBoardType.KEYCODE
                key_vk = ord(qt_text)
                logger.debug(f"Character key: text={qt_text}, vk={key_vk}")
            else:
                # Phím đặc biệt, chuyển đổi Qt key sang tên phím
                key_type = KeyBoardType.KEY
                key_name = self._qt_key_to_name(qt_key)
                logger.debug(f"Special key: qt_key={qt_key}, name={key_name}")
            
            # Chuyển đổi event type
            if event_type == "press":
                event_type_enum = KeyBoardEventType.PRESS
            elif event_type == "release":
                event_type_enum = KeyBoardEventType.RELEASE
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return
            
            # Gửi gói tin bàn phím
            SendHandler.send_keyboard_packet(
                session_id=self.session_id,
                event_type=event_type_enum,
                key_type=key_type,
                key_name=key_name,
                key_vk=key_vk,
            )
            
        except Exception as e:
            logger.error(f"Error handling key event: {e}", exc_info=True)

    def _qt_key_to_name(self, qt_key):
        """Chuyển đổi Qt key code sang tên phím."""
        # Mapping các phím đặc biệt từ Qt sang tên phím chuẩn
        key_mapping = {
            Qt.Key.Key_Alt: "alt",
            Qt.Key.Key_AltGr: "alt_gr", 
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_CapsLock: "caps_lock",
            Qt.Key.Key_Control: "ctrl",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_F1: "f1",
            Qt.Key.Key_F2: "f2",
            Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5",
            Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7",
            Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10",
            Qt.Key.Key_F11: "f11",
            Qt.Key.Key_F12: "f12",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_PageDown: "page_down",
            Qt.Key.Key_PageUp: "page_up",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Shift: "shift",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Menu: "menu",
            Qt.Key.Key_NumLock: "num_lock",
            Qt.Key.Key_Pause: "pause",
            Qt.Key.Key_Print: "print_screen",
            Qt.Key.Key_ScrollLock: "scroll_lock",
        }
        
        return key_mapping.get(qt_key, f"unknown_{qt_key}")

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
