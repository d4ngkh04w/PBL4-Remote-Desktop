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
    KEYBOARD = 2
    MOUSE = 3
    ASSIGN_ID = 4
    REQUEST_CONNECTION = 5
    RESPONSE_CONNECTION = 6
    REQUEST_PASSWORD = 7
    AUTHENTICATION_RESPONSE = 8
    AUTHENTICATION_REQUEST = 9
    AUTHENTICATION_RESULT = 10
    SEND_PASSWORD = 11
    CHAT_MESSAGE = 12
    FILE_TRANSFER = 13
