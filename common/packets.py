from typing import Optional, Union

from common.enums import (
    PacketType,
    KeyBoardEventType,
    MouseEventType,
    MouseButton,
    KeyBoardType,
    Status,
)


class BasePacket:
    """
    Lớp cơ sở cho tất cả các gói tin
    """

    def __init__(self, packet_type: PacketType):
        self.packet_type = packet_type

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self.packet_type})"


class AssignIdPacket(BasePacket):
    """
    Server cấp ID cho client
    """

    def __init__(self, client_id: str):
        super().__init__(PacketType.ASSIGN_ID)
        self.client_id = client_id

    def __repr__(self):
        return f"AssignIdPacket(type={self.packet_type}, client_id={self.client_id})"


class ConnectionRequestPacket(BasePacket):
    """
    Yêu cầu kết nối từ controller -> host
    """

    def __init__(self, sender_id: str, receiver_id: str, password: str):
        super().__init__(PacketType.CONNECTION_REQUEST)
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.password = password

    def __repr__(self):
        return f"ConnectionRequestPacket(type={self.packet_type}, sender_id={self.sender_id}, receiver_id={self.receiver_id})"


class AuthenticationPasswordPacket(BasePacket):
    """Gói tin xác thực mật khẩu"""

    def __init__(self, status: Status = Status.SUCCESS, receiver_id: str = ""):
        super().__init__(PacketType.AUTH_PASSWORD)
        self.status = status
        self.receiver_id = receiver_id

    def __repr__(self):
        return f"AuthenticationPassword(type={self.packet_type}, status={self.status}, receiver_id={self.receiver_id})"


class ConnectionResponsePacket(BasePacket):
    def __init__(self, connection_status: Status, message: str):
        super().__init__(PacketType.CONNECTION_RESPONSE)
        self.connection_status = connection_status
        self.message = message

    def __repr__(self):
        return f"ConnectionResponsePacket(type={self.packet_type}, connection_status={self.connection_status}, message={self.message})"


class SessionPacket(BasePacket):
    """
    Gói tin chứa thông tin phiên làm việc
    """

    def __init__(self, status: Status, session_id: str, role: str | None = None):
        super().__init__(PacketType.SESSION)
        self.status = status
        self.session_id = session_id
        self.role = role

    def __repr__(self):
        return f"SessionPacket(type={self.packet_type}, status={self.status}), session_id={self.session_id})"


# class ImagePacket(BasePacket):
#     """
#     Gói tin chứa toàn bộ màn hình (dùng cho lần gửi đầu tiên)
#     """

#     def __init__(
#         self,
#         image_data: bytes,
#         original_width: int = 0,
#         original_height: int = 0,
#     ):
#         super().__init__(PacketType.IMAGE)
#         self.image_data = image_data
#         # Kích thước gốc trước khi resize
#         self.original_width = original_width
#         self.original_height = original_height

#     def __repr__(self):
#         return f"ImagePacket(type={self.packet_type}, size={len(self.image_data)}, original={self.original_width}x{self.original_height})"


# class FrameUpdatePacket(BasePacket):
#     """
#     Gói tin chứa tất cả các chunk đã thay đổi của một khung hình
#     """

#     def __init__(self, chunks: list):
#         super().__init__(PacketType.FRAME_UPDATE)

#         # chunks là một danh sách các tuple chứa thông tin của mỗi chunk.
#         # Cấu trúc tuple: (x, y, width, height, image_data_compressed)
#         self.chunks = chunks

#     def __repr__(self):
#         return (
#             f"FrameUpdatePacket(type={self.packet_type}, num_chunks={len(self.chunks)})"
#         )


class VideoStreamPacket(BasePacket):
    """
    Gói tin chứa luồng video
    """

    def __init__(self, video_data: bytes):
        super().__init__(PacketType.VIDEO_STREAM)
        self.video_data = video_data

    def __repr__(self):
        return (
            f"VideoStreamPacket(type={self.packet_type}, size={len(self.video_data)})"
        )


class KeyboardPacket(BasePacket):
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


Packet = Union[
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    # ImagePacket,
    # FrameUpdatePacket,
    KeyboardPacket,
    MousePacket,
    AuthenticationPasswordPacket,
    SessionPacket,
    VideoStreamPacket,
]
