import logging
import os

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QApplication,
    QFrame,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSlot, QSize, QPoint
from PyQt5.QtGui import QIcon, QPixmap

from client.controllers.main_window_controller import main_window_controller


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng - Giao diện đơn giản, tối màu
    """

    def __init__(self, config):
        super().__init__()

        self.config = config
        self.__cleanup_done = False

        # Variables for window dragging
        self.__drag_pos = QPoint()
        self.__is_maximized = False

        # Reference to maximize button for icon switching
        self.maximize_btn: QPushButton | None = None

        # Theme management
        self.__is_dark_mode = True  # Start with dark mode
        self.title_bar: QWidget | None = None  # Reference to title bar for updating
        self.minimize_btn: QPushButton | None = None
        self.close_btn: QPushButton | None = None

        # Icon buttons that need theme updates
        self.copy_id_btn: QPushButton | None = None
        self.copy_pass_btn: QPushButton | None = None
        self.refresh_btn: QPushButton | None = None
        self.remove_custom_btn: QPushButton | None = None

        # Khởi tạo các biến UI
        self.id_label: QLabel | None = None
        self.password_label: QLabel | None = None
        self.remote_id_input: QLineEdit | None = None
        self.remote_password_input: QLineEdit | None = None
        self.connect_btn: QPushButton | None = None
        self.custom_password_display: QLineEdit | None = (
            None  # Hiển thị custom password (ẩn)
        )
        self.custom_password_container: QWidget | None = None  # Container để show/hide

        # Khởi tạo Controller
        self.controller = main_window_controller
        self.controller.set_view(self)  # Set reference to this view

        # Setup UI
        self.init_ui()

        # Kết nối signals từ Controller đến slots của View
        self.__connect_controller_signals()

        # Bắt đầu controller và yêu cầu dữ liệu ban đầu
        self.controller.start()
        self.controller.request_new_password()

        # Cập nhật hiển thị custom password nếu có
        self.update_custom_password_display()

    def init_ui(self):
        """Khởi tạo giao diện đơn giản, tối màu cho Remote Desktop."""
        # Remove window frame and title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setWindowTitle("PBL4 Remote Desktop")
        self.setWindowIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "icon.png",
                )
            )
        )

        # Set window size
        self.resize(1200, 750)

        # Center the window on the screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
        else:
            self.move(100, 100)

        # Get current application font family
        app_font_family = QApplication.font().family()

        # Apply initial theme (dark mode)
        self.apply_theme()

        # Main container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)

        # Content area
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.create_main_content(content_layout)

        main_layout.addWidget(content_container)

        # Update button icons after UI is created
        self.update_button_icons()

    def create_title_bar(self):
        """Create custom title bar."""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)

        # Store reference to title bar
        self.title_bar = title_bar

        self.update_title_bar_style()

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 0, 0)
        title_layout.setSpacing(0)

        # App icon and title
        icon_label = QLabel()
        icon_label.setPixmap(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "icon.png",
                )
            ).pixmap(18, 18)
        )

        title_label = QLabel("PBL4 Remote Desktop")
        title_label.setObjectName("titleBarLabel")

        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # Window control buttons
        btn_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                min-width: 46px;
                max-width: 46px;
                min-height: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """

        # Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "night-mode.png",
                )
            )
        )
        self.theme_btn.setToolTip("Dark Mode")
        self.theme_btn.setIconSize(QSize(20, 20))
        self.theme_btn.setStyleSheet(btn_style)
        self.theme_btn.clicked.connect(self.toggle_theme)

        self.minimize_btn = QPushButton()
        self.minimize_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "minimize-night.svg",
                )
            )
        )
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.setIconSize(QSize(24, 24))
        self.minimize_btn.setStyleSheet(btn_style)
        self.minimize_btn.clicked.connect(self.showMinimized)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "maximize-night.svg",
                )
            )
        )
        self.maximize_btn.setIconSize(QSize(24, 24))
        self.maximize_btn.setStyleSheet(btn_style)
        self.maximize_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "close-night.svg",
                )
            )
        )
        self.close_btn.setToolTip("Close")
        self.close_btn.setIconSize(QSize(24, 24))
        self.close_btn.setStyleSheet(
            btn_style
            + """
            QPushButton:hover {
                background-color: #e81123;
            }
            QPushButton:pressed {
                background-color: #c50f1f;
            }
        """
        )
        self.close_btn.clicked.connect(self.close)

        title_layout.addWidget(self.theme_btn)
        title_layout.addWidget(self.minimize_btn)
        title_layout.addWidget(self.maximize_btn)
        title_layout.addWidget(self.close_btn)

        # Make title bar draggable
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseDoubleClickEvent = lambda e: self.toggle_maximize()

        return title_bar

    def title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.__drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.__is_maximized:
            self.move(event.globalPos() - self.__drag_pos)
            event.accept()

    def toggle_maximize(self):
        """Toggle between maximized and normal state."""
        assets_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "images",
        )
        icon_suffix = "night" if self.__is_dark_mode else "light"

        if self.__is_maximized:
            self.showNormal()
            self.__is_maximized = False
            if self.maximize_btn:
                self.maximize_btn.setIcon(
                    QIcon(os.path.join(assets_path, f"maximize-{icon_suffix}.svg"))
                )
                self.maximize_btn.setToolTip("Maximize")
        else:
            self.showMaximized()
            self.__is_maximized = True
            if self.maximize_btn:
                self.maximize_btn.setIcon(
                    QIcon(os.path.join(assets_path, f"unmaximize-{icon_suffix}.svg"))
                )
                self.maximize_btn.setToolTip("Restore Down")

    def __connect_controller_signals(self):
        """Kết nối các signal từ Controller tới các slot cập nhật UI."""
        self.controller.id_updated.connect(self.update_id_display)
        self.controller.password_updated.connect(self.update_password_display)
        self.controller.notification_requested.connect(self.show_notification)
        self.controller.connect_button_state_changed.connect(
            self.update_connect_button_state
        )
        self.controller.text_copied_to_clipboard.connect(self.perform_clipboard_copy)
        self.controller.widget_creation_requested.connect(
            self.create_remote_widget_in_main_thread
        )
        self.controller.custom_password_changed.connect(
            self.update_custom_password_display
        )

    # ==========================================
    # UI Creation Methods
    # ==========================================

    def create_main_content(self, parent_layout):
        """Tạo nội dung chính."""
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(60, 50, 60, 50)
        content_layout.setSpacing(40)

        # === YOUR COMPUTER SECTION ===
        your_section = QWidget()
        your_section.setObjectName("sectionWidget")
        your_section_layout = QVBoxLayout(your_section)
        your_section_layout.setSpacing(18)

        # Section header
        your_header = QLabel("Your Computer")
        your_header.setObjectName("sectionHeader")
        your_section_layout.addWidget(your_header)

        # Info text
        your_info = QLabel(
            "Share this ID and Password with others to allow them to connect to your computer"
        )
        your_info.setObjectName("infoText")
        your_info.setWordWrap(True)
        your_section_layout.addWidget(your_info)

        # ID and Password container
        credentials_container = QWidget()
        credentials_layout = QHBoxLayout(credentials_container)
        credentials_layout.setSpacing(20)

        # Your ID box
        id_box = QWidget()
        id_box_layout = QVBoxLayout(id_box)
        id_box_layout.setSpacing(10)
        id_box_layout.setContentsMargins(0, 0, 0, 0)

        id_title = QLabel("Your ID")
        id_title.setObjectName("titleLabel")

        # ID display with copy button inside
        id_display_container = QWidget()
        id_display_container.setObjectName("idDisplayContainer")
        id_display_layout = QHBoxLayout(id_display_container)
        id_display_layout.setContentsMargins(20, 15, 15, 15)
        id_display_layout.setSpacing(10)

        self.id_label = QLabel("Connecting...")
        self.id_label.setObjectName("idLabel")
        self.id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.copy_id_btn = QPushButton()
        self.copy_id_btn.setObjectName("copyBtn")
        self.copy_id_btn.setIconSize(QSize(20, 20))
        self.copy_id_btn.setFixedSize(40, 40)
        self.copy_id_btn.setToolTip("Copy ID")
        self.copy_id_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_id_btn.clicked.connect(self.controller.request_copy_id)

        id_display_layout.addWidget(self.id_label, 1)
        id_display_layout.addWidget(self.copy_id_btn)

        id_box_layout.addWidget(id_title)
        id_box_layout.addWidget(id_display_container)

        # Password box
        pass_box = QWidget()
        pass_box_layout = QVBoxLayout(pass_box)
        pass_box_layout.setSpacing(10)
        pass_box_layout.setContentsMargins(0, 0, 0, 0)

        pass_title = QLabel("Password")
        pass_title.setObjectName("titleLabel")

        # Password display with buttons inside
        password_display_container = QWidget()
        password_display_container.setObjectName("passwordDisplayContainer")
        password_display_layout = QHBoxLayout(password_display_container)
        password_display_layout.setContentsMargins(20, 15, 15, 15)
        password_display_layout.setSpacing(10)

        self.password_label = QLabel("Loading...")
        self.password_label.setObjectName("passwordLabel")
        self.password_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.copy_pass_btn = QPushButton()
        self.copy_pass_btn.setObjectName("copyBtn")
        self.copy_pass_btn.setIconSize(QSize(20, 20))
        self.copy_pass_btn.setFixedSize(40, 40)
        self.copy_pass_btn.setToolTip("Copy Password")
        self.copy_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_pass_btn.clicked.connect(self.controller.request_copy_password)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setFixedSize(40, 40)
        self.refresh_btn.setToolTip("Refresh Password")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.controller.request_new_password)

        password_display_layout.addWidget(self.password_label, 1)
        password_display_layout.addWidget(self.copy_pass_btn)
        password_display_layout.addWidget(self.refresh_btn)

        pass_box_layout.addWidget(pass_title)
        pass_box_layout.addWidget(password_display_container)

        credentials_layout.addWidget(id_box, 3)
        credentials_layout.addWidget(pass_box, 2)

        your_section_layout.addWidget(credentials_container)

        # Custom Password Section
        custom_pass_container = QWidget()
        custom_pass_layout = QHBoxLayout(custom_pass_container)
        custom_pass_layout.setContentsMargins(15, 10, 0, 0)
        custom_pass_layout.setSpacing(20)

        set_custom_btn = QPushButton("Set Custom Password")
        set_custom_btn.setObjectName("setCustomBtn")
        set_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_custom_btn.setFixedHeight(36)
        set_custom_btn.clicked.connect(self.on_set_custom_password_clicked)

        # Custom password display (ẩn, chỉ hiện khi đã có custom password)
        self.custom_password_display = QLineEdit()
        self.custom_password_display.setReadOnly(True)
        self.custom_password_display.setEchoMode(QLineEdit.EchoMode.Password)
        self.custom_password_display.setFixedHeight(36)
        self.custom_password_display.setFixedWidth(180)
        self.custom_password_display.setPlaceholderText("Custom Password Set")

        # Nút xóa (icon close)
        self.remove_custom_btn = QPushButton()
        self.remove_custom_btn.setObjectName("removeCustomBtn")
        self.remove_custom_btn.setIconSize(QSize(16, 16))
        self.remove_custom_btn.setFixedSize(32, 32)
        self.remove_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_custom_btn.setToolTip("Remove Custom Password")
        self.remove_custom_btn.clicked.connect(
            self.controller.request_remove_custom_password
        )

        password_display_container = QWidget()
        password_display_layout = QHBoxLayout(password_display_container)
        password_display_layout.setContentsMargins(0, 0, 0, 0)
        password_display_layout.setSpacing(16)
        password_display_layout.addWidget(self.custom_password_display)
        password_display_layout.addWidget(self.remove_custom_btn)
        password_display_layout.addStretch()

        custom_pass_layout.addWidget(set_custom_btn)
        custom_pass_layout.addWidget(password_display_container)
        custom_pass_layout.addStretch()

        # Ẩn password display mặc định, sẽ hiện khi load hoặc set password
        password_display_container.setVisible(False)
        self.custom_password_container = (
            password_display_container  # Lưu reference để show/hide
        )

        your_section_layout.addWidget(custom_pass_container)

        content_layout.addWidget(your_section)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        content_layout.addWidget(separator)

        # === CONNECT TO PARTNER SECTION ===
        partner_section = QWidget()
        partner_section.setObjectName("sectionWidget")
        partner_section_layout = QVBoxLayout(partner_section)
        partner_section_layout.setSpacing(18)

        # Section header
        partner_header = QLabel("Connect to Partner")
        partner_header.setObjectName("sectionHeader")
        partner_section_layout.addWidget(partner_header)

        # Info text
        partner_info = QLabel(
            "Enter your partner's ID and Password to control their computer"
        )
        partner_info.setObjectName("infoText")
        partner_info.setWordWrap(True)
        partner_section_layout.addWidget(partner_info)

        # Input container
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setSpacing(20)

        # Partner ID input
        id_input_box = QWidget()
        id_input_layout = QVBoxLayout(id_input_box)
        id_input_layout.setSpacing(10)
        id_input_layout.setContentsMargins(0, 0, 0, 0)

        partner_id_title = QLabel("Partner ID")
        partner_id_title.setObjectName("titleLabel")

        self.remote_id_input = QLineEdit()
        self.remote_id_input.setPlaceholderText("Enter 9-digit ID...")
        self.remote_id_input.setMaxLength(9)
        self.remote_id_input.setMinimumHeight(50)

        id_input_layout.addWidget(partner_id_title)
        id_input_layout.addWidget(self.remote_id_input)

        # Partner Password input
        pass_input_box = QWidget()
        pass_input_layout = QVBoxLayout(pass_input_box)
        pass_input_layout.setSpacing(10)
        pass_input_layout.setContentsMargins(0, 0, 0, 0)

        partner_pass_title = QLabel("Password")
        partner_pass_title.setObjectName("titleLabel")

        self.remote_password_input = QLineEdit()
        self.remote_password_input.setPlaceholderText("Enter password...")
        self.remote_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_password_input.setMinimumHeight(50)

        pass_input_layout.addWidget(partner_pass_title)
        pass_input_layout.addWidget(self.remote_password_input)

        # Connect button
        connect_btn_box = QWidget()
        connect_btn_layout = QVBoxLayout(connect_btn_box)
        connect_btn_layout.setSpacing(10)
        connect_btn_layout.setContentsMargins(0, 0, 0, 0)

        # Spacer to align with inputs - use a transparent label
        connect_label = QLabel(" ")
        connect_label.setFixedHeight(18)  # Match the height of titleLabel
        connect_label.setStyleSheet("background-color: transparent;")

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setMinimumHeight(50)
        self.connect_btn.setMinimumWidth(140)
        self.connect_btn.clicked.connect(self.handle_connect_click)

        connect_btn_layout.addWidget(connect_label)
        connect_btn_layout.addWidget(self.connect_btn)

        input_layout.addWidget(id_input_box, 3)
        input_layout.addWidget(pass_input_box, 2)
        input_layout.addWidget(connect_btn_box)

        partner_section_layout.addWidget(input_container)

        content_layout.addWidget(partner_section)
        content_layout.addStretch()

        parent_layout.addWidget(content)

    # ==========================================
    # User Interaction Handlers
    # ==========================================

    def handle_connect_click(self):
        """Lấy dữ liệu từ input và gửi yêu cầu kết nối tới Controller."""
        if self.remote_id_input and self.remote_password_input:
            host_id = self.remote_id_input.text().strip()
            host_pass = self.remote_password_input.text().strip()
            # Controller sẽ lo việc validate và gửi packet
            self.controller.connect_to_partner(host_id, host_pass)
        else:
            self.show_notification("Input fields are not initialized.", "error")

    def on_set_custom_password_clicked(self):
        """Xử lý khi click nút Set Custom Password."""
        self.controller.request_set_custom_password()

    @pyqtSlot()
    def update_custom_password_display(self):
        """Cập nhật hiển thị custom password field dựa trên việc có custom password hay không."""
        from client.managers.client_manager import ClientManager

        has_custom_password = ClientManager.get_custom_password() is not None

        if has_custom_password and self.custom_password_container:
            custom_password = ClientManager.get_custom_password()
            if self.custom_password_display and custom_password:
                self.custom_password_display.setText(custom_password)
            self.custom_password_container.setVisible(True)
        elif self.custom_password_container:
            self.custom_password_container.setVisible(False)

        # Update style based on theme
        self.update_custom_password_style()

    def update_custom_password_style(self):
        """Update custom password display style based on current theme."""
        if self.custom_password_display:
            if self.__is_dark_mode:
                self.custom_password_display.setStyleSheet(
                    """
                    QLineEdit {
                        border: 1px solid #404040;
                        background-color: #2a2a2a;
                        color: #e8e8e8;
                        selection-background-color: transparent;
                        selection-color: #e8e8e8;
                        letter-spacing: 3px;
                    }
                    QLineEdit:hover {
                        border: 1px solid #404040;
                        background-color: #2a2a2a;
                    }
                    QLineEdit:focus {
                        border: 1px solid #404040;
                        background-color: #2a2a2a;
                    }
                    """
                )
            else:
                self.custom_password_display.setStyleSheet(
                    """
                    QLineEdit {
                        border: 2px solid #e0e0e0;
                        background-color: #fafafa;
                        color: #000000;
                        selection-background-color: transparent;
                        selection-color: #000000;
                        letter-spacing: 3px;
                    }
                    QLineEdit:hover {
                        border: 2px solid #e0e0e0;
                        background-color: #fafafa;
                    }
                    QLineEdit:focus {
                        border: 2px solid #e0e0e0;
                        background-color: #fafafa;
                    }
                    """
                )

    # ==========================================
    # UI Update Slots
    # ==========================================

    @pyqtSlot(str)
    def update_id_display(self, client_id: str):
        """Cập nhật label hiển thị ID."""
        if self.id_label:
            self.id_label.setText(client_id)

    @pyqtSlot(str)
    def update_password_display(self, password: str):
        """Cập nhật label hiển thị mật khẩu."""
        if self.password_label:
            self.password_label.setText(password)

    @pyqtSlot(bool, str)
    def update_connect_button_state(self, enabled: bool, text: str):
        """Cập nhật trạng thái của nút Connect."""
        if self.connect_btn:
            self.connect_btn.setEnabled(enabled)
            if text:  # Chỉ cập nhật text khi có giá trị
                self.connect_btn.setText(text)
            elif enabled:  # Reset về text mặc định khi enable lại
                self.connect_btn.setText("Connect")

    @pyqtSlot(str, str)
    def show_notification(self, message: str, notif_type: str):
        """Hiển thị hộp thoại thông báo (Info, Warning, Error)."""
        try:
            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
            )
            dialog.setModal(True)

            image_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "assets",
                "images",
            )

            # Get icon based on type
            if notif_type == "error":
                icon_path = os.path.join(image_path, "error.png")
            elif notif_type == "warning":
                icon_path = os.path.join(image_path, "warning.png")
            else:
                icon_path = os.path.join(image_path, "info.png")

            # Create layout
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(25, 25, 25, 25)
            main_layout.setSpacing(20)

            # Content layout (icon + message)
            content_layout = QHBoxLayout()
            content_layout.setSpacing(25)

            # Icon label
            icon_label = QLabel()
            pixmap = QPixmap(icon_path).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
            icon_label.setFixedSize(64, 64)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            content_layout.addWidget(icon_label)

            # Message label
            msg_label = QLabel(message)
            msg_label.setWordWrap(True)
            msg_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            content_layout.addWidget(msg_label, 1)

            main_layout.addLayout(content_layout)

            # OK button
            ok_button = QPushButton("OK")
            ok_button.setFixedWidth(100)
            ok_button.clicked.connect(dialog.accept)

            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(ok_button)
            button_layout.addStretch()

            main_layout.addLayout(button_layout)

            dialog.setLayout(main_layout)
            dialog.setMinimumWidth(400)

            # Apply theme styling based on current mode
            if self.__is_dark_mode:
                dialog_style = """
                    QDialog {
                        background-color: #1a1a1a;
                        border: 2px solid #2d2d2d;
                        border-radius: 10px;
                    }
                    QLabel {
                        color: #e8e8e8;
                        font-size: 13px;
                        background-color: transparent;
                        border: none;
                    }
                    QPushButton {
                        background-color: #2d2d2d;
                        border: 1px solid #404040;
                        border-radius: 6px;
                        padding: 8px 24px;
                        color: #e8e8e8;
                        font-size: 13px;
                        font-weight: 500;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;
                        border: 1px solid #505050;
                    }
                    QPushButton:pressed {
                        background-color: #242424;
                    }
                """
            else:
                dialog_style = """
                    QDialog {
                        background-color: #ffffff;
                        border: 2px solid #e0e0e0;
                        border-radius: 10px;
                    }
                    QLabel {
                        color: #000000;
                        font-size: 13px;
                        background-color: transparent;
                        border: none;
                    }
                    QPushButton {
                        background-color: #ff8c00;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 24px;
                        color: #ffffff;
                        font-size: 13px;
                        font-weight: 500;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #ff9d1a;
                    }
                    QPushButton:pressed {
                        background-color: #e67e00;
                    }
                """

            dialog.setStyleSheet(dialog_style)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing notification: {e}", exc_info=True)

    @pyqtSlot(str, str)
    def perform_clipboard_copy(self, type_label: str, content: str):
        """Thực hiện copy nội dung vào clipboard hệ thống (UI task)."""
        if content:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(content)

    @pyqtSlot(str)
    def create_remote_widget_in_main_thread(self, session_id: str):
        """Tạo remote widget trong main thread để tránh thread conflicts."""
        try:
            from client.gui.remote_widget import RemoteWidget
            from client.managers.session_manager import SessionManager

            remote_widget = RemoteWidget(session_id)

            SessionManager._sessions[session_id].widget = remote_widget

            self.controller.connect_button_state_changed.emit(True, "")

            remote_widget.show()
            remote_widget.raise_()
            remote_widget.activateWindow()

            logger.debug(f"Remote widget created in main thread: {session_id}")

        except Exception as e:
            logger.error(
                f"Error creating remote widget in main thread: {e}", exc_info=True
            )
            self.show_notification(f"Error creating remote window: {e}", "error")

    # ==========================================
    # Cleanup & Lifecycle
    # ==========================================

    def get_dark_theme_stylesheet(self):
        """Return dark theme stylesheet."""
        app_font_family = QApplication.font().family()
        return f"""
            QMainWindow {{
                background-color: #1a1a1a;
            }}
            QWidget {{
                background-color: #1a1a1a;
                color: #e8e8e8;
                font-family: '{app_font_family}', 'Courier New', monospace;
            }}
            QLabel {{
                color: #e8e8e8;
                background-color: transparent;
            }}
            QLabel#idLabel {{
                color: #ffd700 !important;
                background-color: transparent;
                font-size: 28px;
                font-weight: 600;
                letter-spacing: 2px;
            }}
            QLabel#passwordLabel {{
                color: #ffd700 !important;
                background-color: transparent;
                font-size: 20px;
                font-weight: 500;
                letter-spacing: 3px;
            }}
            QLabel#sectionHeader {{
                color: #ffffff !important;
                background-color: transparent;
                font-size: 24px;
                font-weight: 600;
                padding-bottom: 5px;
                letter-spacing: 0.2px;
            }}
            QLabel#infoText {{
                color: #9d9d9d !important;
                background-color: transparent;
                font-size: 14px;
                padding-bottom: 8px;
                letter-spacing: 0.3px;
            }}
            QLabel#titleLabel {{
                color: #9d9d9d !important;
                background-color: transparent;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            QLineEdit {{
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 12px 16px;
                color: #e8e8e8;
                font-size: 14px;
                selection-background-color: #ffd700;
                letter-spacing: 2px;
            }}
            QLineEdit:focus {{
                border: 2px solid #ffd700;
                background-color: #2d2d2d;
            }}  
            QLineEdit:hover {{
                border: 1px solid #4a4a4a;
            }}
            QLineEdit::placeholder {{
                color: #6a6a6a;
                letter-spacing: 2px;
            }}
            QPushButton {{
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 12px 24px;
                color: #e8e8e8;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
                border: 1px solid #505050;
            }}
            QPushButton:pressed {{
                background-color: #242424;
            }}
            QPushButton:disabled {{
                background-color: #1e1e1e;
                color: #6a6a6a;
                border: 1px solid #2d2d2d;
            }}
            QPushButton#connectBtn {{
                background-color: #ffd700;
                border: none;
                color: #1a1a1a;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton#connectBtn:hover {{
                background-color: #ffed4e;
            }}
            QPushButton#connectBtn:pressed {{
                background-color: #e6c200;
            }}
            QPushButton#copyBtn {{
                background-color: transparent;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
            }}
            QPushButton#copyBtn:hover {{
                background-color: #3a3a3a;
                border: 1px solid #ffd700;
            }}
            QPushButton#copyBtn:pressed {{
                background-color: #2a2a2a;
            }}
            QPushButton#refreshBtn {{
                background-color: transparent;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
                font-size: 18px;
            }}
            QPushButton#refreshBtn:hover {{
                background-color: #2d2d2d;
                border: 1px solid #ffd700;
            }}
            QPushButton#refreshBtn:pressed {{
                background-color: #2a2a2a;
            }}
            QPushButton#removeCustomBtn {{
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 6px;
            }}
            QPushButton#removeCustomBtn:hover {{
                background-color: #ff5555;
                border: 1px solid #ff5555;
            }}
            QPushButton#removeCustomBtn:pressed {{
                background-color: #e04444;
            }}
            QPushButton#setCustomBtn {{
                background-color: #ffd700;
                border: none;
                border-radius: 6px;
                color: #1a1a1a;
                font-size: 13px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton#setCustomBtn:hover {{
                background-color: #ffed4e;
            }}
            QPushButton#setCustomBtn:pressed {{
                background-color: #e6c200;
            }}
            QWidget#idDisplayContainer {{
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 8px;
            }}
            QWidget#passwordDisplayContainer {{
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 8px;
            }}
            QFrame {{
                background-color: #3e3e42;
            }}
        """

    def get_light_theme_stylesheet(self):
        """Return light theme stylesheet with white and orange colors."""
        app_font_family = QApplication.font().family()
        return f"""
            QMainWindow {{
                background-color: #fafafa;
            }}
            QWidget {{
                background-color: #fafafa;
                color: #000000;
                font-family: '{app_font_family}', 'Segoe UI', sans-serif;
            }}
            QWidget#sectionWidget {{
                background-color: #fafafa;
                border-radius: 12px;
                padding: 20px;
            }}
            QLabel {{
                color: #000000;
                background-color: transparent;
            }}
            QLabel#idLabel {{
                color: #ff8c00 !important;
                background-color: transparent;
                font-size: 28px;
                font-weight: 600;
                letter-spacing: 2px;
            }}
            QLabel#passwordLabel {{
                color: #ff6b00 !important;
                background-color: transparent;
                font-size: 20px;
                font-weight: 500;
                letter-spacing: 3px;
            }}
            QLabel#sectionHeader {{
                color: #1a1a1a !important;
                background-color: transparent;
                font-size: 24px;
                font-weight: 600;
                padding-bottom: 5px;
                letter-spacing: 0.2px;
            }}
            QLabel#infoText {{
                color: #4a4a4a !important;
                background-color: transparent;
                font-size: 14px;
                padding-bottom: 8px;
                letter-spacing: 0.3px;
            }}
            QLabel#titleLabel {{
                color: #666666 !important;
                background-color: transparent;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            QLineEdit {{
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px 16px;
                color: #000000;
                font-size: 14px;
                selection-background-color: #ff8c00;
                selection-color: #fafafa;
                letter-spacing: 2px;
            }}
            QLineEdit:focus {{
                border: 2px solid #ff8c00;
                background-color: #fafafa;
            }}  
            QLineEdit:hover {{
                border: 2px solid #ffb84d;
            }}
            QLineEdit::placeholder {{
                color: #999999;
                letter-spacing: 2px;
            }}
            QPushButton {{
                background-color: #f0f0f0;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px 24px;
                color: #000000;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #e8e8e8;
                border: 2px solid #ff8c00;
            }}
            QPushButton:pressed {{
                background-color: #d8d8d8;
            }}
            QPushButton:disabled {{
                background-color: #f5f5f5;
                color: #b0b0b0;
                border: 2px solid #efefef;
            }}
            QPushButton#connectBtn {{
                background-color: #ff8c00;
                border: none;
                color: #fafafa;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton#connectBtn:hover {{
                background-color: #ff9d1a;
            }}
            QPushButton#connectBtn:pressed {{
                background-color: #e67e00;
            }}
            QPushButton#connectBtn:disabled {{
                background-color: #ffd4a3;
                color: #fafafa;
            }}
            QPushButton#copyBtn {{
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
            }}
            QPushButton#copyBtn:hover {{
                background-color: #fff5e6;
                border: 2px solid #ff8c00;
            }}
            QPushButton#copyBtn:pressed {{
                background-color: #ffe5cc;
            }}
            QPushButton#refreshBtn {{
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 18px;
            }}
            QPushButton#refreshBtn:hover {{
                background-color: #fff5e6;
                border: 2px solid #ff8c00;
            }}
            QPushButton#refreshBtn:pressed {{
                background-color: #ffe5cc;
            }}
            QPushButton#removeCustomBtn {{
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
            }}
            QPushButton#removeCustomBtn:hover {{
                background-color: #ffe5e5;
                border: 2px solid #ff4444;
            }}
            QPushButton#removeCustomBtn:pressed {{
                background-color: #ffcccc;
            }}
            QPushButton#setCustomBtn {{
                background-color: #ff8c00;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton#setCustomBtn:hover {{
                background-color: #ff9d1a;
            }}
            QPushButton#setCustomBtn:pressed {{
                background-color: #ff6b00;
            }}
            QWidget#idDisplayContainer {{
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }}
            QWidget#passwordDisplayContainer {{
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }}
            QFrame {{
                background-color: #e0e0e0;
            }}
        """

    def toggle_theme(self):
        """Toggle between dark and light theme."""
        self.__is_dark_mode = not self.__is_dark_mode
        self.apply_theme()
        self.update_title_bar_style()
        self.update_window_control_icons()
        self.update_button_icons()
        self.update_custom_password_style()

        # Update theme button icon and tooltip
        if self.__is_dark_mode:
            # Đang ở dark mode -> hiển thị icon night-mode
            self.theme_btn.setIcon(
                QIcon(
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "assets",
                        "images",
                        "night-mode.png",
                    )
                )
            )
            self.theme_btn.setToolTip("Dark Mode")
        else:
            # Đang ở light mode -> hiển thị icon light-mode
            self.theme_btn.setIcon(
                QIcon(
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "assets",
                        "images",
                        "light-mode.png",
                    )
                )
            )
            self.theme_btn.setToolTip("Light Mode")

    def is_dark_mode(self):
        """Return current theme state."""
        return self.__is_dark_mode

    def update_button_icons(self):
        """Update button icons based on current theme."""
        assets_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "images",
        )

        if self.__is_dark_mode:
            # Dark mode - use white icons (-night)
            icon_suffix = "night"
        else:
            # Light mode - use black icons (-light)
            icon_suffix = "light"

        # Update copy ID button icon
        if self.copy_id_btn:
            self.copy_id_btn.setIcon(
                QIcon(os.path.join(assets_path, f"copy-{icon_suffix}.svg"))
            )

        # Update copy password button icon
        if self.copy_pass_btn:
            self.copy_pass_btn.setIcon(
                QIcon(os.path.join(assets_path, f"copy-{icon_suffix}.svg"))
            )

        # Update refresh button icon
        if self.refresh_btn:
            self.refresh_btn.setIcon(
                QIcon(os.path.join(assets_path, f"refresh-{icon_suffix}.svg"))
            )

        # Update remove custom button icon
        if self.remove_custom_btn:
            self.remove_custom_btn.setIcon(
                QIcon(os.path.join(assets_path, f"close-{icon_suffix}.svg"))
            )

    def update_window_control_icons(self):
        """Update window control button icons based on current theme."""
        assets_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "images",
        )

        if self.__is_dark_mode:
            # Dark mode - sử dụng icon màu trắng (-night)
            icon_suffix = "night"
        else:
            # Light mode - sử dụng icon màu đen (-light)
            icon_suffix = "light"

        # Update minimize button icon
        if self.minimize_btn:
            self.minimize_btn.setIcon(
                QIcon(os.path.join(assets_path, f"minimize-{icon_suffix}.svg"))
            )

        # Update maximize button icon
        if self.maximize_btn:
            if self.__is_maximized:
                self.maximize_btn.setIcon(
                    QIcon(os.path.join(assets_path, f"unmaximize-{icon_suffix}.svg"))
                )
            else:
                self.maximize_btn.setIcon(
                    QIcon(os.path.join(assets_path, f"maximize-{icon_suffix}.svg"))
                )

        # Update close button icon
        if self.close_btn:
            self.close_btn.setIcon(
                QIcon(os.path.join(assets_path, f"close-{icon_suffix}.svg"))
            )

    def update_title_bar_style(self):
        """Update title bar style based on current theme."""
        if self.title_bar:
            if self.__is_dark_mode:
                self.title_bar.setStyleSheet(
                    """
                    QWidget {
                        background-color: #1a1a1a;
                    }
                    QLabel#titleBarLabel {
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: 400;
                        padding-left: 8px;
                    }
                """
                )
            else:
                self.title_bar.setStyleSheet(
                    """
                    QWidget {
                        background-color: #fafafa;
                    }
                    QLabel#titleBarLabel {
                        color: #000000;
                        font-size: 12px;
                        font-weight: 400;
                        padding-left: 8px;
                    }
                """
                )

    def apply_theme(self):
        """Apply the current theme to the window."""
        if self.__is_dark_mode:
            self.setStyleSheet(self.get_dark_theme_stylesheet())
        else:
            self.setStyleSheet(self.get_light_theme_stylesheet())

    # ==========================================
    # Cleanup & Lifecycle
    # ==========================================

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ chính."""
        if not self.__cleanup_done:
            self.cleanup()
        event.accept()

    def cleanup(self):
        """Dọn dẹp tài nguyên khi ứng dụng đóng."""
        if self.__cleanup_done:
            return

        logger.info("Cleaning up MainWindow...")
        self.__cleanup_done = True

        try:
            # Dọn dẹp controller (sẽ tự động gửi end session cho tất cả sessions)
            if self.controller:
                self.controller.cleanup()

            logger.info("MainWindow cleanup completed.")

        except Exception as e:
            logger.error(f"Error during MainWindow cleanup: {e}", exc_info=True)
