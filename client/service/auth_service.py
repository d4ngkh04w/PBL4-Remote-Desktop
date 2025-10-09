import logging
from common.password_manager import PasswordManager

logger = logging.getLogger(__name__)

class AuthService:
    """Pure static service quản lý xác thực và mật khẩu"""
    
    _my_password: str = ""
    _my_id: str = ""
    

    @classmethod
    def generate_new_password(cls) -> str:
        """Tạo mật khẩu mới"""
        cls._my_password = PasswordManager.generate_password()
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
    
    @classmethod
    def get_password(cls) -> str:
        """Lấy mật khẩu hiện tại"""
        return cls._my_password    
 

# Initialize password when module is loaded
AuthService.generate_new_password()

