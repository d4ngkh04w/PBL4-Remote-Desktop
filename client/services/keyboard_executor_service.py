"""
Service thực thi sự kiện bàn phím trên máy host (máy bị điều khiển)
"""

import logging

import pynput.keyboard as keyboard

from common.packets import KeyboardPacket
from common.enums import KeyBoardEventType, KeyBoardType

logger = logging.getLogger(__name__)


class KeyboardExecutorService:
    """
    Service thực thi các sự kiện bàn phím nhận được từ controller
    """

    # Mapping tên phím sang pynput Key
    SPECIAL_KEY_MAP = {
        "ctrl": keyboard.Key.ctrl,
        "shift": keyboard.Key.shift,
        "alt": keyboard.Key.alt,
        "meta": keyboard.Key.cmd,  # Windows key
        "caps_lock": keyboard.Key.caps_lock,
        "tab": keyboard.Key.tab,
        "backspace": keyboard.Key.backspace,
        "enter": keyboard.Key.enter,
        "esc": keyboard.Key.esc,
        "space": keyboard.Key.space,
        "delete": keyboard.Key.delete,
        "home": keyboard.Key.home,
        "end": keyboard.Key.end,
        "page_up": keyboard.Key.page_up,
        "page_down": keyboard.Key.page_down,
        "left": keyboard.Key.left,
        "up": keyboard.Key.up,
        "right": keyboard.Key.right,
        "down": keyboard.Key.down,
        "insert": keyboard.Key.insert,
        "f1": keyboard.Key.f1,
        "f2": keyboard.Key.f2,
        "f3": keyboard.Key.f3,
        "f4": keyboard.Key.f4,
        "f5": keyboard.Key.f5,
        "f6": keyboard.Key.f6,
        "f7": keyboard.Key.f7,
        "f8": keyboard.Key.f8,
        "f9": keyboard.Key.f9,
        "f10": keyboard.Key.f10,
        "f11": keyboard.Key.f11,
        "f12": keyboard.Key.f12,
        "num_lock": keyboard.Key.num_lock,
        "scroll_lock": keyboard.Key.scroll_lock,
        "print_screen": keyboard.Key.print_screen,
        "pause": keyboard.Key.pause,
    }

    __keyboard_controller = None

    @classmethod
    def initialize(cls):
        """Khởi tạo keyboard controller"""
        try:
            cls.__keyboard_controller = keyboard.Controller()
            return True
        except Exception as e:
            logger.error(
                f"Failed to initialize keyboard controller: {e}", exc_info=True
            )
            return False

    @classmethod
    def execute_keyboard_event(cls, packet: KeyboardPacket):
        """
        Thực thi sự kiện bàn phím từ packet nhận được
        """
        try:
            if packet.key_type == KeyBoardType.KEY:
                cls.__execute_special_key(packet)
            elif packet.key_type == KeyBoardType.KEYCODE:
                cls.__execute_character_key(packet)
            elif packet.key_type == KeyBoardType.COMBINATION:
                cls.__execute_key_combination(packet)
            else:
                logger.warning(f"Unknown key type: {packet.key_type}")

        except Exception as e:
            logger.error(f"Error executing keyboard event: {e}", exc_info=True)

    @classmethod
    def __execute_special_key(cls, packet: KeyboardPacket):
        """Thực thi phím đặc biệt"""
        if not cls.__keyboard_controller:
            return

        key_name = packet.key_value
        key = cls.SPECIAL_KEY_MAP.get(key_name)

        if key is None:
            logger.warning(f"Unknown special key: {key_name}")
            return

        try:
            if packet.event_type == KeyBoardEventType.PRESS:
                cls.__keyboard_controller.press(key)
                logger.debug(f"Pressed special key: {key_name}")
            elif packet.event_type == KeyBoardEventType.RELEASE:
                cls.__keyboard_controller.release(key)
                logger.debug(f"Released special key: {key_name}")
        except Exception as e:
            logger.error(f"Error executing special key {key_name}: {e}", exc_info=True)

    @classmethod
    def __execute_character_key(cls, packet: KeyboardPacket):
        """Thực thi phím ký tự"""
        if not cls.__keyboard_controller:
            return

        key_value = packet.key_value

        try:
            # Nếu key_value là string (ký tự)
            if isinstance(key_value, str):
                if packet.event_type == KeyBoardEventType.PRESS:
                    cls.__keyboard_controller.press(key_value)
                    logger.debug(f"Pressed character: {key_value}")
                elif packet.event_type == KeyBoardEventType.RELEASE:
                    cls.__keyboard_controller.release(key_value)
                    logger.debug(f"Released character: {key_value}")
            # Nếu key_value là mã key code
            elif isinstance(key_value, int):
                # Chuyển đổi key code sang ký tự
                char = chr(key_value) if 32 <= key_value <= 126 else None
                if char:
                    if packet.event_type == KeyBoardEventType.PRESS:
                        cls.__keyboard_controller.press(char)
                        logger.debug(f"Pressed key code: {key_value} ({char})")
                    elif packet.event_type == KeyBoardEventType.RELEASE:
                        cls.__keyboard_controller.release(char)
                        logger.debug(f"Released key code: {key_value} ({char})")
                else:
                    logger.warning(f"Cannot convert key code to character: {key_value}")
        except Exception as e:
            logger.error(
                f"Error executing character key {key_value}: {e}", exc_info=True
            )

    @classmethod
    def __execute_key_combination(cls, packet: KeyboardPacket):
        """Thực thi tổ hợp phím"""
        if not cls.__keyboard_controller:
            return
        combination = packet.key_value

        if not isinstance(combination, list) or len(combination) < 2:
            logger.warning(f"Invalid key combination: {combination}")
            return

        try:
            # Chỉ xử lý khi PRESS (khi nhấn xuống)
            if packet.event_type == KeyBoardEventType.PRESS:
                keys = []

                # Chuyển đổi các phím trong tổ hợp
                for key_name in combination:
                    if key_name in cls.SPECIAL_KEY_MAP:
                        keys.append(cls.SPECIAL_KEY_MAP[key_name])
                    else:
                        keys.append(key_name)

                # Nhấn tất cả các phím modifier trước
                for key in keys[:-1]:
                    cls.__keyboard_controller.press(key)

                # Nhấn phím chính
                cls.__keyboard_controller.press(keys[-1])

                # Nhả phím chính trước
                cls.__keyboard_controller.release(keys[-1])

                # Nhả các phím modifier
                for key in reversed(keys[:-1]):
                    cls.__keyboard_controller.release(key)

                logger.debug(f"Executed key combination: {'+'.join(combination)}")

        except Exception as e:
            logger.error(
                f"Error executing key combination {combination}: {e}", exc_info=True
            )

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên"""
        cls.__keyboard_controller = None
