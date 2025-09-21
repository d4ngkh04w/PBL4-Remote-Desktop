from typing import Optional, Union

from common.enums import (
    PacketType,
    KeyBoardEventType,
    MouseEventType,
    MouseButton,
    SessionAction,
    KeyBoardType,
    ConnectionStatus,
    AuthenticationResult,
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
    Gói tin chứa toàn bộ màn hình (dùng cho lần gửi đầu tiên)
    """

    def __init__(
        self,
        image_data: bytes,
        original_width: int = 0,
        original_height: int = 0,
    ):
        super().__init__(PacketType.IMAGE)
        self.image_data = image_data
        # Kích thước gốc trước khi resize
        self.original_width = original_width
        self.original_height = original_height

    def __repr__(self):
        return f"ImagePacket(type={self.packet_type}, size={len(self.image_data)}, original={self.original_width}x{self.original_height})"


class FrameUpdatePacket(BasePacket):
    """
    Gói tin chứa tất cả các chunk đã thay đổi của một khung hình
    """

    def __init__(self, chunks: list):
        super().__init__(PacketType.FRAME_UPDATE)

        # chunks là một danh sách các tuple chứa thông tin của mỗi chunk.
        # Cấu trúc tuple: (x, y, width, height, image_data_compressed)
        self.chunks = chunks

    def __repr__(self):
        return (
            f"FrameUpdatePacket(type={self.packet_type}, num_chunks={len(self.chunks)})"
        )


class KeyBoardPacket(BasePacket):
    """
    Gói tin bàn phím
    """

    def __init__(
        self,
        event_type: KeyBoardEventType,
        key_type: KeyBoardType,
        key_name: Optional[
            str
        ] = None,  # Tên của phím đặc biệt, ví dụ: 'ctrl_l', 'shift'
        key_vk: Optional[int] = None,  # Mã phím ảo (Virtual-key code) của phím ký tự
    ):
        super().__init__(PacketType.KEYBOARD)
        self.event_type = event_type
        self.key_type = key_type
        self.key_name = key_name
        self.key_vk = key_vk

    def __repr__(self):
        return f"KeyBoardPacket(type={self.packet_type}, event_type={self.event_type}, key_type={self.key_type}, key_name={self.key_name}, key_vk={self.key_vk})"


class MousePacket(BasePacket):
    """
    Gói tin chuột
    """

    def __init__(
        self,
        event_type: MouseEventType,
        position: tuple[int, int],
        button: MouseButton = MouseButton.UNKNOWN,
        scroll_delta: tuple[int, int] = (0, 0),
    ):
        super().__init__(PacketType.MOUSE)
        self.event_type = event_type
        self.button = button
        self.position = position
        self.scroll_delta = scroll_delta

    def __repr__(self):
        return f"MousePacket(type={self.packet_type}, event_type={self.event_type}, button={self.button}, position={self.position}, scroll_delta={self.scroll_delta})"


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
    Phản hồi kết nối
    """

    def __init__(self, connection_status: ConnectionStatus, message: str):
        super().__init__(PacketType.RESPONSE_CONNECTION)
        self.connection_status = connection_status
        self.message = message

    def __repr__(self):
        return f"ResponseConnectionPacket(type={self.packet_type}, connection_status={self.connection_status}, message={self.message})"


class SendPasswordPacket(BasePacket):
    """
    Phản hồi password lại cho máy host
    """

    def __init__(self, host_id: str, controller_id: str, password: str):
        super().__init__(PacketType.SEND_PASSWORD)
        self.host_id = host_id
        self.controller_id = controller_id
        self.password = password

    def __repr__(self):
        return f"SendPasswordPacket(type={self.packet_type}, host_id={self.host_id}, controller_id={self.controller_id}, password={self.password})"


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

    def __init__(self, controller_id: str, host_id: str, success: bool, message: str):
        super().__init__(PacketType.AUTHENTICATION_RESULT)
        self.controller_id = controller_id
        self.host_id = host_id
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
    FrameUpdatePacket,
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
