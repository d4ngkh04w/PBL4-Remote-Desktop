from PyQt5.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QLineEdit,
    QMessageBox,
    QStatusBar,
    QApplication,
)
from PyQt5.QtCore import Qt
from client.auth.auth_manager import AuthManager
from client.network.network_client import NetworkClient
from client.auth.auth_manager import AuthManager
from client.network.network_client import NetworkClient
from common.logger import logger
from common.packet import RequestConnectionPacket
from common.enum import PacketType
from common.password_manager import PasswordManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize components
        self.network_client = NetworkClient()
        self.auth_manager = AuthManager(self.network_client)
        self.remote_widget = None

        # Generate password tự động khi khởi tạo
        self.my_password = PasswordManager.generate_password(6)  # 6 ký tự cho dễ nhớ
        self.my_id = None

        # Track cleanup state to avoid double cleanup
        self._cleanup_done = False

        # UI components that need to be accessed later
        self.id_display = None
        self.password_display = None
        self.connect_btn = None
        self.partner_id_input = None
        self.partner_pass_input = None

        # Setup
        self.init_ui()
        self.setup_connections()

        # Kết nối server sau khi UI đã được khởi tạo hoàn chỉnh
        self.connect_to_server()

    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        self.setWindowTitle("Remote Desktop Client - PBL4")
        self.setGeometry(100, 100, 900, 700)

        # Apply modern style
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0066cc;
            }
        """
        )
       
        # Central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tabs
        self.create_host_tab()
        self.create_controller_tab()


        # Disable controller tab until connected to server
        self.tabs.setTabEnabled(1, False)

        # Status bar
        self.status_bar = self.statusBar()
        if not self.status_bar:
            # Create status bar if it doesn't exist
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Initializing...")

    def create_host_tab(self):
        """Tab hiển thị ID của mình"""
        host_widget = QWidget()
        layout = QVBoxLayout(host_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Share Your ID & Password")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ID Section
        id_group = QGroupBox("Your ID")
        id_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #0066cc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        id_layout = QVBoxLayout(id_group)

        self.id_display = QLabel("Connecting...")
        self.id_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.id_display.setStyleSheet(
            """
            QLabel {
                font-size: 28px;
                font-size: 28px;
                font-weight: bold;
                color: #0066cc;
                background-color: #f8f9fa;
                border: 2px dashed #0066cc;
                border-radius: 8px;
                padding: 15px;
                background-color: #f8f9fa;
                border: 2px dashed #0066cc;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
        """
        )
        id_layout.addWidget(self.id_display)
        layout.addWidget(id_group)

        # Password Section
        pass_group = QGroupBox("Password")
        pass_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #009900;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        pass_layout = QVBoxLayout(pass_group)

        self.password_display = QLabel(
            self.my_password
        )  # Hiển thị password đã generate
        self.password_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_display.setStyleSheet(
            """
            QLabel {
                font-size: 22px;
                font-size: 22px;
                font-weight: bold;
                color: #009900;
                background-color: #f8fff8;
                border: 2px dashed #009900;
                border-radius: 8px;
                padding: 12px;
                background-color: #f8fff8;
                border: 2px dashed #009900;
                border-radius: 8px;
                padding: 12px;
                margin: 5px;
            }
        """
        )
        pass_layout.addWidget(self.password_display)
        layout.addWidget(pass_group)

        # Action buttons
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.refresh_btn = QPushButton("🔄 Refresh Password")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """
        )
        self.refresh_btn.clicked.connect(self.refresh_password)

        copy_id_btn = QPushButton("📋 Copy ID")
        copy_id_btn.setMinimumHeight(40)
        copy_id_btn.setStyleSheet(self.refresh_btn.styleSheet())
        copy_id_btn.clicked.connect(self.copy_id)

        copy_pass_btn = QPushButton("📋 Copy Password")
        copy_pass_btn.setMinimumHeight(40)
        copy_pass_btn.setStyleSheet(self.refresh_btn.styleSheet())
        copy_pass_btn.clicked.connect(self.copy_password)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(copy_id_btn)
        btn_layout.addWidget(copy_pass_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.tabs.addTab(host_widget, "🏠 Your ID")
        self.tabs.addTab(host_widget, "🏠 Your ID")

    def create_controller_tab(self):
        """Tab kết nối đến partner"""
        controller_widget = QWidget()
        layout = QVBoxLayout(controller_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Connect to Partner's Computer")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Connect Section
        connect_group = QGroupBox("Connection Details")
        connect_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #6c757d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        connect_layout = QFormLayout(connect_group)
        connect_layout.setSpacing(15)

        # Partner ID Input
        # Partner ID Input
        self.partner_id_input = QLineEdit()
        self.partner_id_input.setPlaceholderText("Enter 9-digit Partner ID")
        self.partner_id_input.setPlaceholderText("Enter 9-digit Partner ID")
        self.partner_id_input.setMaxLength(9)
        self.partner_id_input.setStyleSheet(
            """
            QLineEdit {
                padding: 10px;
                border: 2px solid #ced4da;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
        """
        )
        connect_layout.addRow("Partner ID:", self.partner_id_input)

        # Password Input
        # Password Input
        self.partner_pass_input = QLineEdit()
        self.partner_pass_input.setPlaceholderText("Enter Password")
        self.partner_pass_input.setEchoMode(QLineEdit.Password)
        self.partner_pass_input.setStyleSheet(self.partner_id_input.styleSheet())
        self.partner_pass_input.setStyleSheet(self.partner_id_input.styleSheet())
        connect_layout.addRow("Password:", self.partner_pass_input)

        layout.addWidget(connect_group)

        layout.addWidget(connect_group)

        # Connect Button
        self.connect_btn = QPushButton("🔗 Connect to Partner")
        self.connect_btn.setMinimumHeight(50)
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """
        )
        self.connect_btn.clicked.connect(self.connect_to_partner)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.connect_btn)

        layout.addStretch()
        self.tabs.addTab(controller_widget, "🎮 Control Partner")

    def setup_connections(self):
        """Thiết lập kết nối signals"""
        self.network_client.on_message_received = self.handle_server_message

        # Enable Enter key for connection
        if self.partner_pass_input is not None:
            self.partner_pass_input.returnPressed.connect(self.connect_to_partner)
        else:
            logger.warning(
                "partner_pass_input is None, cannot connect returnPressed signal"
            )

    def connect_to_server(self):
        """Kết nối đến server để nhận ID"""
        try:
            if self.network_client.connect():
                if hasattr(self, "status_bar") and self.status_bar:
                    self.status_bar.showMessage(
                        "Connected to server, waiting for ID..."
                    )
                logger.info("Connected to server, waiting for ID assignment")
            else:
                if hasattr(self, "status_bar") and self.status_bar:
                    self.status_bar.showMessage("Failed to connect to server")
                self.show_connection_error()
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            self.show_connection_error()

    def show_connection_error(self):
        """Hiển thị lỗi kết nối"""
        if hasattr(self, "id_display") and self.id_display:
            self.id_display.setText("Connection Failed")
            self.id_display.setStyleSheet(
                """
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #dc3545;
                    background-color: #f8d7da;
                    border: 2px dashed #dc3545;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 5px;
                }
            """
            )
        # Disable controller tab if connection failed
        self.tabs.setTabEnabled(1, False)
        if (
            hasattr(self, "my_password")
            and hasattr(self, "password_display")
            and self.password_display
        ):
            self.password_display.setText(self.my_password)

    def handle_server_message(self, packet):
        """Xử lý tin nhắn từ server"""
        try:
            if packet.packet_type == PacketType.ASSIGN_ID:
                self.handle_assign_id(packet)
            elif packet.packet_type == PacketType.AUTHENTICATION_RESPONSE:
                self.handle_authentication_response(packet)
            elif packet.packet_type == PacketType.IMAGE:
                if self.remote_widget:
                    self.remote_widget.handle_image_packet(packet)
            else:
                logger.warning(f"Unknown packet type: {packet.packet_type}")
        except Exception as e:
            logger.error(f"Error handling server message: {e}")

    def handle_assign_id(self, packet):
        """Xử lý phản hồi ID từ server"""
        if hasattr(packet, "client_id"):
            if hasattr(self, "id_display") and self.id_display:
                self.id_display.setText(packet.client_id)
            if hasattr(self, "status_bar") and self.status_bar:
                self.status_bar.showMessage("Ready - ID received from server")
            if hasattr(self, "my_id"):
                self.my_id = packet.client_id
            logger.info(f"Received ID: {packet.client_id}")
            # Enable controller tab when connected
            self.tabs.setTabEnabled(1, True)

    def handle_authentication_response(self, packet):
        """Xử lý phản hồi kết nối từ server"""
        if hasattr(packet, "success") and packet.success:
            self.on_connection_successful()
        else:
            error_msg = getattr(packet, "error_message", "Connection failed")
            self.show_connection_failed(error_msg)

    def connect_to_partner(self):
        """Kết nối đến partner"""
        partner_id = self.partner_id_input.text().strip()
        password = self.partner_pass_input.text().strip()

        # Validation
        # Validation
        if not partner_id or not password:
            QMessageBox.warning(
                self, "Input Error", "Please enter both Partner ID and Password"
            )
            return

        if len(partner_id) != 9 or not partner_id.isdigit():
            QMessageBox.warning(
                self, "Invalid ID", "Partner ID must be exactly 9 digits"
            )
            return

        # Disable button during connection
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("🔄 Connecting...")

        try:
            connect_packet = RequestConnectionPacket(partner_id, self.my_id)
            self.network_client.send(connect_packet)
            self.status_bar.showMessage(f"Connecting to Partner ID: {partner_id}")
            logger.info(f"Connection request sent for partner: {partner_id}")
        except Exception as e:
            logger.error(f"Error sending connect request: {e}")
            self.reset_connect_button()
            QMessageBox.critical(
                self, "Connection Error", f"Failed to send connection request: {str(e)}"
            )

    def on_connection_successful(self):
        """Xử lý khi kết nối thành công"""
        try:
            from client.gui.remote_widget import RemoteWidget

            # Create RemoteWidget
            self.remote_widget = RemoteWidget(self.network_client)

            # Add remote desktop tab
            tab_index = self.tabs.addTab(self.remote_widget, "🖥️ Remote Desktop")
            self.tabs.setCurrentIndex(tab_index)

            # Update UI
            self.connect_btn.setText("🔌 Disconnect")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.disconnect_from_partner)
            self.connect_btn.setEnabled(True)

            self.statusBar().showMessage("✅ Connected - Remote desktop active")
            logger.info("Remote desktop connection established")

        except Exception as e:
            logger.error(f"Error creating remote widget: {e}")
            self.reset_connect_button()

    def show_connection_failed(self, error_message):
        """Hiển thị lỗi kết nối"""
        self.reset_connect_button()
        QMessageBox.critical(
            self, "Connection Failed", f"Failed to connect to partner:\n{error_message}"
        )
        self.statusBar().showMessage("❌ Connection failed")

    def disconnect_from_partner(self):
        """Ngắt kết nối khỏi partner"""
        if self.remote_widget:
            # Remove remote desktop tab
            for i in range(self.tabs.count()):
                if self.tabs.widget(i) == self.remote_widget:
                    self.tabs.removeTab(i)
                    break

            # Cleanup
            self.remote_widget.cleanup()
            self.remote_widget = None

        self.reset_connect_button()
        self.statusBar().showMessage("Disconnected from partner")
        logger.info("Disconnected from partner")

    def reset_connect_button(self):
        """Reset trạng thái nút kết nối"""
        self.connect_btn.setText("🔗 Connect to Partner")
        self.connect_btn.setEnabled(True)
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.connect_to_partner)

    def refresh_password(self):
        """Làm mới password"""
        self.my_password = PasswordManager.generate_password(6)
        if hasattr(self, "password_display") and self.password_display:
            self.password_display.setText(self.my_password)
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage("Password refreshed", 2000)
        logger.info("Password refreshed")

    def copy_id(self):
        """Copy ID to clipboard"""
        if (
            hasattr(self, "id_display")
            and self.id_display
            and self.id_display.text()
            and self.id_display.text() != "Connecting..."
        ):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.id_display.text())
            if hasattr(self, "status_bar") and self.status_bar:
                self.status_bar.showMessage("ID copied to clipboard", 2000)

    def copy_password(self):
        """Copy password to clipboard"""
        clipboard = QApplication.clipboard()
        if hasattr(clipboard, "setText"):
            clipboard.setText(self.my_password)
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage("Password copied to clipboard", 2000)

    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        if self._cleanup_done:
            logger.info("Cleanup already performed, skipping...")
            return

        try:
            logger.info("Starting cleanup process...")
            self._cleanup_done = True

            if self.remote_widget:
                logger.info("Cleaning up remote widget...")
                self.remote_widget.cleanup()

            if self.network_client:
                logger.info("Disconnecting from server...")
                self.network_client.disconnect()

            logger.info("MainWindow cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def closeEvent(self, a0):
        """Xử lý sự kiện đóng ứng dụng"""
        logger.info("Application closing - performing cleanup...")
        self.cleanup()
        if a0:
            a0.accept()  # Chấp nhận sự kiện đóng
        super().closeEvent(a0)


if __name__ == "__main__":
    import sys
    import signal

    app = QApplication(sys.argv)
    window = MainWindow()

    # Đảm bảo cleanup khi nhận signal terminate
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, cleaning up...")
        window.cleanup()
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    window.show()

    try:
        exit_code = app.exec_()
    finally:
        # Đảm bảo cleanup được gọi dù có lỗi gì
        window.cleanup()

    sys.exit(exit_code)
