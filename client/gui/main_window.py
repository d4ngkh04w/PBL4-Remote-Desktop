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

from client.controllers.main_window_controller import MainWindowController
from client.service.auth_service import AuthService


class MainWindow(QMainWindow):
    """
    Main window for the client-new application.
    """

    def __init__(self):
        super().__init__()

        # UI components that need to be accessed later
        self.id_display = None
        self.password_display = None
        self.connect_btn = None

        self.host_id_input = None
        self.host_pass_input = None

        self.tabs = None
        self.status_bar = None
        self.remote_widget = None

        # Track cleanup state
        self._cleanup_done = False

        # Initialize controller for business logic
        self.controller = MainWindowController(self)

        # Setup UI
        self.init_ui()

        # Start controller after UI is ready
        self.controller.start()

        # Initialize password display
        if self.password_display:
            self.password_display.setText(AuthService.get_password())

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

        # Create tabs only after self.tabs is initialized
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

        # Connect to server will be done after UI is fully initialized

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
                font-weight: bold;
                color: #0066cc;
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

        self.password_display = QLabel("Loading...")
        self.password_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_display.setStyleSheet(
            """
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #009900;
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
        self.refresh_btn.clicked.connect(self.controller.refresh_password)

        copy_id_btn = QPushButton("📋 Copy ID")
        copy_id_btn.setMinimumHeight(40)
        copy_id_btn.setStyleSheet(self.refresh_btn.styleSheet())
        copy_id_btn.clicked.connect(self.copy_id_to_clipboard)

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
        self.host_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
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
        self.connect_btn.clicked.connect(self.handle_connect_click)
        layout.addWidget(self.connect_btn)

        layout.addStretch()

        self.tabs.addTab(controller_widget, "🎮 Control Host")

    def handle_connect_click(self):
        """Handle connect button click"""
        if self.host_id_input is not None and self.host_pass_input is not None:
            host_id = self.host_id_input.text().strip()
            host_pass = self.host_pass_input.text().strip()
            self.controller.connect_to_partner(host_id, host_pass)
        else:
            if self.status_bar is not None:
                self.status_bar.showMessage("Input fields are not ready.", 5000)

    def copy_id_to_clipboard(self):
        """Copy ID to clipboard"""
        if AuthService:
            client_id = AuthService.get_client_id()
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(client_id)
                if self.status_bar is not None:
                    self.status_bar.showMessage("ID copied to clipboard!", 2000)

    def copy_password(self):
        """Copy password to clipboard"""
        if AuthService:
            password = AuthService.get_password()
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(password)
                if self.status_bar is not None:
                    self.status_bar.showMessage("Password copied to clipboard!", 2000)

    def closeEvent(self, event):
        """Handle window close event"""
        if not self._cleanup_done:
            self.cleanup()
        event.accept()

    def cleanup(self):
        """Clean up resources when closing"""
        if self._cleanup_done:
            return

        try:
            self._cleanup_done = True

            if self.controller:
                self.controller.cleanup()

            if self.remote_widget:
                if hasattr(self.remote_widget, "cleanup"):
                    self.remote_widget.cleanup()

        except Exception as e:
            print(f"Error during cleanup: {e}")
