import sys
from timeit import main

from PyQt5.QtWidgets import QApplication

from client.gui.main_window import MainWindow
from common.logger import logger


class RemoteDesktopClient:
    """
    Client chính của ứng dụng Remote Desktop
    """

    def __init__(self):
        self.app = None
        self.main_window = None

    def initialize(self):
        """Khởi tạo ứng dụng"""
        try:
            # Tạo QApplication
            self.app = QApplication(sys.argv)

            # Thiết lập thông tin ứng dụng
            self.app.setApplicationName("Remote Desktop Client")
            # Tạo main  window
            self.main_window = MainWindow()
            logger.info("Client created successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to setup application - {e}")
            return False

    def run(self):
        """Chạy ứng dụng"""
        if not self.initialize():
            return -1

        try:
            logger.info("Starting Remote Desktop Client")

            # Hiển thị cửa sổ chính
            self.main_window.show()

            # Chạy vòng lặp sự kiện của ứng dụng
            return self.app.exec_()

        except Exception as e:
            logger.error(f"Failed to start application - {e}")
            return -1

    def shutdown(self):
        """Tắt ứng dụng"""
        try:
            if self.main_window:
                self.main_window.cleanup()
            logger.info("Application shutdown successfully.")
        except Exception as e:
            logger.error(f"Failed to shutdown application - {e}")
            return -1
