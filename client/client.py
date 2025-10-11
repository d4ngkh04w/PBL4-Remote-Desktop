import logging
import sys
from PyQt5.QtWidgets import QApplication
from client.gui.main_window import MainWindow

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

    def _initialize_qt_application(self):
        """Khởi tạo ứng dụng QApplication."""
        try:
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("Remote Desktop Client")
            logger.info("Qt application initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Qt application - {e}")
            return False

    def _create_main_window(self):
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

    def run(self):
        """
        Chạy ứng dụng: Khởi tạo Qt, tạo cửa sổ, hiển thị và chạy vòng lặp sự kiện.
        """
        try:
            if not self._initialize_qt_application():
                return -1

            if not self._create_main_window():
                return -1

            if self.app is not None:
                return self.app.exec_()
            else:
                logger.error("Application is None, cannot start event loop")
                return -1

        except Exception as e:
            logger.error(f"Failed to start application - {e}")
            return -1
