import threading
import logging
from common.password_manager import PasswordManager
from common.enum import EventType
from client.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class AuthService:
    """Pure static service quản lý xác thực và mật khẩu"""
    
    # Class variables để lưu trữ state
    _lock = threading.RLock()
    _my_password: str = None
    _running = False
    _initialized = False

    @classmethod
    def initialize(cls):
        """Khởi tạo AuthService"""
        with cls._lock:
            if cls._initialized:
                return
                
            cls._my_password = None
            cls._running = False
            cls.generate_new_password()
            cls._initialized = True


    @classmethod
    def start(cls):
        """Bắt đầu AuthService"""
        with cls._lock:
            if cls._running:
                return

            cls._running = True
            
            # Subscribe to events
            EventBus.subscribe(EventType.CREATE_PASSWORD.name, cls._on_create_password)
            EventBus.subscribe(EventType.VERIFY_PASSWORD.name, cls._on_verify_password)         
    
    @classmethod
    def stop(cls):
        """Dừng AuthService"""
        with cls._lock:
            if not cls._running:
                return

            cls._running = False

            # Unsubscribe khỏi events
            EventBus.unsubscribe(EventType.CREATE_PASSWORD.name, cls._on_create_password)
            EventBus.unsubscribe(EventType.VERIFY_PASSWORD.name, cls._on_verify_password)
            logger.debug("AuthService stopped")

    @classmethod
    def generate_new_password(cls) -> str:
        """Tạo mật khẩu mới"""
        with cls._lock:
            cls._my_password = PasswordManager.generate_password()            
            return cls._my_password
    
    @classmethod
    def get_current_password(cls) -> str:
        """Lấy mật khẩu hiện tại"""
        with cls._lock:
            return cls._my_password
   
    @classmethod
    def verify_password(cls, password: str) -> bool:
        """Xác minh mật khẩu"""        
        with cls._lock:
            return cls._my_password == password
    
    @classmethod
    def _on_create_password(cls, data):
        """Xử lý yêu cầu tạo mật khẩu mới"""
        new_password = cls.generate_new_password()
        EventBus.publish(EventType.PASSWORD_CREATED.name, {
            "password": new_password
        }, source="AuthService")
    
    @classmethod
    def _on_verify_password(cls, data):
        """Xử lý yêu cầu xác minh mật khẩu"""
        if not data or "password" not in data or "controller_id" not in data or "host_id" not in data:
            logger.error("Invalid password verification request")
            return
        
        password_to_verify = data["password"]
        is_valid = cls.verify_password(password_to_verify)

        EventBus.publish(
            EventType.PASSWORD_CORRECT.name if is_valid else EventType.PASSWORD_INCORRECT.name, 
            {"password": password_to_verify, "controller_id": data["controller_id"], "host_id": data["host_id"]}, 
            source="AuthService"
        )


# Convenience functions để dễ sử dụng
def get_auth_service():
    """Trả về class AuthService để dùng như singleton"""
    return AuthService

def initialize_auth_service():
    """Initialize AuthService"""
    return AuthService.initialize()

def start_auth_service():
    """Start AuthService"""
    return AuthService.start()

def stop_auth_service():
    """Stop AuthService"""
    return AuthService.stop()