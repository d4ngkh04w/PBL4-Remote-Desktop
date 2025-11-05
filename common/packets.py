from common.enums import (
    KeyBoardEventType,
    MouseEventType,
    MouseButton,
    KeyBoardType,
    Status,
)


class ClientInformationPacket:
    """Thông tin của client"""

    def __init__(self, os: str, host_name: str, device_id: str):
        self.os = os
        self.host_name = host_name
        self.device_id = device_id


class AssignIdPacket:
    """
    Server cấp ID cho client
    """

    def __init__(self, client_id: str):
        self.client_id = client_id

    def __repr__(self):
        return f"AssignIdPacket(client_id={self.client_id})"


class ConnectionRequestPacket:
    """
    Yêu cầu kết nối từ controller -> host
    """

    def __init__(self, sender_id: str, receiver_id: str, password: str):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.password = password

    def __repr__(self):
        return f"ConnectionRequestPacket(sender_id={self.sender_id}, receiver_id={self.receiver_id})"


class AuthenticationPasswordPacket:
    """Gói tin xác thực mật khẩu"""

    def __init__(self, status: Status = Status.SUCCESS, receiver_id: str = ""):
        self.status = status
        self.receiver_id = receiver_id

    def __repr__(self):
        return f"AuthenticationPassword(status={self.status}, receiver_id={self.receiver_id})"


class ConnectionResponsePacket:
    def __init__(self, connection_status: Status, message: str):
        self.connection_status = connection_status
        self.message = message

    def __repr__(self):
        return f"ConnectionResponsePacket(connection_status={self.connection_status}, message={self.message})"


class SessionPacket:
    """
    Gói tin chứa thông tin phiên làm việc
    """

    def __init__(self, status: Status, session_id: str, role: str | None = None):
        self.status = status
        self.session_id = session_id
        self.role = role

    def __repr__(self):
        return f"SessionPacket(status={self.status}), session_id={self.session_id})"


class VideoStreamPacket:
    """
    Gói tin chứa luồng video
    """

    def __init__(
        self,
        session_id: str | None,
        video_data: bytes,
    ):
        self.video_data = video_data
        self.session_id = session_id

    def __repr__(self):
        return f"VideoStreamPacket(size={len(self.video_data)}, session_id={self.session_id})"


class VideoConfigPacket:
    """
    Packet cấu hình video
    """

    def __init__(
        self,
        session_id: str,
        width: int,
        height: int,
        fps: int,
        codec: str,
        extradata: bytes,
    ):
        self.session_id = session_id
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec  # "h264"
        self.extradata = extradata  # SPS/PPS


class KeyboardPacket:
    """
    Gói tin bàn phím
    """

    def __init__(
        self,
        event_type: KeyBoardEventType,
        key_type: KeyBoardType,
        key_value: str | int | list[str],
        session_id: str | None = None,
    ):
        self.session_id = session_id
        self.event_type = event_type
        self.key_type = key_type
        self.key_value = key_value

    def __repr__(self):
        return f"KeyBoardPacket(event_type={self.event_type}, key_type={self.key_type}, key_value={self.key_value})"


class MousePacket:
    """
    Gói tin chuột
    """

    def __init__(
        self,
        event_type: MouseEventType,
        position: tuple[int, int],
        button: MouseButton = MouseButton.UNKNOWN,
        scroll_delta: tuple[int, int] = (0, 0),
        session_id: str | None = None,
    ):
        self.session_id = session_id
        self.event_type = event_type
        self.button = button
        self.position = position
        self.scroll_delta = scroll_delta

    def __repr__(self):
        return f"MousePacket(event_type={self.event_type}, button={self.button}, position={self.position}, scroll_delta={self.scroll_delta})"


class CursorInfoPacket:
    """
    Gói tin thông tin cursor
    """

    def __init__(
        self,
        session_id: str | None,
        cursor_type: str,
        position: tuple[int, int],
        visible: bool = True,
    ):
        self.session_id = session_id
        self.cursor_type = cursor_type  # "normal", "text", "hand", "wait", etc.
        self.position = position  # Vị trí tương đối trên monitor
        self.visible = visible

    def __repr__(self):
        return f"CursorInfoPacket(cursor_type={self.cursor_type}, position={self.position}, visible={self.visible}, session_id={self.session_id})"


Packet = (
    AssignIdPacket
    | ClientInformationPacket
    | ConnectionRequestPacket
    | ConnectionResponsePacket
    | KeyboardPacket
    | MousePacket
    | AuthenticationPasswordPacket
    | SessionPacket
    | VideoStreamPacket
    | VideoConfigPacket
    | CursorInfoPacket
)
