import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent

from common.packets import KeyboardPacket
from common.enums import KeyBoardEventType, KeyBoardType
from client.services.sender_service import SenderService

logger = logging.getLogger(__name__)


class KeyboardListenerService:
    """
    Service lắng nghe sự kiện bàn phím từ RemoteWidget
    và chuyển đổi thành KeyboardPacket để gửi đi
    """

    # Tracking pressed modifier keys per session to handle sticky keys
    __pressed_modifiers = {}  # {session_id: set of pressed modifier names}

    # Mapping các phím đặc biệt Qt sang tên phím
    SPECIAL_KEYS = {
        Qt.Key.Key_Control: "ctrl",
        Qt.Key.Key_Shift: "shift",
        Qt.Key.Key_Alt: "alt",
        Qt.Key.Key_Meta: "meta",  # Windows key
        Qt.Key.Key_CapsLock: "caps_lock",
        Qt.Key.Key_Tab: "tab",
        Qt.Key.Key_Backspace: "backspace",
        Qt.Key.Key_Return: "enter",
        Qt.Key.Key_Enter: "enter",
        Qt.Key.Key_Escape: "esc",
        Qt.Key.Key_Space: "space",
        Qt.Key.Key_Delete: "delete",
        Qt.Key.Key_Home: "home",
        Qt.Key.Key_End: "end",
        Qt.Key.Key_PageUp: "page_up",
        Qt.Key.Key_PageDown: "page_down",
        Qt.Key.Key_Left: "left",
        Qt.Key.Key_Up: "up",
        Qt.Key.Key_Right: "right",
        Qt.Key.Key_Down: "down",
        Qt.Key.Key_Insert: "insert",
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
        Qt.Key.Key_NumLock: "num_lock",
        Qt.Key.Key_ScrollLock: "scroll_lock",
        Qt.Key.Key_Print: "print_screen",
        Qt.Key.Key_Pause: "pause",
    }

    @classmethod
    def handle_key_event(cls, event: QKeyEvent, event_type_str: str, session_id: str):
        """
        Xử lý sự kiện bàn phím từ widget
        """
        try:
            # Bỏ qua auto-repeat events để tránh gửi hàng trăm packet khi giữ phím
            if event.isAutoRepeat():
                return

            # Xác định loại sự kiện
            event_type = (
                KeyBoardEventType.PRESS
                if event_type_str == "press"
                else KeyBoardEventType.RELEASE
            )

            # Kiểm tra xem có phải tổ hợp phím không
            modifiers = event.modifiers()
            has_modifier = bool(
                modifiers & Qt.KeyboardModifier.ControlModifier
                or modifiers & Qt.KeyboardModifier.ShiftModifier
                or modifiers & Qt.KeyboardModifier.AltModifier
                or modifiers & Qt.KeyboardModifier.MetaModifier
            )

            key = event.key()

            # Xử lý tổ hợp phím
            if has_modifier and key not in [
                Qt.Key.Key_Control,
                Qt.Key.Key_Shift,
                Qt.Key.Key_Alt,
                Qt.Key.Key_Meta,
            ]:
                cls.__handle_key_combination(event, event_type, session_id)
            # Xử lý phím đặc biệt (bao gồm cả modifier keys)
            elif key in cls.SPECIAL_KEYS:
                cls.__handle_special_key(event, event_type, session_id)
            # Xử lý phím ký tự thông thường
            else:
                cls.__handle_character_key(event, event_type, session_id)

        except Exception as e:
            logger.error(f"Error handling key event: {e}", exc_info=True)

    @classmethod
    def __handle_special_key(
        cls, event: QKeyEvent, event_type: KeyBoardEventType, session_id: str
    ):
        """Xử lý phím đặc biệt (Ctrl, Shift, Alt, F1-F12, ...)"""
        key_name = cls.SPECIAL_KEYS.get(event.key())
        if key_name:
            # Track modifier key states
            if key_name in ["ctrl", "shift", "alt", "meta"]:
                if session_id not in cls.__pressed_modifiers:
                    cls.__pressed_modifiers[session_id] = set()

                if event_type == KeyBoardEventType.PRESS:
                    cls.__pressed_modifiers[session_id].add(key_name)
                else:
                    cls.__pressed_modifiers[session_id].discard(key_name)

            packet = KeyboardPacket(
                event_type=event_type,
                key_type=KeyBoardType.KEY,
                key_value=key_name,
                session_id=session_id,
            )
            SenderService.send_packet(packet)
            logger.debug(
                f"Sent special key packet: {key_name} ({event_type.value}) for session {session_id}"
            )

    @classmethod
    def __handle_character_key(
        cls, event: QKeyEvent, event_type: KeyBoardEventType, session_id: str
    ):
        """Xử lý phím ký tự thông thường (a-z, 0-9, ...)"""
        # Lấy mã ký tự
        key_code = event.key()

        # Nếu có text thì ưu tiên dùng text (cho các phím có ký tự)
        text = event.text()
        if text and text.isprintable():
            key_value = text
        else:
            key_value = key_code

        packet = KeyboardPacket(
            event_type=event_type,
            key_type=KeyBoardType.KEYCODE,
            key_value=key_value,
            session_id=session_id,
        )
        SenderService.send_packet(packet)
        logger.debug(
            f"Sent character key packet: {key_value} ({event_type.value}) for session {session_id}"
        )

    @classmethod
    def clear_all_modifiers(cls, session_id: str):
        """
        Release tất cả các modifier keys đang được giữ
        Sử dụng khi widget mất focus để tránh sticky keys
        """
        if session_id not in cls.__pressed_modifiers:
            return

        pressed = cls.__pressed_modifiers[session_id].copy()
        for modifier_name in pressed:
            packet = KeyboardPacket(
                event_type=KeyBoardEventType.RELEASE,
                key_type=KeyBoardType.KEY,
                key_value=modifier_name,
                session_id=session_id,
            )
            SenderService.send_packet(packet)
            logger.debug(
                f"Released stuck modifier: {modifier_name} for session {session_id}"
            )

        cls.__pressed_modifiers[session_id].clear()

    @classmethod
    def __handle_key_combination(
        cls, event: QKeyEvent, event_type: KeyBoardEventType, session_id: str
    ):
        """Xử lý tổ hợp phím (Ctrl+C, Alt+Tab, ...)"""
        modifiers = event.modifiers()
        key = event.key()

        combination = []

        # Thêm các phím modifier
        if bool(modifiers & Qt.KeyboardModifier.ControlModifier):
            combination.append("ctrl")
        if bool(modifiers & Qt.KeyboardModifier.ShiftModifier):
            combination.append("shift")
        if bool(modifiers & Qt.KeyboardModifier.AltModifier):
            combination.append("alt")
        if bool(modifiers & Qt.KeyboardModifier.MetaModifier):
            combination.append("meta")

        # Thêm phím chính
        if key in cls.SPECIAL_KEYS:
            combination.append(cls.SPECIAL_KEYS[key])
        else:
            text = event.text()
            if text and text.isprintable():
                combination.append(text.lower())
            else:
                combination.append(chr(key).lower() if 32 <= key <= 126 else str(key))

        packet = KeyboardPacket(
            event_type=event_type,
            key_type=KeyBoardType.COMBINATION,
            key_value=combination,
            session_id=session_id,
        )
        SenderService.send_packet(packet)
        logger.debug(
            f"Sent key combination packet: {'+'.join(combination)} ({event_type.value}) for session {session_id}"
        )

    @classmethod
    def start_listening(cls, session_id: str):
        """Bắt đầu lắng nghe sự kiện bàn phím cho session"""
        if session_id not in cls.__pressed_modifiers:
            cls.__pressed_modifiers[session_id] = set()
        logger.info(f"Keyboard listener started for session: {session_id}")

    @classmethod
    def stop_listening(cls, session_id: str):
        """Dừng lắng nghe sự kiện bàn phím cho session"""
        # Clear all pressed modifiers before stopping
        cls.clear_all_modifiers(session_id)
        if session_id in cls.__pressed_modifiers:
            del cls.__pressed_modifiers[session_id]
        logger.info(f"Keyboard listener stopped for session: {session_id}")
