import threading
import logging
from common.packets import AssignIdPacket
from common.password_manager import PasswordManager
from common.enums import EventType
from common.enums import PacketType

logger = logging.getLogger(__name__)


class AuthService:
    """Pure static service quản lý xác thực và mật khẩu"""

    # Class variables để lưu trữ state
    _my_password: str = ""
    _my_id: str = ""
    _partner_id: str = ""

    @classmethod
    def generate_new_password(cls) -> str:
        """Tạo mật khẩu mới"""
        cls._my_password = PasswordManager.generate_password()
        return cls._my_password

    @classmethod
    def get_current_password(cls) -> str:
        """Lấy mật khẩu hiện tại"""
        return cls._my_password

    @classmethod
    def verify_password(cls, password: str) -> bool:
        """Xác minh mật khẩu"""
        return cls._my_password == password

    @classmethod
    def set_client_id(cls, client_id: str):
        """Set client ID từ server"""
        cls._my_id = client_id
        logger.debug(f"Set client ID: {cls._my_id}")

    @classmethod
    def get_client_id(cls) -> str:
        """Lấy client ID đã được gán"""
        return cls._my_id


# Initialize password when module is loaded
AuthService.generate_new_password()


# Convenience functions để dễ sử dụng


def get_client_id():
    """Lấy client ID đã được gán"""
    return AuthService.get_client_id()
