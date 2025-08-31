from common.enum import PacketType, KeyBoardEventType, MouseEventType, MouseButton


class ImagePacket:
    """
    Gói tin hình ảnh
    """

    def __init__(self, image_data: bytes):
        self.packet_type = PacketType.IMAGE
        self.image_data = image_data

    def __repr__(self):
        return f"ImagePacket(type={self.packet_type}, size={len(self.image_data)})"


class KeyBoardPacket:
    """
    Gói tin bàn phím
    """

    def __init__(self, event_type: KeyBoardEventType, key_code: int):
        self.packet_type = PacketType.KEYBOARD
        self.event_type = event_type
        self.key_code = key_code

    def __repr__(self):
        return f"KeyBoardPacket(type={self.packet_type}, event_type={self.event_type}, key_code={self.key_code})"


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

    def __repr__(self):
        return f"MousePacket(type={self.packet_type}, event_type={self.event_type}, button={self.button}, position={self.position})"


class AssignIdPacket:
    """
    Server cấp ID cho client
    """

    def __init__(self, client_id: str):
        self.packet_type = PacketType.ASSIGN_ID
        self.client_id = client_id

    def __repr__(self):
        return f"AssignIdPacket(type={self.packet_type}, client_id={self.client_id})"


class RequestConnectionPacket:
    """
    Yêu cầu kết nối từ controller -> host
    """

    def __init__(self, target_id: str):
        self.packet_type = PacketType.REQUEST_CONNECTION
        self.target_id = target_id

    def __repr__(self):
        return f"RequestConnectionPacket(type={self.packet_type}, target_id={self.target_id})"


class ResponseConnectionPacket:
    """
    Phản hồi kết nối từ host -> controller
    """

    def __init__(self, success: bool, message: str):
        self.packet_type = PacketType.RESPONSE_CONNECTION
        self.success = success
        self.message = message

    def __repr__(self):
        return f"ResponseConnectionPacket(type={self.packet_type}, success={self.success}, message={self.message})"


class SendPasswordPacket:
    """
    Phản hồi password lại cho máy host
    """

    def __init__(self, host_id: str, password: str):
        self.packet_type = PacketType.AUTHENTICATION_RESPONSE
        self.host_id = host_id
        self.password = password

    def __repr__(self):
        return f"SendPasswordPacket(type={self.packet_type}, host_id={self.host_id})"


class RequestPasswordPacket:
    """
    Yêu cầu xác thực password từ host
    """

    def __init__(self, controller_id: str):
        self.packet_type = PacketType.AUTHENTICATION_REQUEST
        self.controller_id = controller_id

    def __repr__(self):
        return f"RequestPasswordPacket(type={self.packet_type}, controller_id={self.controller_id})"
