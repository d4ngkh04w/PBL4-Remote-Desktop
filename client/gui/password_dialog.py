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

    def __init__(self, parent=None):
        super().__init__(parent)

        # Remove window frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.setWindowTitle("Set Custom Password")
        self.setModal(True)
        self.setMinimumWidth(450)

        # Variables for window dragging
        self._drag_pos = QPoint()

        # Apply dark theme
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
            QFrame[frameShape="4"] {
                background-color: #3e3e42;
                max-height: 1px;
                border: none;
            }
        """
        )

        # Biến lưu mật khẩu
        self.password = ""

        self._setup_ui()

    def _setup_ui(self):
        """Thiết lập giao diện"""
        # Main layout container
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Add custom title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_label = QLabel("Set Custom Password")
        title_label.setStyleSheet(
            """
            font-size: 20px;
            font-weight: 600;
            color: #ffffff;
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
        desc_label.setStyleSheet(
            """
            color: #9d9d9d;
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
        self.password_input.textChanged.connect(self._on_text_changed)
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
        self.confirm_input.textChanged.connect(self._on_text_changed)
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
        self.cancel_button.setMinimumHeight(45)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton("Set Password")
        self.ok_button.setMinimumHeight(45)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setStyleSheet(
            """
            QPushButton:enabled {
                background-color: #ffd700;
                border: none;
                color: #1a1a1a;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:enabled:hover {
                background-color: #ffed4e;
            }
            QPushButton:enabled:pressed {
                background-color: #e6c200;
            }
            QPushButton:disabled {
                background-color: #1e1e1e;
                color: #6a6a6a;
                border: 1px solid #2d2d2d;
            }
        """
        )
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Add content layout to main layout
        main_layout.addLayout(layout)

        # Focus on first input
        self.password_input.setFocus()

    def _create_title_bar(self):
        """Tạo custom title bar cho dialog"""
        title_bar = QFrame()
        title_bar.setStyleSheet(
            """
            QFrame {
                background-color: #1a1a1a;
                border-bottom: 1px solid #2d2d2d;
            }
        """
        )
        title_bar.setFixedHeight(40)

        title_layout = QHBoxLayout(title_bar)
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
        title_text = QLabel("Set Custom Password")
        title_text.setStyleSheet(
            """
            color: #e8e8e8;
            font-size: 13px;
            font-weight: 500;
        """
        )
        title_layout.addWidget(title_text)

        title_layout.addStretch()

        # Close button
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
        close_btn.setIconSize(QSize(24, 24))
        close_btn.setStyleSheet(
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
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)

        # Make title bar draggable
        title_bar.mousePressEvent = self._title_bar_mouse_press
        title_bar.mouseMoveEvent = self._title_bar_mouse_move

        return title_bar

    def _title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _on_text_changed(self):
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

    def _on_ok_clicked(self):
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
