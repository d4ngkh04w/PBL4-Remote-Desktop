from enum import Enum


class KeyBoardEventType(Enum):
    """
    Enum các sự kiện bàn phím
    """

    PRESS = 1
    RELEASE = 2


class MouseEventType(Enum):
    """
    Enum các sự kiện chuột
    """

    MOVE = 1
    CLICK = 2
    SCROLL = 3


class MouseButton(Enum):
    """
    Enum các nút chuột
    """

    LEFT = 1
    RIGHT = 2
    MIDDLE = 3


class PacketType(Enum):
    """
    Enum các loại gói tin
    """

    IMAGE = 1
    IMAGE_CHUNK = 2
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
