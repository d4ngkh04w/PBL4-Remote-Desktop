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
    QMessageBox,
    QApplication,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSlot, QSize, QPoint
from PyQt5.QtGui import QIcon

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

        # Dark theme stylesheet - Optimized
        self.setStyleSheet(
            f"""
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
            }}
            QLineEdit {{
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 12px 16px;
                color: #e8e8e8;
                font-size: 14px;
                selection-background-color: #ffd700;
            }}
            QLineEdit:focus {{
                border: 2px solid #ffd700;
                background-color: #2d2d2d;
            }}  
            QLineEdit:hover {{
                border: 1px solid #4a4a4a;
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
            QPushButton#refreshBtn {{
                background-color: transparent;
                border: 1px solid #404040;
                font-size: 18px;
            }}
            QPushButton#refreshBtn:hover {{
                background-color: #2d2d2d;
                border: 1px solid #505050;
            }}
        """
        )

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

    def create_title_bar(self):
        """Create custom title bar."""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet(
            """
            QWidget {
                background-color: #1a1a1a;
            }
        """
        )

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
        title_label.setStyleSheet(
            """
            color: #cccccc;
            font-size: 12px;
            font-weight: 400;
            padding-left: 8px;
        """
        )

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

        minimize_btn = QPushButton()
        minimize_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "minimize.svg",
                )
            )
        )
        minimize_btn.setToolTip("Minimize")
        minimize_btn.setIconSize(QSize(24, 24))
        minimize_btn.setStyleSheet(btn_style)
        minimize_btn.clicked.connect(self.showMinimized)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "maximize.svg",
                )
            )
        )
        self.maximize_btn.setIconSize(QSize(24, 24))
        self.maximize_btn.setStyleSheet(btn_style)
        self.maximize_btn.clicked.connect(self.toggle_maximize)

        close_btn = QPushButton()
        close_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "close.svg",
                )
            )
        )
        close_btn.setToolTip("Close")
        close_btn.setIconSize(QSize(24, 24))
        close_btn.setStyleSheet(
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
        close_btn.clicked.connect(self.close)

        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(self.maximize_btn)
        title_layout.addWidget(close_btn)

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
        if self.__is_maximized:
            self.showNormal()
            self.__is_maximized = False
            if self.maximize_btn:
                self.maximize_btn.setIcon(
                    QIcon(
                        os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "assets",
                            "images",
                            "maximize.svg",
                        )
                    )
                )
                self.maximize_btn.setToolTip("Maximize")
        else:
            self.showMaximized()
            self.__is_maximized = True
            if self.maximize_btn:
                self.maximize_btn.setIcon(
                    QIcon(
                        os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "assets",
                            "images",
                            "unmaximize.svg",
                        )
                    )
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
        your_section_layout = QVBoxLayout(your_section)
        your_section_layout.setSpacing(18)

        # Section header
        your_header = QLabel("Your Computer")
        your_header.setStyleSheet(
            """
            font-size: 24px;
            font-weight: 600;
            color: #ffffff;
            padding-bottom: 5px;
            letter-spacing: 0.2px;
        """
        )
        your_section_layout.addWidget(your_header)

        # Info text
        your_info = QLabel(
            "Share this ID and Password with others to allow them to connect to your computer"
        )
        your_info.setWordWrap(True)
        your_info.setStyleSheet(
            """
            font-size: 14px;
            color: #9d9d9d;
            padding-bottom: 8px;
            line-height: 1.5;
        """
        )
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
        id_title.setStyleSheet(
            """
            font-size: 13px;
            color: #9d9d9d;
            font-weight: 600;
            letter-spacing: 0.5px;
        """
        )

        # ID display with copy button inside
        id_display_container = QWidget()
        id_display_container.setStyleSheet(
            """
            QWidget {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 8px;
            }
        """
        )
        id_display_layout = QHBoxLayout(id_display_container)
        id_display_layout.setContentsMargins(20, 15, 15, 15)
        id_display_layout.setSpacing(10)

        self.id_label = QLabel("Connecting...")
        self.id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.id_label.setStyleSheet(
            """
            QLabel {
                background-color: transparent;
                border: none;
                font-size: 28px;
                font-weight: 600;
                color: #ffd700;
                letter-spacing: 2px;
            }
        """
        )

        copy_id_btn = QPushButton()
        copy_id_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "copy.png",
                )
            )
        )
        copy_id_btn.setIconSize(QSize(20, 20))
        copy_id_btn.setFixedSize(40, 40)
        copy_id_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #404040;
                border-radius: 6px;
                color: #9d9d9d;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #ffd700;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """
        )
        copy_id_btn.setToolTip("Copy ID")
        copy_id_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_id_btn.clicked.connect(self.controller.request_copy_id)

        id_display_layout.addWidget(self.id_label, 1)
        id_display_layout.addWidget(copy_id_btn)

        id_box_layout.addWidget(id_title)
        id_box_layout.addWidget(id_display_container)

        # Password box
        pass_box = QWidget()
        pass_box_layout = QVBoxLayout(pass_box)
        pass_box_layout.setSpacing(10)
        pass_box_layout.setContentsMargins(0, 0, 0, 0)

        pass_title = QLabel("Password")
        pass_title.setStyleSheet(
            """
            font-size: 13px;
            color: #9d9d9d;
            font-weight: 600;
            letter-spacing: 0.5px;
        """
        )

        # Password display with buttons inside
        password_display_container = QWidget()
        password_display_container.setStyleSheet(
            """
            QWidget {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 8px;
            }
        """
        )
        password_display_layout = QHBoxLayout(password_display_container)
        password_display_layout.setContentsMargins(20, 15, 15, 15)
        password_display_layout.setSpacing(10)

        self.password_label = QLabel("Loading...")
        self.password_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_label.setStyleSheet(
            """
            QLabel {
                background-color: transparent;
                border: none;
                font-size: 20px;
                font-weight: 500;
                color: #4ec9b0;
                letter-spacing: 3px;
            }
        """
        )

        # Button container
        button_container = QWidget()
        button_container.setStyleSheet("background-color: transparent; border: none;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        copy_pass_btn = QPushButton()
        copy_pass_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "copy.png",
                )
            )
        )
        copy_pass_btn.setIconSize(QSize(20, 20))
        copy_pass_btn.setFixedSize(40, 40)
        copy_pass_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #404040;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #ffd700;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """
        )
        copy_pass_btn.setToolTip("Copy Password")
        copy_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_pass_btn.clicked.connect(self.controller.request_copy_password)

        refresh_btn = QPushButton()
        refresh_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "reload.png",
                )
            )
        )
        refresh_btn.setIconSize(QSize(20, 20))
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #404040;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #ffd700;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """
        )
        refresh_btn.setToolTip("Refresh Password")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.controller.request_new_password)

        button_layout.addWidget(copy_pass_btn)
        button_layout.addWidget(refresh_btn)

        password_display_layout.addWidget(self.password_label, 1)
        password_display_layout.addWidget(button_container)

        pass_box_layout.addWidget(pass_title)
        pass_box_layout.addWidget(password_display_container)

        credentials_layout.addWidget(id_box, 3)
        credentials_layout.addWidget(pass_box, 2)

        your_section_layout.addWidget(credentials_container)

        # Custom Password Section
        custom_pass_container = QWidget()
        custom_pass_layout = QHBoxLayout(custom_pass_container)
        custom_pass_layout.setContentsMargins(0, 10, 0, 0)
        custom_pass_layout.setSpacing(20)

        set_custom_btn = QPushButton("Set Custom Password")
        set_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_custom_btn.setFixedHeight(36)
        set_custom_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ffd700;
                border: none;
                border-radius: 6px;
                color: #1a1a1a;
                font-size: 13px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #ffed4e;
            }
            QPushButton:pressed {
                background-color: #e6c200;
            }
        """
        )
        set_custom_btn.clicked.connect(self.on_set_custom_password_clicked)

        # Custom password display (ẩn, chỉ hiện khi đã có custom password)
        self.custom_password_display = QLineEdit()
        self.custom_password_display.setReadOnly(True)
        self.custom_password_display.setEchoMode(QLineEdit.EchoMode.Password)
        self.custom_password_display.setFixedHeight(36)
        self.custom_password_display.setFixedWidth(180)
        self.custom_password_display.setStyleSheet(
            """
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e8e8e8;
                font-size: 13px;
                letter-spacing: 2px;
            }
        """
        )
        self.custom_password_display.setPlaceholderText("Custom Password Set")

        # Nút xóa (icon close)
        remove_custom_btn = QPushButton()
        remove_custom_btn.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "close.svg",
                )
            )
        )
        remove_custom_btn.setIconSize(QSize(16, 16))
        remove_custom_btn.setFixedSize(32, 32)
        remove_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_custom_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ff5555;
                border: 1px solid #ff5555;
            }
            QPushButton:pressed {
                background-color: #e04444;
            }
        """
        )
        remove_custom_btn.setToolTip("Remove Custom Password")
        remove_custom_btn.clicked.connect(
            self.controller.request_remove_custom_password
        )

        password_display_container = QWidget()
        password_display_layout = QHBoxLayout(password_display_container)
        password_display_layout.setContentsMargins(0, 0, 0, 0)
        password_display_layout.setSpacing(8)
        password_display_layout.addWidget(self.custom_password_display)
        password_display_layout.addWidget(remove_custom_btn)
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
        separator.setStyleSheet(
            """
            background-color: #3e3e42;
            max-height: 1px;
            border: none;
            margin: 10px 0;
        """
        )
        content_layout.addWidget(separator)

        # === CONNECT TO PARTNER SECTION ===
        partner_section = QWidget()
        partner_section_layout = QVBoxLayout(partner_section)
        partner_section_layout.setSpacing(18)

        # Section header
        partner_header = QLabel("Connect to Partner")
        partner_header.setStyleSheet(
            """
            font-size: 24px;
            font-weight: 600;
            color: #ffffff;
            padding-bottom: 5px;
            letter-spacing: 0.2px;
        """
        )
        partner_section_layout.addWidget(partner_header)

        # Info text
        partner_info = QLabel(
            "Enter your partner's ID and Password to control their computer"
        )
        partner_info.setWordWrap(True)
        partner_info.setStyleSheet(
            """
            font-size: 14px;
            color: #9d9d9d;
            padding-bottom: 8px;
            line-height: 1.5;
        """
        )
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
        partner_id_title.setStyleSheet(
            """
            font-size: 13px;
            color: #9d9d9d;
            font-weight: 600;
            letter-spacing: 0.5px;
        """
        )

        self.remote_id_input = QLineEdit()
        self.remote_id_input.setPlaceholderText("Enter 9-digit ID...")
        self.remote_id_input.setMaxLength(9)
        self.remote_id_input.setStyleSheet(
            """
            QLineEdit {
                min-height: 50px;
                font-size: 16px;
                font-weight: 500;
                letter-spacing: 1px;
            }
        """
        )

        id_input_layout.addWidget(partner_id_title)
        id_input_layout.addWidget(self.remote_id_input)

        # Partner Password input
        pass_input_box = QWidget()
        pass_input_layout = QVBoxLayout(pass_input_box)
        pass_input_layout.setSpacing(10)
        pass_input_layout.setContentsMargins(0, 0, 0, 0)

        partner_pass_title = QLabel("Password")
        partner_pass_title.setStyleSheet(
            """
            font-size: 13px;
            color: #9d9d9d;
            font-weight: 600;
            letter-spacing: 0.5px;
        """
        )

        self.remote_password_input = QLineEdit()
        self.remote_password_input.setPlaceholderText("Enter password...")
        self.remote_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_password_input.setStyleSheet(
            """
            QLineEdit {
                min-height: 50px;
                font-size: 16px;
                font-weight: 500;
            }
        """
        )

        pass_input_layout.addWidget(partner_pass_title)
        pass_input_layout.addWidget(self.remote_password_input)

        # Connect button
        connect_btn_box = QWidget()
        connect_btn_layout = QVBoxLayout(connect_btn_box)
        connect_btn_layout.setSpacing(10)
        connect_btn_layout.setContentsMargins(0, 0, 0, 0)

        connect_label = QLabel(" ")  # Spacer to align with inputs
        connect_label.setStyleSheet("font-size: 13px;")

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setMinimumHeight(50)
        self.connect_btn.setMinimumWidth(140)
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                font-size: 16px;
                min-height: 50px;
                border-radius: 8px;
            }
        """
        )
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
            msg_box = QMessageBox(self)
            msg_box.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
            )
            msg_box.setText(message)

            image_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "assets",
                "images",
            )

            # Set icon based on type
            if notif_type == "error":
                msg_box.setIconPixmap(
                    QIcon(os.path.join(image_path, "error.png")).pixmap(64, 64)
                )
            elif notif_type == "warning":
                msg_box.setIconPixmap(
                    QIcon(os.path.join(image_path, "warning.png")).pixmap(64, 64)
                )
            else:
                msg_box.setIconPixmap(
                    QIcon(os.path.join(image_path, "info.png")).pixmap(64, 64)
                )

            # Apply dark theme styling
            msg_box.setStyleSheet(
                """
                QMessageBox {
                    background-color: #1a1a1a;
                    color: #e8e8e8;
                    border: 2px solid #2d2d2d;
                    border-radius: 10px;
                    padding: 3px;
                    margin: -1px;
                }
                QMessageBox QLabel {
                    color: #e8e8e8;
                    font-size: 13px;
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
            )

            msg_box.exec()
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
