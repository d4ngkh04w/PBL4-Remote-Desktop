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
    ID_REQUEST = 4 # Yêu cầu ID và Password
    ID_RESPONSE = 5 # Phản hồi ID và Password
    CONNECT_REQUEST = 6 # Yêu cầu kết nối
    CONNECT_RESPONSE = 7 # Phản hồi kết nối
    CHAT_MESSAGE = 8 # Tin nhắn trò chuyện
    FILE_TRANSFER = 9 # Chuyển file
