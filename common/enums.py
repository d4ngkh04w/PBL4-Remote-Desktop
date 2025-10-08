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
    CONNECTION_RESPONSE = 7
    REQUEST_PASSWORD = 8
    SEND_PASSWORD = 9
    CHAT_MESSAGE = 10
    FILE_TRANSFER = 11


class EventType(Enum):
    """
    Enum các loại sự kiện
    """

    # Startup events
    CREATE_PASSWORD = "CREATE_PASSWORD"  # đã xử lí

    # Connection with server events
    NETWORK_CONNECTED = "NETWORK_CONNECTED"  # đã xử lí
    NETWORK_DISCONNECTED = "NETWORK_DISCONNECTED"  # đã xử lí
    NETWORK_CONNECTION_FAILED = "NETWORK_CONNECTION_FAILED"  # đã xử lí
    NETWORK_RECONNECTING = "NETWORK_RECONNECTING"  # chưa xử lí

    # Remote desktop events    
    # Host
    CONNECTED_TO_CONTROLLER = "CONNECTED_TO_CONTROLLER"  # chưa xử lí
    REJECT_CONNECTION = "REJECT_CONNECTION"  # đã xử lí

    # Controller
    CONNECTED_TO_HOST = "CONNECTED_TO_HOST"  # chưa xử lí
    RECEIVE_IMAGE = "RECEIVE_IMAGE"
    RECEIVE_FRAME_UPDATE = "RECEIVE_FRAME_UPDATE"
    DISCONNECTED_WITH_HOST = "DISCONNECTED_WITH_HOST"  # đã xử lí
    GET_HOST_PASSWORD_FROM_UI = "GET_HOST_PASSWORD_FROM_UI"

    # UI events
    UI_UPDATE_STATUS = "UI_UPDATE_STATUS"  # đã xử lí
    UI_SHOW_NOTIFICATION = "UI_SHOW_NOTIFICATION"  
    UI_SHOW_NOTIFICATION_SUGGESTION = "UI_SHOW_NOTIFICATION_SUGGESTION"  # đã xử lí
    UI_SHOW_CLIENT_ID = "UI_SHOW_CLIENT_ID"  # đã xử lí
    UI_SEND_HOST_PASSWORD = "UI_SEND_HOST_PASSWORD"  # đã xử lí

    # Authentication events
    VERIFY_PASSWORD = "VERIFY_PASSWORD"  # đã xử lí
    PASSWORD_CORRECT = "PASSWORD_CORRECT"  # đã xử lí
    PASSWORD_INCORRECT = "PASSWORD_INCORRECT"  # đã xử lí


class ConnectionStatus(Enum):
    """
    Enum trạng thái kết nối
    """

    SUCCESS = "SUCCESS"

    REJECTED = "REJECTED"
    HOST_NOT_FOUND = "HOST_NOT_FOUND"
    HOST_UNAVAILABLE = "HOST_UNAVAILABLE"
    CONTROLLER_NOT_FOUND = "CONTROLLER_NOT_FOUND"
    CONTROLLER_UNAVAILABLE = "CONTROLLER_UNAVAILABLE"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    ERROR = "ERROR"

    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    SERVER_FULL = "SERVER_FULL"
