import logging

from pynput.keyboard import Controller, Key

from common.packets import KeyboardPacket
from common.enums import KeyBoardEventType, KeyBoardType

logger = logging.getLogger(__name__)


class KeyboardExecutorService:
    """Service thực thi các sự kiện bàn phím nhận được từ server."""

    def __init__(self):
        self.__keyboard = Controller()
        self.__running = False

        # Mapping từ tên phím (string) sang Key enum của pynput
        self.__special_keys_map = {
            "alt": Key.alt,
            "alt_l": Key.alt_l,
            "alt_r": Key.alt_r,
            "alt_gr": Key.alt_gr,
            "backspace": Key.backspace,
            "caps_lock": Key.caps_lock,
            "cmd": Key.cmd,
            "cmd_l": Key.cmd_l,
            "cmd_r": Key.cmd_r,
            "ctrl": Key.ctrl,
            "ctrl_l": Key.ctrl_l,
            "ctrl_r": Key.ctrl_r,
            "delete": Key.delete,
            "down": Key.down,
            "end": Key.end,
            "enter": Key.enter,
            "esc": Key.esc,
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12,
            "f13": Key.f13,
            "f14": Key.f14,
            "f15": Key.f15,
            "f16": Key.f16,
            "f17": Key.f17,
            "f18": Key.f18,
            "f19": Key.f19,
            "f20": Key.f20,
            "home": Key.home,
            "left": Key.left,
            "page_down": Key.page_down,
            "page_up": Key.page_up,
            "right": Key.right,
            "shift": Key.shift,
            "shift_l": Key.shift_l,
            "shift_r": Key.shift_r,
            "space": Key.space,
            "tab": Key.tab,
            "up": Key.up,
            "media_play_pause": Key.media_play_pause,
            "media_volume_mute": Key.media_volume_mute,
            "media_volume_down": Key.media_volume_down,
            "media_volume_up": Key.media_volume_up,
            "media_previous": Key.media_previous,
            "media_next": Key.media_next,
            "insert": Key.insert,
            "menu": Key.menu,
            "num_lock": Key.num_lock,
            "pause": Key.pause,
            "print_screen": Key.print_screen,
            "scroll_lock": Key.scroll_lock,
        }

    def start(self):
        """Bắt đầu service."""
        if self.__running:
            logger.warning("Keyboard executor service already running")
            return

        self.__running = True
        logger.info("Keyboard executor service started")

    def stop(self):
        """Dừng service."""
        if not self.__running:
            return

        self.__running = False
        logger.info("Keyboard executor service stopped")

    def execute_keyboard_packet(self, packet: KeyboardPacket):
        """
        Thực thi gói tin bàn phím.

        Args:
            packet: KeyboardPacket chứa thông tin sự kiện bàn phím
        """
        if not self.__running:
            logger.warning("Keyboard executor service is not running")
            return

        try:
            if packet.event_type == KeyBoardEventType.PRESS:
                self.__press_key(packet)
            elif packet.event_type == KeyBoardEventType.RELEASE:
                self.__release_key(packet)
            else:
                logger.warning(f"Unknown keyboard event type: {packet.event_type}")

        except Exception as e:
            logger.error(f"Error executing keyboard packet: {e}", exc_info=True)

    def __press_key(self, packet: KeyboardPacket):
        """Nhấn phím."""
        key = self.__get_key_from_packet(packet)
        if key is not None:
            self.__keyboard.press(key)
            logger.debug(f"Pressed key: {key}")
        else:
            logger.warning(f"Could not determine key to press from packet: {packet}")

    def __release_key(self, packet: KeyboardPacket):
        """Nhả phím."""
        key = self.__get_key_from_packet(packet)
        if key is not None:
            self.__keyboard.release(key)
            logger.debug(f"Released key: {key}")
        else:
            logger.warning(f"Could not determine key to release from packet: {packet}")

    def __get_key_from_packet(self, packet: KeyboardPacket):
        """
        Lấy key object từ packet.

        Returns:
            Key object hoặc string character, hoặc None nếu không xác định được
        """
        try:
            if packet.key_type == KeyBoardType.KEY:
                # Phím đặc biệt (Ctrl, Shift, F1, etc.)
                if packet.key_name:
                    key_name_lower = packet.key_name.lower()
                    key = self.__special_keys_map.get(key_name_lower)
                    if key:
                        return key
                    else:
                        logger.warning(f"Unknown special key name: {packet.key_name}")
                        return None
                else:
                    logger.warning("KEY type packet missing key_name")
                    return None

            elif packet.key_type == KeyBoardType.KEYCODE:
                # Phím ký tự (a, b, 1, 2, etc.)
                if packet.key_vk is not None:
                    try:
                        # Chuyển đổi virtual key code thành ký tự
                        char = chr(packet.key_vk)
                        return char
                    except (ValueError, OverflowError) as e:
                        logger.warning(f"Invalid key_vk: {packet.key_vk}, error: {e}")
                        return None
                else:
                    logger.warning("KEYCODE type packet missing key_vk")
                    return None

            else:
                logger.warning(f"Unknown key type: {packet.key_type}")
                return None

        except Exception as e:
            logger.error(f"Error getting key from packet: {e}", exc_info=True)
            return None

    def is_running(self):
        """Kiểm tra trạng thái service."""
        return self.__running
