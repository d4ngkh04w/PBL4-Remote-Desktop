from enum import Enum


class KeyBoardEventType(Enum):
    """
    Enum các sự kiện bàn phím
    """

    PRESS = "PRESS"
    RELEASE = "RELEASE"  # release là nhả phím ra


class KeyBoardType(Enum):
    """
    Enum các loại phím
    """

    KEY = "KEY"  # Các phím đặc biệt như Ctrl, Shift, Alt, F1-F12, ...
    KEYCODE = "KEYCODE"  # Các phím ký tự như a, b, 1, 2, ...
    COMBINATION = "COMBINATION"  # Tổ hợp phím như Ctrl+C, Alt+Tab, ...


class MouseEventType(Enum):
    """
    Enum các sự kiện chuột
    """

    MOVE = "MOVE"
    PRESS = "PRESS"  # Khi nhấn chuột xuống
    RELEASE = "RELEASE"  # Khi nhả chuột ra
    SCROLL = "SCROLL"
    # DOUBLE_CLICK = 5


class MouseButton(Enum):
    """
    Enum các nút chuột
    """

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    MIDDLE = "MIDDLE"
    UNKNOWN = "UNKNOWN"


class PacketType(Enum):
    """
    Enum các loại gói tin - Format phân nhóm (category/type)
    """

    KEYBOARD = "input/keyboard"
    MOUSE = "input/mouse"

    ASSIGN_ID = "auth/assign-id"
    CLIENT_INFORMATION = "auth/client-info"
    CONNECTION_REQUEST = "auth/connection-request"
    AUTH_PASSWORD = "auth/password"
    CONNECTION_RESPONSE = "auth/connection-response"

    SESSION = "session/control"

    CHAT_MESSAGE = "comm/chat"
    FILE_TRANSFER = "comm/file"

    VIDEO_STREAM = "media/video-stream"
    VIDEO_CONFIG = "media/video-config"

    @classmethod
    def get(cls, value) -> "PacketType":
        from common.packets import Packet

        if not isinstance(value, Packet):
            raise KeyError(f"Invalid packet value: {value}")

        class_name = type(value).__name__

        # Xóa "Packet" ở cuối
        if not class_name.endswith("Packet"):
            raise KeyError(f"Invalid packet class name: {class_name}")

        base_name = class_name[:-6]  # Remove "Packet" suffix

        special_cases = {
            "AuthenticationPassword": "AUTH_PASSWORD",
        }

        if base_name in special_cases:
            snake_case = special_cases[base_name]
        else:
            # Chuyển đổi từ PascalCase sang UPPER_SNAKE_CASE
            import re

            snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", base_name).upper()

        # Tìm PacketType tương ứng
        for member in cls:
            if member.name == snake_case:
                return member

        raise KeyError(
            f"No PacketType found for class '{class_name}' (tried {snake_case})"
        )


class Status(Enum):
    """
    Enum trạng thái
    """

    SUCCESS = "SUCCESS"
    RECEIVER_NOT_FOUND = "RECEIVER_NOT_FOUND"
    SENDER_NOT_FOUND = "SENDER_NOT_FOUND"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    ALREADY_CONNECTED = "ALREADY_CONNECTED"
    ERROR = "ERROR"
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    SERVER_FULL = "SERVER_FULL"
