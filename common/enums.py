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
    Enum các loại gói tin
    """

    IMAGE = 1
    FRAME_UPDATE = 2
    KEYBOARD = 3
    MOUSE = 4
    ASSIGN_ID = 5
    CLIENT_INFORMATION = 6
    CONNECTION_REQUEST = 7
    AUTH_PASSWORD = 8
    CONNECTION_RESPONSE = 9
    SESSION = 10
    CHAT_MESSAGE = 11
    FILE_TRANSFER = 12
    VIDEO_STREAM = 13
    VIDEO_CONFIG = 14


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
