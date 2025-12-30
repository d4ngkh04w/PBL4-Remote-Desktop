import os

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
)
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QIcon


class PasswordDialog(QDialog):
    """Custom dialog để nhập và xác nhận mật khẩu"""

    def __init__(self, parent=None, is_dark_mode=True):
        super().__init__(parent)

        # Remove window frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.setWindowTitle("Set Custom Password")
        self.setModal(True)
        self.setMinimumWidth(450)

        # Variables for window dragging
        self.__drag_pos = QPoint()
        self.__is_dark_mode = is_dark_mode

        # UI references for theme updates
        self.title_bar = None
        self.title_text = None
        self.close_btn = None

        # Apply theme
        self.__apply_theme()

        # Biến lưu mật khẩu
        self.password = ""

        self.__setup_ui()

    def __apply_theme(self):
        """Apply theme based on dark mode setting."""
        if self.__is_dark_mode:
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a1a;
                    color: #e8e8e8;
                }
                QLabel {
                    color: #e8e8e8;
                }
                QLineEdit {
                    background-color: #2a2a2a;
                    border: 1px solid #404040;
                    border-radius: 6px;
                    padding: 12px 16px;
                    color: #e8e8e8;
                    font-size: 14px;
                    selection-background-color: #ffd700;
                    letter-spacing: 2px;
                }
                QLineEdit:focus {
                    border: 2px solid #ffd700;
                    background-color: #2d2d2d;
                }
                QLineEdit:hover {
                    border: 1px solid #4a4a4a;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    border-radius: 6px;
                    padding: 12px 24px;
                    color: #e8e8e8;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 1px solid #505050;
                }
                QPushButton:pressed {
                    background-color: #242424;
                }
                QPushButton:disabled {
                    background-color: #1e1e1e;
                    color: #6a6a6a;
                    border: 1px solid #2d2d2d;
                }
                QPushButton#okButton:enabled {
                    background-color: #ffd700;
                    border: none;
                    color: #1a1a1a;
                    font-weight: 600;
                    font-size: 14px;
                }
                QPushButton#okButton:enabled:hover {
                    background-color: #ffed4e;
                }
                QPushButton#okButton:enabled:pressed {
                    background-color: #e6c200;
                }
                QPushButton#okButton:disabled {
                    background-color: #1e1e1e;
                    color: #6a6a6a;
                    border: 1px solid #2d2d2d;
                }
                QFrame[frameShape="4"] {
                    background-color: #3e3e42;
                    max-height: 1px;
                    border: none;
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #fafafa;
                    color: #000000;
                }
                QLabel {
                    color: #000000;
                }
                QLineEdit {
                    background-color: #ffffff;
                    border: 2px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 12px 16px;
                    color: #000000;
                    font-size: 14px;
                    selection-background-color: #ff8c00;
                    letter-spacing: 2px;
                }
                QLineEdit:focus {
                    border: 2px solid #ff8c00;
                    background-color: #ffffff;
                }
                QLineEdit:hover {
                    border: 2px solid #ffb347;
                }
                QPushButton {
                    background-color: #ffffff;
                    border: 2px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 12px 24px;
                    color: #000000;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #fff5e6;
                    border: 2px solid #ff8c00;
                }
                QPushButton:pressed {
                    background-color: #ffe5cc;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #999999;
                    border: 2px solid #e0e0e0;
                }
                QPushButton#okButton:enabled {
                    background-color: #ff8c00;
                    border: none;
                    color: #ffffff;
                    font-weight: 600;
                    font-size: 14px;
                }
                QPushButton#okButton:enabled:hover {
                    background-color: #ff9d1a;
                }
                QPushButton#okButton:enabled:pressed {
                    background-color: #ff6b00;
                }
                QPushButton#okButton:disabled {
                    background-color: #f5f5f5;
                    color: #999999;
                    border: 2px solid #e0e0e0;
                }
                QFrame[frameShape="4"] {
                    background-color: #e0e0e0;
                    max-height: 1px;
                    border: none;
                }
            """
            )

    def __update_title_bar_style(self):
        """Update title bar style based on current theme."""
        if self.title_bar:
            if self.__is_dark_mode:
                self.title_bar.setStyleSheet(
                    """
                    QFrame {
                        background-color: #1a1a1a;
                        border-bottom: 1px solid #2a2a2a;
                    }
                """
                )
            else:
                self.title_bar.setStyleSheet(
                    """
                    QFrame {
                        background-color: #fafafa;
                        border-bottom: 1px solid #e0e0e0;
                    }
                """
                )

        if self.title_text:
            if self.__is_dark_mode:
                self.title_text.setStyleSheet(
                    "color: #e8e8e8; font-size: 13px; font-weight: 500;"
                )
            else:
                self.title_text.setStyleSheet(
                    "color: #000000; font-size: 13px; font-weight: 500;"
                )

        if self.close_btn:
            assets_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "assets",
                "images",
            )
            icon_suffix = "night" if self.__is_dark_mode else "light"
            self.close_btn.setIcon(
                QIcon(os.path.join(assets_path, f"close-{icon_suffix}.svg"))
            )

    def __setup_ui(self):
        """Thiết lập giao diện"""
        # Main layout container
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Add custom title bar
        title_bar = self.__create_title_bar()
        main_layout.addWidget(title_bar)

        # Content layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_label = QLabel("Set Custom Password")
        if self.__is_dark_mode:
            title_label.setStyleSheet(
                """
                font-size: 20px;
                font-weight: 600;
                color: #ffffff;
                margin-bottom: 5px;
            """
            )
        else:
            title_label.setStyleSheet(
                """
                font-size: 20px;
                font-weight: 600;
                color: #000000;
                margin-bottom: 5px;
            """
            )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Enter a custom password for remote connections.\nMinimum 6 characters required."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.__is_dark_mode:
            desc_label.setStyleSheet(
                """
                color: #9d9d9d;
                font-size: 13px;
                margin-bottom: 5px;
            """
            )
        else:
            desc_label.setStyleSheet(
                """
                color: #666666;
                font-size: 13px;
                margin-bottom: 5px;
            """
            )
        layout.addWidget(desc_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(
            """
            background-color: #3e3e42;
            max-height: 1px;
            border: none;
            margin: 5px 0;
        """
        )
        layout.addWidget(line)

        # Password input
        password_label = QLabel("Password:")
        password_label.setStyleSheet(
            """
            font-weight: 600;
            font-size: 13px;
            color: #9d9d9d;
            margin-top: 5px;
        """
        )
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password (min 6 characters)")
        self.password_input.setMinimumHeight(45)
        self.password_input.textChanged.connect(self.__on_text_changed)
        layout.addWidget(self.password_input)

        # Confirm password input
        confirm_label = QLabel("Confirm Password:")
        confirm_label.setStyleSheet(
            """
            font-weight: 600;
            font-size: 13px;
            color: #9d9d9d;
            margin-top: 5px;
        """
        )
        layout.addWidget(confirm_label)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Re-enter password")
        self.confirm_input.setMinimumHeight(45)
        self.confirm_input.textChanged.connect(self.__on_text_changed)
        layout.addWidget(self.confirm_input)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5555; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setMinimumHeight(45)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton("Set Password")
        self.ok_button.setObjectName("okButton")
        self.ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_button.setMinimumHeight(45)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.__on_ok_clicked)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Add content layout to main layout
        main_layout.addLayout(layout)

        # Focus on first input
        self.password_input.setFocus()

    def __create_title_bar(self):
        """Tạo custom title bar cho dialog"""
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(40)

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 0, 0, 0)
        title_layout.setSpacing(8)

        # App icon
        icon_label = QLabel()
        icon_label.setPixmap(
            QIcon(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets",
                    "images",
                    "icon.png",
                )
            ).pixmap(QSize(18, 18))
        )
        title_layout.addWidget(icon_label)

        # Title text
        self.title_text = QLabel("Set Custom Password")
        self.title_text.setStyleSheet("font-size: 13px; font-weight: 500;")
        title_layout.addWidget(self.title_text)

        title_layout.addStretch()

        # Close button
        self.close_btn = QPushButton()
        self.close_btn.setIconSize(QSize(24, 24))
        self.close_btn.setStyleSheet(
            """
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
                background-color: #e81123;
            }
            QPushButton:pressed {
                background-color: #c50f1f;
            }
        """
        )
        self.close_btn.clicked.connect(self.reject)
        title_layout.addWidget(self.close_btn)

        # Make title bar draggable
        self.title_bar.mousePressEvent = self.__title_bar_mouse_press
        self.title_bar.mouseMoveEvent = self.__title_bar_mouse_move

        # Update title bar style based on theme
        self.__update_title_bar_style()

        return self.title_bar

    def __title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.__drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def __title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for dragging"""
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and not self.__drag_pos.isNull()
        ):
            self.move(event.globalPos() - self.__drag_pos)
            event.accept()

    def __on_text_changed(self):
        """Xử lý khi text thay đổi - validate real-time"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        # Clear error
        self.error_label.setText("")

        # Validate
        if len(password) == 0:
            self.ok_button.setEnabled(False)
            return

        if len(password) < 6:
            self.error_label.setText("Password must be at least 6 characters")
            self.ok_button.setEnabled(False)
            return

        if len(confirm) == 0:
            self.ok_button.setEnabled(False)
            return

        if password != confirm:
            self.error_label.setText("Passwords do not match")
            self.ok_button.setEnabled(False)
            return

        # All good
        self.error_label.setText("Passwords match")
        self.error_label.setStyleSheet("color: #4ec9b0; font-size: 12px;")
        self.ok_button.setEnabled(True)

    def __on_ok_clicked(self):
        """Xử lý khi click OK"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        # Final validation
        if len(password) < 6:
            self.error_label.setText("Password must be at least 6 characters")
            self.error_label.setStyleSheet("color: #ff5555; font-size: 12px;")
            return

        if password != confirm:
            self.error_label.setText("Passwords do not match")
            self.error_label.setStyleSheet("color: #ff5555; font-size: 12px;")
            return

        self.password = password
        self.accept()

    def get_password(self) -> str:
        """Lấy mật khẩu đã nhập"""
        return self.password
