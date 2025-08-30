from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

# Comment tạm để test UI
# from client.auth.auth_manager import AuthManager
# from client.network.network_client import NetworkClient
from common.logger import logger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Comment tạm để test UI
        # self.network_client = NetworkClient()
        # self.remote_widget = AuthManager()
        self.init_ui()
        # self.setup_connections()

    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        self.setWindowTitle("Remote Desktop Client")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_host_tab()
        self.create_controller_tab()

        self.statusBar().showMessage("Ready (Test Mode)")

    def create_host_tab(self):
        """Tab hiển thị ID của mình"""
        host_widget = QWidget()
        layout = QVBoxLayout()

        # ID Section
        id_group = QGroupBox("Your ID")
        id_layout = QVBoxLayout()

        id_display = QLabel("123456789")  # Mock data
        id_display.setAlignment(Qt.AlignCenter)
        id_display.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #0066cc;
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                padding: 10px;
                margin: 5px;
            }
        """)
        id_layout.addWidget(id_display)
        id_group.setLayout(id_layout)
        layout.addWidget(id_group)

        # Password Section
        pass_group = QGroupBox("Password")
        pass_layout = QVBoxLayout()

        password_display = QLabel("abc123")  # Mock data
        password_display.setAlignment(Qt.AlignCenter)
        password_display.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #009900;
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                padding: 8px;
                margin: 5px;
            }
        """)
        pass_layout.addWidget(password_display)
        pass_group.setLayout(pass_layout)
        layout.addWidget(pass_group)

        # Buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Password")
        refresh_btn.clicked.connect(self.refresh_password)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        host_widget.setLayout(layout)
        self.tabs.addTab(host_widget, "Your ID")

    def create_controller_tab(self):
        """Tab kết nối đến partner"""
        controller_widget = QWidget()
        layout = QVBoxLayout()

        # Connect Section
        connect_group = QGroupBox("Connect to Partner")
        connect_layout = QFormLayout()

        # Partner ID
        self.partner_id_input = QLineEdit()
        self.partner_id_input.setPlaceholderText("Enter Partner ID (9 digits)")
        self.partner_id_input.setMaxLength(9)
        connect_layout.addRow("Partner ID:", self.partner_id_input)

        # Password
        self.partner_pass_input = QLineEdit()
        self.partner_pass_input.setPlaceholderText("Enter Password")
        self.partner_pass_input.setEchoMode(QLineEdit.Password)
        connect_layout.addRow("Password:", self.partner_pass_input)

        # Connect Button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.clicked.connect(self.connect_to_partner)
        connect_layout.addRow("", self.connect_btn)

        connect_group.setLayout(connect_layout)
        layout.addWidget(connect_group)

        layout.addStretch()
        controller_widget.setLayout(layout)
        self.tabs.addTab(controller_widget, "Control Partner")

    def refresh_password(self):
        """Làm mới password"""
        QMessageBox.information(self, "Info", "Refresh Password clicked!")

    def connect_to_partner(self):
        """Kết nối đến partner"""
        partner_id = self.partner_id_input.text().strip()
        password = self.partner_pass_input.text().strip()

        if not partner_id or not password:
            QMessageBox.warning(
                self, "Warning", "Please enter both Partner ID and Password")
            return

        QMessageBox.information(
            self, "Success", f"Connecting to Partner ID: {partner_id}")

    def setup_connections(self):
        """Cài đặt kết nối tín hiệu và khe"""
        pass

    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        logger.info("MainWindow cleanup")
