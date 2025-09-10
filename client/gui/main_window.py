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
    QStatusBar,
    QApplication,
)
from PyQt5.QtCore import Qt
from client.network.network_client import NetworkClient
from client.controllers.main_window_controller import MainWindowController
from common.password_manager import PasswordManager
from common.utils import unformat_numeric_id


class MainWindow(QMainWindow):
    def __init__(self, server_host, server_port, use_ssl, cert_file, fps=30):
        super().__init__()

        # Initialize components
        self.network_client = NetworkClient(
            server_host, server_port, use_ssl, cert_file
        )
        self.remote_widget = None
        self.fps = fps  # Lưu FPS config

        # Generate password tự động khi khởi tạo
        self.my_password = PasswordManager.generate_password(6)  # 6 ký tự cho dễ nhớ
        self.my_id = None

        # Track cleanup state to avoid double cleanup
        self._cleanup_done = False

        # UI components that need to be accessed later
        self.id_display = None
        self.password_display = None
        self.connect_btn = None
        self.host_id_input = None
        self.host_pass_input = None

        # Initialize controller for business logic
        self.controller = MainWindowController(self, self.network_client, self.fps)

        # Setup
        self.init_ui()
        self.setup_connections()

        # Kết nối server sau khi UI đã được khởi tạo hoàn chỉnh
        self.controller.connect_to_server()

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
        self.host_id_input = QLineEdit()
        self.host_id_input.setPlaceholderText("Enter 9-digit Partner ID")
        self.host_id_input.setMaxLength(9)
        self.host_id_input.setStyleSheet(
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
        connect_layout.addRow("Partner ID:", self.host_id_input)

        # Password Input
        self.host_pass_input = QLineEdit()
        self.host_pass_input.setPlaceholderText("Enter Password")
        self.host_pass_input.setEchoMode(QLineEdit.Password)
        self.host_pass_input.setStyleSheet(self.host_id_input.styleSheet())
        connect_layout.addRow("Password:", self.host_pass_input)

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
        self.connect_btn.clicked.connect(self.connect_to_host)
        layout.addWidget(self.connect_btn)

        # Test Button - chỉ để test UI RemoteWidget
        self.test_ui_btn = QPushButton("🎨 Test Remote UI")
        self.test_ui_btn.setMinimumHeight(40)
        self.test_ui_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """
        )
        self.test_ui_btn.clicked.connect(self.test_remote_ui)
        layout.addWidget(self.test_ui_btn)

        layout.addStretch()
        self.tabs.addTab(controller_widget, "🎮 Control Host")

    def setup_connections(self):
        """Thiết lập kết nối signals - chỉ UI signals"""
        # Enable Enter key for connection
        if self.host_pass_input is not None:
            self.host_pass_input.returnPressed.connect(self.connect_to_host)

    # ====== UI EVENT HANDLERS - delegate to controller ======
    def connect_to_host(self):
        """UI Event: Kết nối đến host"""
        host_id = self.host_id_input.text().strip()
        password = self.host_pass_input.text().strip()
        self.controller.handle_controller_connect(host_id, password)

    def refresh_password(self):
        """UI Event: Làm mới password"""
        self.controller.refresh_password()

    def copy_id(self):
        """UI Event: Copy ID to clipboard"""
        if (
            self.id_display
            and self.id_display.text()
            and self.id_display.text() != "Connecting..."
        ):
            clipboard = QApplication.clipboard()
            clipboard.setText(unformat_numeric_id(self.id_display.text()))
            if self.status_bar:
                self.status_bar.showMessage("ID copied to clipboard", 2000)

    def copy_password(self):
        """UI Event: Copy password to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.my_password)
        if self.status_bar:
            self.status_bar.showMessage("Password copied to clipboard", 2000)

    def test_remote_ui(self):
        """Test function: Show RemoteWidget UI without real connection"""
        try:
            from client.gui.remote_widget import RemoteWidget

            # Tạo RemoteWidget với network_client dummy (None) và parent đúng
            self.remote_widget = RemoteWidget(None, self)

            # Connect disconnect signal
            self.remote_widget.disconnect_requested.connect(self.close_test_remote_ui)

            # Thêm tab mới
            tab_index = self.tabs.addTab(self.remote_widget, "🎨 Test Remote UI")
            self.tabs.setCurrentIndex(tab_index)

            self.status_bar.showMessage("Remote UI test opened", 3000)

        except Exception as e:
            self.status_bar.showMessage(f"Error opening test UI: {str(e)}", 5000)

    def close_test_remote_ui(self):
        """Close test remote UI"""
        if hasattr(self, "remote_widget") and self.remote_widget:
            # Tìm và remove tab
            for i in range(self.tabs.count()):
                if self.tabs.widget(i) == self.remote_widget:
                    self.tabs.removeTab(i)
                    break

            # Cleanup
            self.remote_widget.cleanup()
            self.remote_widget = None
            self.status_bar.showMessage("Test UI closed", 2000)

    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        self.controller.cleanup()

    def closeEvent(self, a0):
        """Xử lý sự kiện đóng ứng dụng"""
        self.cleanup()
        if a0:
            a0.accept()  # Chấp nhận sự kiện đóng
        super().closeEvent(a0)
