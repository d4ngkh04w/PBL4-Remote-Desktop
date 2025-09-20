from enum import Enum


class KeyBoardEventType(Enum):
    """
    Enum các sự kiện bàn phím
    """

    PRESS = 1
    RELEASE = 2


class KeyBoardType(Enum):
    """
    Enum các loại phím
    """

    KEY = 1  # Các phím đặc biệt như Ctrl, Shift, Alt, F1-F12, ...
    KEYCODE = 2  # Các phím ký tự như a, b, 1, 2, ...


class MouseEventType(Enum):
    """
    Enum các sự kiện chuột
    """

    MOVE = 1
    PRESS = 2  # Khi nhấn chuột xuống
    RELEASE = 3  # Khi nhả chuột ra
    SCROLL = 4
    # DOUBLE_CLICK = 5


class MouseButton(Enum):
    """
    Enum các nút chuột
    """

    LEFT = 1
    RIGHT = 2
    MIDDLE = 3
    UNKNOWN = 4


class PacketType(Enum):
    """
    Enum các loại gói tin
    """

    IMAGE = 1
    FRAME_UPDATE = 2
    KEYBOARD = 3
    MOUSE = 4
    ASSIGN_ID = 5
    REQUEST_CONNECTION = 6
    RESPONSE_CONNECTION = 7
    REQUEST_PASSWORD = 8
    AUTHENTICATION_RESPONSE = 9
    AUTHENTICATION_REQUEST = 10
    AUTHENTICATION_RESULT = 11
    SESSION = 12
    SEND_PASSWORD = 13
    CHAT_MESSAGE = 14
    FILE_TRANSFER = 15


class SessionAction(Enum):
    """
    Enum các hành động trong phiên điều khiển
    """

    CREATED = 1
    ENDED = 2
    ERROR = 3
    TIMEOUT = 4


class ConnectionStatus(Enum):
    """
    Enum trạng thái kết nối
    """

    SUCCESS = 1
    FAILED = 2
    REJECTED = 3
    SESSION_EXPIRED = 4


class AuthenticationResult(Enum):
    """
    Enum kết quả xác thực
    """

    SUCCESS = 1
    FAILED = 2
