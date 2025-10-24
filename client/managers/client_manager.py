import logging

from common.password_manager import PasswordManager
from common.utils import get_hardware_id

logger = logging.getLogger(__name__)


class ClientManager:
    """
    Quản lý thông tin client
    """

    __my_password: str = ""  # Mật khẩu tạm thời
    __my_id: str = ""
    __custom_password: str | None = None  # Mật khẩu tự đặt
    __device_id: str = ""  # Hardware ID của máy

    @classmethod
    def generate_new_password(cls) -> str:
        """Tạo mật khẩu tạm thời mới"""
        cls.__my_password = PasswordManager.generate_password()
        return cls.__my_password

    @classmethod
    def __get_device_id(cls) -> str:
        """Lấy device ID (hardware ID) của máy"""
        if not cls.__device_id:
            cls.__device_id = get_hardware_id()
        return cls.__device_id

    @classmethod
    def set_custom_password(cls, password: str | None):
        """
        Đặt mật khẩu tự đặt
        """
        cls.__custom_password = password
        device_id = cls.__get_device_id()

        if password:
            PasswordManager.store_password(device_id, password)
        else:
            try:
                PasswordManager.delete_stored_password(device_id)
            except Exception:
                pass

    @classmethod
    def get_custom_password(cls) -> str | None:
        """Lấy mật khẩu tự đặt"""
        return cls.__custom_password

    @classmethod
    def __load_custom_password(cls):
        """Tải mật khẩu tự đặt từ keyring"""
        device_id = cls.__get_device_id()
        stored_password = PasswordManager.get_stored_password(device_id)
        if stored_password:
            cls.__custom_password = stored_password

    @classmethod
    def verify_password(cls, password: str) -> bool:
        """
        Xác minh mật khẩu - kiểm tra cả mật khẩu tạm thời và mật khẩu tự đặt
        """
        temp_match = cls.__my_password == password
        custom_match = (
            cls.__custom_password is not None and cls.__custom_password == password
        )

        return temp_match or custom_match

    @classmethod
    def set_client_id(cls, client_id: str):
        """Set client ID từ server"""
        cls.__my_id = client_id
        cls.__load_custom_password()

    @classmethod
    def get_client_id(cls) -> str:
        """Lấy client ID đã được gán"""
        return cls.__my_id

    @classmethod
    def get_password(cls) -> str:
        """Lấy mật khẩu tạm thời hiện tại"""
        return cls.__my_password
