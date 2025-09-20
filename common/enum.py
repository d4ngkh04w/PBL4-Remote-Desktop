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


class EventType(Enum):
    """
    Enum các loại sự kiện
    """

    # Startup events
    CREATE_PASSWORD = 0 # đã xử lí

    # Connection with server events
    NETWORK_CONNECTED = 1 # đã xử lí
    NETWORK_DISCONNECTED = 2 # đã xử lí
    NETWORK_CONNECTION_FAILED = 3 # đã xử lí
    NETWORK_RECONNECTING = 4 # chưa xử lí

    # Remote desktop events
    # Host 
    CONNECTED_TO_CONTROLLER = 16 # chưa xử lí
    # Controller 
    CONNECTED_TO_HOST = 17 # chưa xử lí
    RECEIVE_IMAGE = 14
    RECEIVE_FRAME_UPDATE = 15
    # UI events
    UI_UPDATE_STATUS = 20 # đã xử lí
    UI_SHOW_NOTIFICATION = 21 # đã xử lí
    UI_SHOW_CLIENT_ID = 22 # đã xử lí
    UI_REQUEST_HOST_PASSWORD = 23 # đã xử lí

    # Authentication events   
    VERIFY_PASSWORD = 32 # đã xử lí
    PASSWORD_CORRECT = 33 # đã xử lí
    PASSWORD_INCORRECT = 34 # đã xử lí


    
