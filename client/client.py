import logging
import threading
from PyQt5.QtWidgets import QApplication
from client.gui.main_window import MainWindow
from client.service.auth_service import AuthService
from client.service.connection_service import ConnectionService
from client.core.event_bus import EventBus



logger = logging.getLogger(__name__)

class RemoteDesktopClient:
    """
    Client chính của ứng dụng Remote Desktop
    """

    def __init__(self, server_host, server_port, use_ssl, cert_file, fps=30):
        self.server_host = server_host
        self.server_port = server_port
        self.use_ssl = use_ssl
        self.cert_file = cert_file
        self.fps = fps

        self.app = None
        self.main_window = None
        
        self.auth_service = None
        self.connection_service = None

    def initialize_qt_application(self):
        """Khởi tạo ứng dụng"""        
        # Tạo QApplication
        self.app = QApplication(sys.argv)        
        self.app.setApplicationName("Remote Desktop Client")

        # Kết nối tín hiệu aboutToQuit với slot cleanup
        self.app.aboutToQuit.connect(self.cleanup)    
       
        logger.info("Client created successfully.")
        return True
        

    def initialize_services(self):
        """Khởi tạo các dịch vụ"""
        try:
            # Khởi động EventBus 
            EventBus.start()            

            # Tạo AuthService            
            AuthService.initialize()
            AuthService.start()           

            # Tạo ConnectionService            
            connection_config = {
                "host": self.server_host,
                "port": self.server_port,
                "use_ssl": self.use_ssl,
                "cert_file": self.cert_file,
                "reconnect": True,
            }

            # Sử dụng class methods thay vì instance
            ConnectionService.initialize(connection_config)
            ConnectionService.start()            
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize services - {e}")
            return False

    def create_main_window(self):
        """Tạo cửa sổ chính"""
        try:
            self.main_window = MainWindow()
            return True
        except Exception as e:
            logger.error(f"Failed to create main window - {e}")
            return False

    def run(self):
        """Chạy ứng dụng"""
        try:
            # Khởi tạo Qt Application
            if not self.initialize_qt_application():
                return -1
                
            # Khởi tạo Services
            if not self.initialize_services():
                return -1
                
            # Tạo main window
            if not self.create_main_window():
                return -1
                
            logger.info("Starting Remote Desktop Client")
            
            # Hiển thị cửa sổ chính
            self.main_window.show()
            
            # Chạy vòng lặp sự kiện của ứng dụng
            return self.app.exec_()
            
        except Exception as e:
            logger.error(f"Failed to start application - {e}")
            return -1

    def cleanup(self):
        """Dọn dẹp tài nguyên khi tắt ứng dụng"""
        try:
            logger.info("Starting application cleanup...")
            
            # Dừng main window trước
            if self.main_window:               
                self.main_window.cleanup()       
                logger.info("Main window cleaned up successfully.")    
            
            
            ConnectionService.stop()
            AuthService.stop()            
            EventBus.stop()
                
            logger.info("Application cleanup completed successfully.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
