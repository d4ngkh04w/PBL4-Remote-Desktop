import logging
from PyQt5.QtWidgets import QApplication
from client.gui.main_window import MainWindow
from client.service.auth_service import AuthService
from client.network.socket_client import SocketClient
import sys


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
        self.socket_client = None

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
        """Khởi tạo các dịch vụ (chưa kết nối)"""
        try:
            # Khởi tạo Authentication Service
            self.auth_service = AuthService()

            # Khởi tạo Socket Client (chưa kết nối)
            self.socket_client = SocketClient(
                self.server_host, self.server_port, self.use_ssl, self.cert_file
            )

            return True
        except Exception as e:
            logger.error(f"Failed to initialize services - {e}")
            return False

    def connect_to_server(self):
        """Kết nối đến server sau khi UI đã sẵn sàng"""
        try:
            logger.info(f"Connecting to server at {self.server_host}:{self.server_port}")
            if not self.socket_client.connect():
                logger.warning("Initial connection failed, but auto-reconnect is enabled")
                # Không return False ở đây vì auto-reconnect sẽ chạy background
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server - {e}")
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

            # Khởi tạo Services (chưa kết nối)
            if not self.initialize_services():
                return -1

            # Tạo main window trước
            if not self.create_main_window():
                return -1

            # Hiển thị cửa sổ chính
            if self.main_window is not None:
                self.main_window.show()
            else:
                logger.error("Main window is None, cannot show.")
                return -1

            # Kết nối đến server sau khi UI đã sẵn sàng
            if not self.connect_to_server():
                return -1

            # Chạy vòng lặp sự kiện của ứng dụng
            if self.app is not None:
                return self.app.exec_()
            else:
                logger.error(
                    "QApplication instance is None, cannot execute event loop."
                )
                return -1

        except Exception as e:
            logger.error(f"Failed to start application - {e}")
            return -1

    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        try:
            if self.socket_client:
                self.socket_client.disconnect()
                self.socket_client = None
        except Exception as e:
            logger.error(f"Error during cleanup - {e}")
