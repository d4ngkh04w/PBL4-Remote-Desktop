import logging

from pynput import keyboard

from common.enums import KeyBoardEventType, KeyBoardType
from client.handlers.send_handler import SendHandler

logger = logging.getLogger(__name__)


class KeyboardListenerService:
    """Service lắng nghe sự kiện bàn phím và gửi gói tin đến server."""

    def __init__(self):
        self._listener = None
        self._is_running = False

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
            if self._listener:
                self._listener.stop()
                self._listener = None
            self._is_running = False
            logger.info("Keyboard listener stopped")
        except Exception as e:
            logger.error(f"Error stopping keyboard listener: {e}", exc_info=True)

    def __on_press(self, key):
        """Xử lý sự kiện phím được nhấn."""
        try:
            self.__send_key_event(key, KeyBoardEventType.PRESS)
        except Exception as e:
            logger.error(f"Error handling key press: {e}", exc_info=True)

    def __on_release(self, key):
        """Xử lý sự kiện phím được nhả."""
        try:
            self.__send_key_event(key, KeyBoardEventType.RELEASE)
        except Exception as e:
            logger.error(f"Error handling key release: {e}", exc_info=True)

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
                key_vk = ord(key.char) if len(key.char) == 1 else None
                logger.debug(f"Character key: char={key.char}, vk={key_vk}")
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
