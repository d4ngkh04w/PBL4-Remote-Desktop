from typing import Union
import lz4.frame as lz4

from common.enum import (
    PacketType,
    KeyBoardEventType,
    MouseEventType,
    MouseButton,
    SessionAction,
)


class BasePacket:
    """
    Lớp cơ sở cho tất cả các gói tin
    """

    def __init__(self, packet_type: PacketType):
        self.packet_type = packet_type

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self.packet_type})"


class ImagePacket(BasePacket):
    """
    Gói tin hình ảnh
    """

    def __init__(
        self,
        session_id: str,
        image_data: bytes,
        original_width: int = 0,
        original_height: int = 0,
    ):
        super().__init__(PacketType.IMAGE)
        self.session_id = session_id
        self.image_data = image_data
        # Kích thước gốc trước khi resize
        self.original_width = original_width
        self.original_height = original_height

    def __repr__(self):
        return f"ImagePacket(type={self.packet_type}, size={len(self.image_data)}, original={self.original_width}x{self.original_height})"


class KeyBoardPacket(BasePacket):
    """
    Gói tin bàn phím
    """

    def __init__(self, session_id: str, event_type: KeyBoardEventType, key_code: int):
        super().__init__(PacketType.KEYBOARD)
        self.session_id = session_id
        self.event_type = event_type
        self.key_code = key_code

    def __repr__(self):
        return f"KeyBoardPacket(type={self.packet_type}, event_type={self.event_type}, key_code={self.key_code})"


class MousePacket(BasePacket):
    """
    Gói tin chuột
    """

    def __init__(
        self,
        session_id: str,
        event_type: MouseEventType,
        button: MouseButton,
        position: tuple[int, int],
    ):
        super().__init__(PacketType.MOUSE)
        self.session_id = session_id
        self.event_type = event_type
        self.button = button
        self.position = position

    def __repr__(self):
        return f"MousePacket(type={self.packet_type}, event_type={self.event_type}, button={self.button}, position={self.position})"


class AssignIdPacket(BasePacket):
    """
    Server cấp ID cho client
    """

    def __init__(self, client_id: str):
        super().__init__(PacketType.ASSIGN_ID)
        self.client_id = client_id

    def __repr__(self):
        return f"AssignIdPacket(type={self.packet_type}, client_id={self.client_id})"


class RequestConnectionPacket(BasePacket):
    """
    Yêu cầu kết nối từ controller -> host
    """

    def __init__(self, host_id: str, controller_id: str):
        super().__init__(PacketType.REQUEST_CONNECTION)
        self.host_id = host_id
        self.controller_id = controller_id

    def __repr__(self):
        return f"RequestConnectionPacket(type={self.packet_type}, host_id={self.host_id}, controller_id={self.controller_id})"


class ResponseConnectionPacket(BasePacket):
    """
    Phản hồi kết nối\n
    Ví dụ:\n
        {"success": true, "message": "Host is ready"}
        {"success": false, "message": "Host rejected connection"}
        {"success": false, "message": "Host not found"}
        {"success": false, "message": "Invalid password"}
    """

    def __init__(self, success: bool, message: str):
        super().__init__(PacketType.RESPONSE_CONNECTION)
        self.success = success
        self.message = message

    def __repr__(self):
        return f"ResponseConnectionPacket(type={self.packet_type}, success={self.success}, message={self.message})"


class SendPasswordPacket(BasePacket):
    """
    Phản hồi password lại cho máy host
    """

    def __init__(self, host_id: str, controller_id: str, password: str):
        super().__init__(PacketType.AUTHENTICATION_RESPONSE)
        self.host_id = host_id
        self.controller_id = controller_id
        self.password = password

    def __repr__(self):
        return f"SendPasswordPacket(type={self.packet_type}, host_id={self.host_id}, controller_id={self.controller_id})"


class RequestPasswordPacket(BasePacket):
    """
    Yêu cầu xác thực password từ host
    """

    def __init__(self, controller_id: str, host_id: str):
        super().__init__(PacketType.AUTHENTICATION_REQUEST)
        self.controller_id = controller_id
        self.host_id = host_id

    def __repr__(self):
        return f"RequestPasswordPacket(type={self.packet_type}, controller_id={self.controller_id})"


class AuthenticationResultPacket(BasePacket):
    """
    Gói tin kết quả xác thực
    """

    def __init__(self, controller_id: str, success: bool, message: str):
        super().__init__(PacketType.AUTHENTICATION_RESULT)
        self.controller_id = controller_id
        self.success = success
        self.message = message

    def __repr__(self):
        return f"AuthenticationResultPacket(type={self.packet_type}, success={self.success}, message={self.message})"


class SessionPacket(BasePacket):
    """
    Gói tin phiên làm việc
    """

    def __init__(self, session_id: str, action: SessionAction):
        super().__init__(PacketType.SESSION)
        self.session_id = session_id
        self.action = action

    def __repr__(self):
        return f"SessionPacket(type={self.packet_type}, session_id={self.session_id}, action={self.action})"


Packet = Union[
    ImagePacket,
    KeyBoardPacket,
    MousePacket,
    AssignIdPacket,
    SendPasswordPacket,
    RequestConnectionPacket,
    ResponseConnectionPacket,
    AuthenticationResultPacket,
    RequestPasswordPacket,
    SessionPacket,
]
