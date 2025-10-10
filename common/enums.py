from enum import Enum


class KeyBoardEventType(Enum):
    """
    Enum các sự kiện bàn phím
    """

    PRESS = "PRESS"
    RELEASE = "RELEASE"


class KeyBoardType(Enum):
    """
    Enum các loại phím
    """

    KEY = "KEY"  # Các phím đặc biệt như Ctrl, Shift, Alt, F1-F12, ...
    KEYCODE = "KEYCODE"  # Các phím ký tự như a, b, 1, 2, ...


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
    CONNECTION_REQUEST = 6
    AUTH_PASSWORD = 7
    CONNECTION_RESPONSE = 8
    SESSION = 9
    CHAT_MESSAGE = 10
    FILE_TRANSFER = 11
    VIDEO_STREAM = 12


class Status(Enum):
    """
    Enum trạng thái
    """

    SUCCESS = "SUCCESS"
    RECEIVER_NOT_FOUND = "RECEIVER_NOT_FOUND"
    SENDER_NOT_FOUND = "SENDER_NOT_FOUND"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    ERROR = "ERROR"
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    SERVER_FULL = "SERVER_FULL"
