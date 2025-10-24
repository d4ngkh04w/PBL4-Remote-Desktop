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
    QMessageBox,
    QApplication,
)
from PyQt5.QtCore import Qt, pyqtSlot
from client.controllers.main_window_controller import main_window_controller
import logging

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng (View).
    Chịu trách nhiệm hiển thị giao diện, nhận tương tác người dùng, khởi tạo widget
    """

    def __init__(self, config):
        super().__init__()

        self.config = config
        self._cleanup_done = False

        # Khởi tạo các biến UI
        self.id_display: QLabel | None = None
        self.password_display: QLabel | None = None
        self.connect_btn: QPushButton | None = None
        self.refresh_btn: QPushButton | None = None
        self.host_id_input: QLineEdit | None = None
        self.host_pass_input: QLineEdit | None = None
        self.tabs: QTabWidget = QTabWidget()
        self.status_bar: QStatusBar | None = None

        # Khởi tạo Controller (chỉ truyền config, không truyền self)
        self.controller = main_window_controller

        # Setup UI
        self.init_ui()

        # Kết nối signals từ Controller đến slots của View
        self._connect_controller_signals()

        # Bắt đầu controller và yêu cầu dữ liệu ban đầu
        self.controller.start()
        self.controller.request_new_password()

    def init_ui(self):
        """Khởi tạo giao diện người dùng, layout và style."""
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
        self.setCentralWidget(self.tabs)

        # Create tabs
        self.create_host_tab()
        self.create_controller_tab()

        # Disable controller tab until connected to server
        self.tabs.setTabEnabled(1, False)

        # Status bar
        self.status_bar = self.statusBar()
        if not self.status_bar:
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Initializing...")

    def _connect_controller_signals(self):
        """Kết nối các signal từ Controller tới các slot cập nhật UI."""
        self.controller.status_updated.connect(self.update_status_bar)
        self.controller.id_updated.connect(self.update_id_display)
        self.controller.password_updated.connect(self.update_password_display)
        self.controller.tabs_state_changed.connect(self.set_controller_tab_enabled)
        self.controller.notification_requested.connect(self.show_notification)

        self.controller.connect_button_state_changed.connect(
            self.update_connect_button_state
        )
        self.controller.text_copied_to_clipboard.connect(self.perform_clipboard_copy)
        self.controller.widget_creation_requested.connect(
            self.create_remote_widget_in_main_thread
        )

    # ==========================================
    # UI Creation Methods (Layout & Style)
    # ==========================================

    def create_host_tab(self):
        """Tab hiển thị ID và Password của máy này."""
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

        # Action buttons styles
        btn_style = """
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

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.refresh_btn = QPushButton("🔄 Refresh Password")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setStyleSheet(btn_style)
        # Kết nối tới phương thức yêu cầu của controller
        self.refresh_btn.clicked.connect(self.controller.request_new_password)

        copy_id_btn = QPushButton("📋 Copy ID")
        copy_id_btn.setMinimumHeight(40)
        copy_id_btn.setStyleSheet(btn_style)
        # Kết nối tới phương thức yêu cầu của controller
        copy_id_btn.clicked.connect(self.controller.request_copy_id)

        copy_pass_btn = QPushButton("📋 Copy Password")
        copy_pass_btn.setMinimumHeight(40)
        copy_pass_btn.setStyleSheet(btn_style)
        # Kết nối tới phương thức yêu cầu của controller
        copy_pass_btn.clicked.connect(self.controller.request_copy_password)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(copy_id_btn)
        btn_layout.addWidget(copy_pass_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.tabs.addTab(host_widget, "🏠 Your ID")

    def create_controller_tab(self):
        """Tab để nhập ID/Pass và kết nối đến máy khác."""
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

        # Input styles
        input_style = """
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

        # Partner ID Input
        self.host_id_input = QLineEdit()
        self.host_id_input.setPlaceholderText("Enter 9-digit Partner ID")
        self.host_id_input.setMaxLength(9)
        self.host_id_input.setStyleSheet(input_style)
        connect_layout.addRow("Partner ID:", self.host_id_input)

        # Password Input
        self.host_pass_input = QLineEdit()
        self.host_pass_input.setPlaceholderText("Enter Password")
        self.host_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.host_pass_input.setStyleSheet(input_style)
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
        # Kết nối tới handler cục bộ để lấy dữ liệu input
        self.connect_btn.clicked.connect(self.handle_connect_click)
        layout.addWidget(self.connect_btn)

        layout.addStretch()

        self.tabs.addTab(controller_widget, "🎮 Control Host")

    # ==========================================
    # User Interaction Handlers (View -> Controller)
    # ==========================================

    def handle_connect_click(self):
        """Lấy dữ liệu từ input và gửi yêu cầu kết nối tới Controller."""
        if self.host_id_input and self.host_pass_input:
            host_id = self.host_id_input.text().strip()
            host_pass = self.host_pass_input.text().strip()
            # Controller sẽ lo việc validate và gửi packet
            self.controller.connect_to_partner(host_id, host_pass)
        else:
            self.show_notification("Input fields are not initialized.", "error")

    # ==========================================
    # UI Update Slots (Controller -> View)
    # ==========================================

    @pyqtSlot(str)
    def update_status_bar(self, message: str):
        """Cập nhật thanh trạng thái."""
        if self.status_bar:
            self.status_bar.showMessage(message, 5000)

    @pyqtSlot(str)
    def update_id_display(self, client_id: str):
        """Cập nhật label hiển thị ID."""
        if self.id_display:
            self.id_display.setText(client_id)

    @pyqtSlot(str)
    def update_password_display(self, password: str):
        """Cập nhật label hiển thị mật khẩu."""
        if self.password_display:
            self.password_display.setText(password)

    @pyqtSlot(bool)
    def set_controller_tab_enabled(self, enabled: bool):
        """Bật/tắt tab điều khiển."""
        self.tabs.setTabEnabled(1, enabled)

    @pyqtSlot(bool, str)
    def update_connect_button_state(self, enabled: bool, text: str):
        """Cập nhật trạng thái và text của nút Connect."""
        if self.connect_btn:
            self.connect_btn.setEnabled(enabled)
            self.connect_btn.setText(text)

    @pyqtSlot(str, str)
    def show_notification(self, message: str, notif_type: str):
        """Hiển thị hộp thoại thông báo (Info, Warning, Error)."""
        title = notif_type.capitalize()
        if notif_type == "error":
            QMessageBox.critical(self, title, message)
        elif notif_type == "warning":
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    @pyqtSlot(str, str)
    def perform_clipboard_copy(self, type_label: str, content: str):
        """Thực hiện copy nội dung vào clipboard hệ thống (UI task)."""
        if content:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(content)
                self.update_status_bar(f"{type_label} copied to clipboard!")

    @pyqtSlot(str)
    def create_remote_widget_in_main_thread(self, session_id: str):
        """Tạo remote widget trong main thread để tránh thread conflicts."""
        try:
            from client.gui.remote_widget import RemoteWidget
            from client.managers.session_manager import SessionManager

            remote_widget = RemoteWidget(session_id)

            SessionManager._sessions[session_id].widget = remote_widget

            self.controller.connect_button_state_changed.emit(
                True, "🔗 Connect to Partner"
            )

            remote_widget.show()
            remote_widget.raise_()
            remote_widget.activateWindow()

            logger.debug(f"Remote widget created in main thread: {session_id}")
            self.update_status_bar(f"Remote session started: {session_id}")

        except Exception as e:
            logger.error(
                f"Error creating remote widget in main thread: {e}", exc_info=True
            )
            self.show_notification(f"Error creating remote window: {e}", "error")

    # ==========================================
    # Cleanup & Lifecycle
    # ==========================================

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ chính."""
        if not self._cleanup_done:
            self.cleanup()
        event.accept()

    def cleanup(self):
        """Dọn dẹp tài nguyên khi ứng dụng đóng."""
        if self._cleanup_done:
            return

        logger.info("Cleaning up MainWindow...")
        self._cleanup_done = True

        try:
            # Dọn dẹp controller (sẽ tự động gửi end session cho tất cả sessions)
            if self.controller:
                self.controller.cleanup()

            logger.info("MainWindow cleanup completed.")

        except Exception as e:
            logger.error(f"Error during MainWindow cleanup: {e}", exc_info=True)
