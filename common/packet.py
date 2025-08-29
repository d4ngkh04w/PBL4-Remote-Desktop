from common.enum import PacketType, KeyBoardEventType, MouseEventType, MouseButton


class ImagePacket:
    """
    Gói tin hình ảnh
    """

    def __init__(self, image_data: bytes):
        self.packet_type = PacketType.IMAGE
        self.image_data = image_data


class KeyBoardPacket:
    """
    Gói tin bàn phím
    """

    def __init__(self, event_type: KeyBoardEventType, key_code: int):
        self.packet_type = PacketType.KEYBOARD
        self.event_type = event_type
        self.key_code = key_code


class MousePacket:
    """
    Gói tin chuột
    """

    def __init__(
        self, event_type: MouseEventType, button: MouseButton, position: tuple[int, int]
    ):
        self.packet_type = PacketType.MOUSE
        self.event_type = event_type
        self.button = button
        self.position = position
