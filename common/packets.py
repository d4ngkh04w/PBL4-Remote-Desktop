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

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        password: str,
        sender_hostname: str = "Unknown",
    ):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.password = password
        self.sender_hostname = sender_hostname

    def __repr__(self):
        return f"ConnectionRequestPacket(sender_id={self.sender_id}, receiver_id={self.receiver_id}, hostname={self.sender_hostname})"


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

    def __init__(
        self,
        status: Status,
        session_id: str,
        role: str | None = None,
        partner_hostname: str | None = None,
    ):
        self.status = status
        self.session_id = session_id
        self.role = role
        self.partner_hostname = partner_hostname  # Hostname of the other party

    def __repr__(self):
        return f"SessionPacket(status={self.status}), session_id={self.session_id})"


class VideoStreamPacket:
    """
    Gói tin chứa luồng video và thông tin cursor
    """

    def __init__(
        self,
        session_id: str | None,
        video_data: bytes,
        cursor_type: str | None = None,
        cursor_position: tuple[int, int] | None = None,
    ):
        self.video_data = video_data
        self.session_id = session_id
        self.cursor_type = cursor_type  # "normal", "text", "hand", "wait", etc.
        self.cursor_position = cursor_position  # Vị trí tương đối trên monitor

    def __repr__(self):
        return f"VideoStreamPacket(size={len(self.video_data)}, session_id={self.session_id}, cursor={self.cursor_type}@{self.cursor_position})"


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


class ChatMessagePacket:
    """
    Gói tin chat message
    """

    def __init__(
        self, session_id: str, sender_role: str, message: str, timestamp: float
    ):
        self.session_id = session_id
        self.sender_role = sender_role  # "host" or "controller"
        self.message = message
        self.timestamp = timestamp

    def __repr__(self):
        return f"ChatMessagePacket(sender_role={self.sender_role}, message={self.message[:50]}...)"


class FileMetadataPacket:
    """
    Gói tin chứa metadata của file (tên, kích thước, ...)
    """

    def __init__(
        self,
        session_id: str,
        file_id: str,
        filename: str,
        filesize: int,
        sender_role: str,
    ):
        self.session_id = session_id
        self.file_id = file_id
        self.filename = filename
        self.filesize = filesize
        self.sender_role = sender_role  # "host" or "controller"

    def __repr__(self):
        return f"FileMetadataPacket(file_id={self.file_id}, filename={self.filename}, size={self.filesize})"


class FileAcceptPacket:
    """
    Gói tin chấp nhận nhận file
    """

    def __init__(self, session_id: str, file_id: str):
        self.session_id = session_id
        self.file_id = file_id

    def __repr__(self):
        return f"FileAcceptPacket(file_id={self.file_id})"


class FileRejectPacket:
    """
    Gói tin từ chối nhận file
    """

    def __init__(self, session_id: str, file_id: str):
        self.session_id = session_id
        self.file_id = file_id

    def __repr__(self):
        return f"FileRejectPacket(file_id={self.file_id})"


class FileChunkPacket:
    """
    Gói tin chứa chunk dữ liệu file
    """

    def __init__(
        self,
        session_id: str,
        file_id: str,
        chunk_index: int,
        chunk_data: bytes,
        total_chunks: int,
    ):
        self.session_id = session_id
        self.file_id = file_id
        self.chunk_index = chunk_index
        self.chunk_data = chunk_data
        self.total_chunks = total_chunks

    def __repr__(self):
        return f"FileChunkPacket(file_id={self.file_id}, chunk={self.chunk_index}/{self.total_chunks})"


class FileCompletePacket:
    """
    Gói tin thông báo file đã gửi xong
    """

    def __init__(self, session_id: str, file_id: str, success: bool, message: str = ""):
        self.session_id = session_id
        self.file_id = file_id
        self.success = success
        self.message = message

    def __repr__(self):
        return f"FileCompletePacket(file_id={self.file_id}, success={self.success})"


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
    | ChatMessagePacket
    | FileMetadataPacket
    | FileAcceptPacket
    | FileRejectPacket
    | FileChunkPacket
    | FileCompletePacket
)
