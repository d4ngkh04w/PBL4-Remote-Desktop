import logging
import time
from threading import Timer

from pynput import keyboard

from common.enums import KeyBoardEventType, KeyBoardType
from client.handlers.send_handler import SendHandler

logger = logging.getLogger(__name__)


class KeyboardListenerService:
    """Service lắng nghe sự kiện bàn phím và gửi gói tin đến server."""

    def __init__(self):
        self._listener = None
        self._is_running = False
        self._pressed_keys = set()  # Theo dõi các phím đang được nhấn
        self._combination_timer = None  # Timer để phát hiện tổ hợp phím
        self._combination_delay = 0.1  # Delay 100ms để phát hiện tổ hợp phím

        # Các phím modifier (thường được sử dụng trong tổ hợp)
        self._modifier_keys = {
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_l,
            keyboard.Key.ctrl_r,
            keyboard.Key.alt,
            keyboard.Key.alt_l,
            keyboard.Key.alt_r,
            keyboard.Key.alt_gr,
            keyboard.Key.shift,
            keyboard.Key.shift_l,
            keyboard.Key.shift_r,
            keyboard.Key.cmd,
            keyboard.Key.cmd_l,
            keyboard.Key.cmd_r,
        }

    def start(self):
        """Bắt đầu lắng nghe sự kiện bàn phím."""
        if self._is_running:
            logger.warning("Keyboard listener already running")
            return

        try:
            self._listener = keyboard.Listener(
                on_press=self.__on_press,
                on_release=self.__on_release,
            )
            self._listener.start()
            self._is_running = True
            logger.info("Keyboard listener started")
        except Exception as e:
            logger.error(f"Error starting keyboard listener: {e}", exc_info=True)

    def stop(self):
        """Dừng lắng nghe sự kiện bàn phím."""
        if not self._is_running:
            return

        try:
            if self._combination_timer:
                self._combination_timer.cancel()
                self._combination_timer = None

            if self._listener:
                self._listener.stop()
                self._listener = None
            self._is_running = False
            self._pressed_keys.clear()
            logger.info("Keyboard listener stopped")
        except Exception as e:
            logger.error(f"Error stopping keyboard listener: {e}", exc_info=True)

    def __on_press(self, key):
        """Xử lý sự kiện phím được nhấn."""
        try:
            # Nếu phím đã được nhấn rồi thì bỏ qua (tránh repeat events)
            if key in self._pressed_keys:
                return

            self._pressed_keys.add(key)

            # Kiểm tra nếu có modifier key và có key khác, đây có thể là tổ hợp phím
            has_modifier = self.__has_modifier_key()
            key_count = len(self._pressed_keys)

            if has_modifier and key_count >= 2:
                # Hủy timer cũ nếu có
                if self._combination_timer:
                    self._combination_timer.cancel()

                # Đặt timer mới để chờ xem có phím nào khác được nhấn không
                self._combination_timer = Timer(
                    self._combination_delay, self.__handle_potential_combination
                )
                self._combination_timer.start()
                logger.debug(f"Potential combination detected with {key_count} keys")
            else:
                # Gửi sự kiện phím đơn lẻ nếu không phải tổ hợp
                if not has_modifier or key_count == 1:
                    self.__send_key_event(key, KeyBoardEventType.PRESS)
        except Exception as e:
            logger.error(f"Error handling key press: {e}", exc_info=True)

    def __on_release(self, key):
        """Xử lý sự kiện phím được nhả."""
        try:
            self._pressed_keys.discard(key)

            # Nếu còn ít hơn 2 phím được nhấn và có timer đang chạy, kích hoạt xử lý tổ hợp ngay
            if len(self._pressed_keys) <= 1 and self._combination_timer:
                self._combination_timer.cancel()
                self.__handle_potential_combination()

            # Gửi sự kiện nhả phím
            self.__send_key_event(key, KeyBoardEventType.RELEASE)
        except Exception as e:
            logger.error(f"Error handling key release: {e}", exc_info=True)

    def __has_modifier_key(self):
        """Kiểm tra xem có phím modifier nào đang được nhấn không."""
        return any(key in self._modifier_keys for key in self._pressed_keys)

    def __handle_potential_combination(self):
        """Xử lý tổ hợp phím tiềm năng."""
        try:
            if len(self._pressed_keys) >= 2 and self.__has_modifier_key():
                # Có tổ hợp phím, gửi packet tổ hợp
                keys_info = []

                # Sắp xếp để modifier keys đi trước
                modifier_keys = [
                    k for k in self._pressed_keys if k in self._modifier_keys
                ]
                regular_keys = [
                    k for k in self._pressed_keys if k not in self._modifier_keys
                ]

                # Thêm modifier keys trước
                for key in modifier_keys:
                    key_info = self.__convert_key_to_info(key)
                    if key_info:
                        keys_info.append(key_info)

                # Thêm regular keys sau
                for key in regular_keys:
                    key_info = self.__convert_key_to_info(key)
                    if key_info:
                        keys_info.append(key_info)

                if keys_info:
                    SendHandler.send_keyboard_combination_packet(
                        session_id=None, keys=keys_info
                    )
                    logger.info(
                        f"Sent keyboard combination: {[str(k) for k in self._pressed_keys]}"
                    )

            self._combination_timer = None
        except Exception as e:
            logger.error(f"Error handling combination: {e}", exc_info=True)

    def __convert_key_to_info(self, key):
        """Chuyển đổi key object thành thông tin key để gửi."""
        try:
            if hasattr(key, "char") and key.char is not None:
                # Phím ký tự
                if len(key.char) == 1:
                    return {
                        "key_type": KeyBoardType.KEYCODE,
                        "key_vk": ord(key.char),
                    }
                else:
                    # Multi-character, treat as special key
                    return {
                        "key_type": KeyBoardType.KEY,
                        "key_name": key.char,
                    }
            elif hasattr(key, "vk") and key.vk is not None:
                # Phím có virtual key code
                return {"key_type": KeyBoardType.KEYCODE, "key_vk": key.vk}
            else:
                # Phím đặc biệt
                return {
                    "key_type": KeyBoardType.KEY,
                    "key_name": str(key).replace("Key.", ""),
                }
        except Exception as e:
            logger.error(f"Error converting key to info: {e}", exc_info=True)
            return None

    def __send_key_event(self, key, event_type: KeyBoardEventType):
        """Gửi sự kiện phím đến server."""
        try:
            key_name = None
            key_vk = None
            key_type = None

            # Kiểm tra xem key có phải là phím ký tự không
            if hasattr(key, "char") and key.char is not None:
                # Phím ký tự (a, b, 1, 2, ...)
                key_type = KeyBoardType.KEYCODE
                if len(key.char) == 1:
                    key_vk = ord(key.char)
                    logger.debug(f"Character key: char={key.char}, vk={key_vk}")
                else:
                    # Multi-character string, treat as special key
                    key_type = KeyBoardType.KEY
                    key_name = key.char
                    logger.debug(f"Multi-char key: char={key.char}")
            elif hasattr(key, "vk") and key.vk is not None:
                # Phím có virtual key code nhưng không có char
                key_type = KeyBoardType.KEYCODE
                key_vk = key.vk
                logger.debug(f"VK key: vk={key.vk}")
            else:
                # Phím đặc biệt (Ctrl, Shift, Alt, F1-F12, ...)
                key_type = KeyBoardType.KEY
                key_name = str(key).replace("Key.", "")
                logger.debug(f"Special key: name={key_name}")

            # Gửi gói tin bàn phím
            SendHandler.send_keyboard_packet(
                session_id=None,
                event_type=event_type,
                key_type=key_type,
                key_name=key_name,
                key_vk=key_vk,
            )

        except Exception as e:
            logger.error(f"Error sending key event: {e}", exc_info=True)

    def is_running(self):
        """Kiểm tra trạng thái listener."""
        return self._is_running
