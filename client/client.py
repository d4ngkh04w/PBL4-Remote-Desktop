import logging
import sys
import socket
import ssl

from PyQt5.QtWidgets import QApplication

from client.gui.main_window import MainWindow
from client.services.listener_service import ListenerService
from client.services.sender_service import SenderService


logger = logging.getLogger(__name__)


class RemoteDesktopClient:
    """
    Lớp chịu trách nhiệm chính cho việc khởi tạo và chạy vòng đời
    của ứng dụng client (GUI).
    """

    def __init__(self, server_host, server_port, use_ssl, cert_file, fps=30):
        self.config = {
            "server_host": server_host,
            "server_port": server_port,
            "use_ssl": use_ssl,
            "cert_file": cert_file,
            "fps": fps,
        }
        self.app = None
        self.main_window = None
        self.socket = None

    def __initialize_qt_application(self):
        """Khởi tạo ứng dụng QApplication."""
        try:
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("Remote Desktop Client")
            logger.info("Qt application initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Qt application - {e}")
            return False

    def __create_main_window(self):
        """
        Tạo cửa sổ chính và truyền cấu hình kết nối vào cho nó.
        """
        try:
            # MainWindow sẽ nhận config và tự quản lý việc kết nối
            self.main_window = MainWindow(config=self.config)
            logger.info("Main window created successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to create main window - {e}")
            return False
        
    def __connect_to_server(self):
        """Kết nối đến server."""
        try:
            plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.config["use_ssl"]:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_verify_locations(self.config["cert_file"])
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = False
                self.socket = context.wrap_socket(
                    plain_socket, server_hostname=self.config["server_host"]
                )
            else:
                self.socket = plain_socket

            self.socket.settimeout(10)
            self.socket.connect(
                (self.config["server_host"], self.config["server_port"])
            )
            logger.info(
                f"Successfully connected to server at {self.config['server_host']}:{self.config['server_port']}"
            )

            # Khởi tạo các dịch vụ sau khi kết nối thành công
            if not self.__init_services():
                logger.error("Failed to initialize services")
                return False

            from client.controllers.main_window_controller import MainWindowController

            controller = MainWindowController.get_instance()
            if controller:
                controller.on_connection_established()
            return True

        except Exception as e:
            logger.error(f"Failed to connect to server - {e}")
            return False

    def __init_services(self):
        """Khởi tạo dịch vụ Listener và Sender."""
        try:
            if self.socket:
                ListenerService.initialize(self.socket)
                SenderService.initialize(self.socket)
                logger.debug("Listener and Sender services initialized successfully.")
                return True
            else:
                logger.error("Socket is None, cannot initialize services")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize services - {e}")
            return False

    def run(self):
        """
        Chạy ứng dụng: Khởi tạo Qt, tạo cửa sổ, hiển thị và chạy vòng lặp sự kiện.
        """
        try:
            if not self.__initialize_qt_application():
                logger.error("Application initialization failed.")
                return -1

            if not self.__create_main_window():
                logger.error("Failed to create main window.")
                return -1

            # Hiển thị cửa sổ chính
            if self.main_window:
                self.main_window.show()
                logger.debug("Main window displayed successfully.")
            else:
                logger.error("Main window is None, cannot display")
                return -1

            if not self.__connect_to_server():
                logger.error("Failed to connect to server.")
                return -1

            if self.app is not None:
                return self.app.exec_()
            else:
                logger.error("Application is None, cannot start event loop")
                return -1

        except Exception as e:
            logger.error(f"Failed to start application - {e}")
            return -1

    def shutdown(self):
        """Dọn dẹp tài nguyên khi đóng ứng dụng."""
        try:
            if self.main_window:
                self.main_window.cleanup()
                self.main_window = None

            if self.app:
                self.app.quit()
                self.app = None

            ListenerService.shutdown()
            SenderService.shutdown()

            logger.info("Client application shutdown completed.")
        except Exception as e:
            logger.error(f"Error during client shutdown - {e}")
