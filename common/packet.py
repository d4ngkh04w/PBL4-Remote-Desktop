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

class IDRequestPacket:
    """
    Yêu cầu cấp ID từ sever
    """

    def __init__(self):
        self.packet_type = PacketType.ID_REQUEST

class IDResponsePacket:
    """
    Server trả về ID và password
    """

    def __init__(self, client_id: str, temp_password: str):
        self.packet_type = PacketType.ID_RESPONSE
        self.client_id = client_id
        self.temp_password = temp_password

class ConnectRequestPacket:
    """
    Yêu cầu kết nối từ client
    """

    def __init__(self, client_id: str, temp_password: str):
        self.packet_type = PacketType.CONNECT_REQUEST
        self.client_id = client_id
        self.temp_password = temp_password

class ConnectResponsePacket:
    """
    Phản hồi yêu cầu kết nối từ server
    """

    def __init__(self, success: bool, message: str):
        self.packet_type = PacketType.CONNECT_RESPONSE
        self.success = success
        self.message = message