import logging
import time

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
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
    cursor_info_received = pyqtSignal(
        str, tuple, bool
    )  # cursor_type, position, visible

    def __init__(self, remote_widget, session_id: str):
        super().__init__()
        self.remote_widget = remote_widget
        self.session_id = session_id

        self.full_screen_pixmap: QPixmap | None = None

        self.__running = False
        self.__cleanup_done = False

        # Throttling cho mouse move events
        self.__last_mouse_position = None
        self.__last_mouse_send_time = 0
        self.__mouse_move_interval = 0.016  # ~60 FPS, 16ms
        self.__pending_mouse_event = None

        # Timer để gửi mouse move event sau một khoảng thời gian
        self.__mouse_timer = QTimer()
        self.__mouse_timer.timeout.connect(self.__send_pending_mouse_event)
        self.__mouse_timer.setInterval(int(self.__mouse_move_interval * 1000))

        self.__connect_signals()

        logger.info("RemoteWidgetController initialized")
        self.start()

    def __connect_signals(self):
        """Kết nối signals từ View đến slots của Controller và ngược lại."""
        # Controller -> View
        self.frame_decoded.connect(self.remote_widget.update_frame)
        self.error_occurred.connect(self.remote_widget.show_error)
        self.toggle_fullscreen.connect(self.remote_widget.toggle_fullscreen_ui)
        self.cursor_info_received.connect(self.remote_widget.update_cursor_overlay)

        # View -> Controller
        self.remote_widget.disconnect_requested.connect(self.handle_disconnect_request)
        self.remote_widget.fullscreen_requested.connect(self.toggle_fullscreen.emit)
        self.remote_widget.widget_focused.connect(self.on_widget_focused)
        self.remote_widget.widget_unfocused.connect(self.on_widget_unfocused)
        self.remote_widget.key_event_occurred.connect(self.on_key_event)
        self.remote_widget.mouse_event_occurred.connect(self.on_mouse_event)

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

    def handle_cursor_info(
        self, cursor_type: str, position: tuple[int, int], visible: bool
    ):
        """Xử lý thông tin cursor nhận được từ server."""
        try:
            self.cursor_info_received.emit(cursor_type, position, visible)
        except Exception as e:
            logger.error(f"Error handling cursor info: {e}", exc_info=True)

    @pyqtSlot(str)
    def handle_disconnect_request(self, session_id: str):
        """Xử lý yêu cầu ngắt kết nối từ widget."""
        if session_id == self.session_id and not self.__cleanup_done:
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

    @pyqtSlot(str, tuple, str, tuple)
    def on_mouse_event(
        self, event_type: str, position: tuple, button: str, scroll_delta: tuple
    ):
        """Xử lý sự kiện chuột từ widget."""
        from client.services.sender_service import SenderService
        from common.packets import MousePacket
        from common.enums import MouseEventType, MouseButton

        # Chuyển đổi event_type string sang enum
        try:
            mouse_event_type = MouseEventType[event_type]
        except KeyError:
            logger.error(f"Invalid mouse event type: {event_type}")
            return

        # Chuyển đổi button string sang enum
        try:
            mouse_button = MouseButton[button]
        except KeyError:
            logger.error(f"Invalid mouse button: {button}")
            return

        # Tối ưu cho mouse move events với throttling
        if mouse_event_type == MouseEventType.MOVE:
            current_time = time.time()

            # Bỏ qua nếu vị trí không thay đổi
            if position == self.__last_mouse_position:
                return

            # Throttle: chỉ gửi sau một khoảng thời gian
            time_since_last_send = current_time - self.__last_mouse_send_time

            if time_since_last_send >= self.__mouse_move_interval:
                # Gửi ngay lập tức
                packet = MousePacket(
                    event_type=mouse_event_type,
                    position=position,
                    button=mouse_button,
                    scroll_delta=scroll_delta,
                    session_id=self.session_id,
                )
                SenderService.send_packet(packet)
                self.__last_mouse_position = position
                self.__last_mouse_send_time = current_time

                # Clear pending event nếu có
                self.__pending_mouse_event = None
                if self.__mouse_timer.isActive():
                    self.__mouse_timer.stop()
            else:
                # Lưu lại để gửi sau
                self.__pending_mouse_event = (
                    mouse_event_type,
                    position,
                    mouse_button,
                    scroll_delta,
                )

                # Start timer nếu chưa chạy
                if not self.__mouse_timer.isActive():
                    self.__mouse_timer.start()
        else:
            # Click, release, scroll - gửi ngay lập tức
            packet = MousePacket(
                event_type=mouse_event_type,
                position=position,
                button=mouse_button,
                scroll_delta=scroll_delta,
                session_id=self.session_id,
            )
            SenderService.send_packet(packet)

            # Log chỉ cho non-move events để tránh spam
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Mouse {event_type} - Pos: {position}, Button: {button}, Scroll: {scroll_delta}"
                )

    def __send_pending_mouse_event(self):
        """Gửi mouse move event đang chờ."""
        if self.__pending_mouse_event:
            from client.services.sender_service import SenderService
            from common.packets import MousePacket

            event_type, position, button, scroll_delta = self.__pending_mouse_event

            packet = MousePacket(
                event_type=event_type,
                position=position,
                button=button,
                scroll_delta=scroll_delta,
                session_id=self.session_id,
            )
            SenderService.send_packet(packet)

            self.__last_mouse_position = position
            self.__last_mouse_send_time = time.time()
            self.__pending_mouse_event = None

        self.__mouse_timer.stop()

    def start(self):
        if self.__running:
            return
        self.__running = True
        # Keyboard listener sẽ được start khi widget focus
        logger.debug(f"RemoteWidgetController started for session: {self.session_id}")

    def stop(self):
        if not self.__running:
            return
        self.__running = False

        logger.info(f"RemoteWidgetController stopped for session: {self.session_id}")

    def cleanup(self):
        """Dọn dẹp tài nguyên của controller."""
        if self.__cleanup_done:
            return
        self.__cleanup_done = True

        try:
            # Stop mouse timer
            if self.__mouse_timer.isActive():
                self.__mouse_timer.stop()

            self.stop()
            logger.info(f"RemoteWidgetController cleanup completed: {self.session_id}")
        except Exception as e:
            logger.error(f"Error during controller cleanup: {e}", exc_info=True)
