import logging

import pynput.mouse as mouse

from common.packets import MousePacket
from common.enums import MouseEventType, MouseButton

logger = logging.getLogger(__name__)


class MouseExecutorService:
    """
    Service thực thi các sự kiện chuột nhận được từ controller
    """

    # Mapping button enum sang pynput Button
    BUTTON_MAP = {
        MouseButton.LEFT: mouse.Button.left,
        MouseButton.RIGHT: mouse.Button.right,
        MouseButton.MIDDLE: mouse.Button.middle,
    }

    __mouse_controller = None

    @classmethod
    def initialize(cls):
        """Khởi tạo mouse controller"""
        try:
            cls.__mouse_controller = mouse.Controller()
            logger.info("MouseExecutorService initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize mouse controller: {e}", exc_info=True)
            return False

    @classmethod
    def execute_mouse_event(cls, packet: MousePacket):
        """
        Thực thi sự kiện chuột từ packet nhận được
        """
        if not cls.__mouse_controller:
            logger.warning("Mouse controller not initialized")
            return

        try:
            if packet.event_type == MouseEventType.MOVE:
                cls.__execute_move(packet)
            elif packet.event_type == MouseEventType.PRESS:
                cls.__execute_press(packet)
            elif packet.event_type == MouseEventType.RELEASE:
                cls.__execute_release(packet)
            elif packet.event_type == MouseEventType.SCROLL:
                cls.__execute_scroll(packet)
            else:
                logger.warning(f"Unknown mouse event type: {packet.event_type}")

        except Exception as e:
            logger.error(f"Error executing mouse event: {e}", exc_info=True)

    @classmethod
    def __execute_move(cls, packet: MousePacket):
        """Thực thi di chuyển chuột"""
        try:
            x, y = packet.position
            cls.__mouse_controller.position = (x, y)
        except Exception as e:
            logger.error(f"Error moving mouse: {e}", exc_info=True)

    @classmethod
    def __execute_press(cls, packet: MousePacket):
        """Thực thi nhấn chuột"""
        try:
            button = cls.BUTTON_MAP.get(packet.button)
            if button is None:
                logger.warning(f"Unknown mouse button: {packet.button}")
                return

            # Di chuyển chuột đến vị trí trước khi nhấn
            x, y = packet.position
            cls.__mouse_controller.position = (x, y)

            # Nhấn nút
            cls.__mouse_controller.press(button)
            logger.debug(f"Mouse pressed: {packet.button.value} at ({x}, {y})")
        except Exception as e:
            logger.error(f"Error pressing mouse button: {e}", exc_info=True)

    @classmethod
    def __execute_release(cls, packet: MousePacket):
        """Thực thi nhả chuột"""
        try:
            button = cls.BUTTON_MAP.get(packet.button)
            if button is None:
                logger.warning(f"Unknown mouse button: {packet.button}")
                return

            # Di chuyển chuột đến vị trí trước khi nhả
            x, y = packet.position
            cls.__mouse_controller.position = (x, y)

            # Nhả nút
            cls.__mouse_controller.release(button)
            logger.debug(f"Mouse released: {packet.button.value} at ({x}, {y})")
        except Exception as e:
            logger.error(f"Error releasing mouse button: {e}", exc_info=True)

    @classmethod
    def __execute_scroll(cls, packet: MousePacket):
        """Thực thi cuộn chuột"""
        try:
            # Di chuyển chuột đến vị trí trước khi cuộn
            x, y = packet.position
            cls.__mouse_controller.position = (x, y)

            # Lấy giá trị cuộn
            dx, dy = packet.scroll_delta

            # Thực hiện cuộn
            # pynput scroll nhận (dx, dy) - dx cho horizontal, dy cho vertical
            cls.__mouse_controller.scroll(dx, dy)
            logger.debug(f"Mouse scrolled: ({dx}, {dy}) at ({x}, {y})")
        except Exception as e:
            logger.error(f"Error scrolling mouse: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên"""
        cls.__mouse_controller = None
        logger.info("MouseExecutorService shutdown")
