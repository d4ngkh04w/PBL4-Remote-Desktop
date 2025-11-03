import logging
import sys
import socket
import ssl
import os
import platform

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase, QFont, QIcon

from client.gui.main_window import MainWindow
from client.services.listener_service import ListenerService
from client.services.sender_service import SenderService
from client.services.keyboard_executor_service import KeyboardExecutorService
from client.services.mouse_executor_service import MouseExecutorService
from common.packets import ClientInformationPacket
from common.protocol import Protocol
from common.utils import get_hostname, get_hardware_id


logger = logging.getLogger(__name__)


class RemoteDesktopClient:
    """
    Lớp chịu trách nhiệm chính cho việc khởi tạo và chạy vòng đời
    của ứng dụng client (GUI).
    """

    def __init__(self, server_host, server_port, use_ssl, cert_file, fps=25):
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
            if sys.platform == "win32":
                import ctypes

                myappid = "pbl4.remotedesktop.app"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

            self.app = QApplication(sys.argv)
            self.app.setApplicationName("Remote Desktop Client")

            # Set application icon
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "assets",
                "images",
                "icon.png",
            )
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                self.app.setWindowIcon(app_icon)
                logger.info(f"Application icon loaded from {icon_path}")
            else:
                logger.warning(f"Icon file not found at {icon_path}")

            # Load custom font from assets/fonts
            font_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "assets",
                "fonts",
                "JetBrainsMono-Regular.ttf",
            )

            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        font_family = font_families[0]
                        font = QFont(font_family, 10)
                        self.app.setFont(font)
                        logger.info(f"Font '{font_family}' loaded successfully")
                    else:
                        logger.warning("Font family not found in the font file")
                else:
                    logger.warning(f"Failed to load font from {font_path}")
            else:
                logger.warning(f"Font file not found at {font_path}")

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

            # Gửi thông tin client lên server
            self.__send_client_information()

            # Khởi tạo các dịch vụ sau khi kết nối thành công
            if not self.__init_services():
                logger.error("Failed to initialize services")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to connect to server - {e}")
            return False

    def __send_client_information(self):
        """Gửi thông tin client (OS, hostname, device_id) lên server."""
        try:
            if not self.socket:
                raise RuntimeError("Socket is not initialized")

            os_info = platform.system()  # Windows, Linux, Darwin (macOS)
            hostname = get_hostname()
            device_id = get_hardware_id()

            client_info_packet = ClientInformationPacket(
                os=os_info, host_name=hostname, device_id=device_id
            )

            Protocol.send_packet(self.socket, client_info_packet)
        except Exception as e:
            logger.error(f"Failed to send client information: {e}")
            raise

    def __init_services(self):
        """Khởi tạo dịch vụ Listener và Sender."""
        try:
            if self.socket:
                SenderService.initialize(self.socket)
                ListenerService.initialize(self.socket)

                # Khởi tạo KeyboardExecutorService và MouseExecutorService (cho máy host)
                KeyboardExecutorService.initialize()
                MouseExecutorService.initialize()

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
            logger.info("Starting client shutdown...")

            # Cleanup main window trước (sẽ tự động end tất cả sessions)
            if self.main_window:
                self.main_window.cleanup()
                self.main_window = None

            if self.socket:
                try:
                    self.socket.close()
                except Exception as e:
                    logger.error(f"Error closing socket: {e}")
                self.socket = None

            ListenerService.shutdown()
            SenderService.shutdown()
            KeyboardExecutorService.shutdown()

            # Quit QApplication
            if self.app:
                self.app.quit()
                self.app = None

            logger.info("Client application shutdown completed.")
        except Exception as e:
            logger.error(f"Error during client shutdown: {e}", exc_info=True)
