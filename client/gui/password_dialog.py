"""
Dialog để nhập mật khẩu tự đặt với xác nhận
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class PasswordDialog(QDialog):
    """Custom dialog để nhập và xác nhận mật khẩu"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Custom Password")
        self.setModal(True)
        self.setMinimumWidth(400)

        # Biến lưu mật khẩu
        self.password = ""

        self._setup_ui()

    def _setup_ui(self):
        """Thiết lập giao diện"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Set Custom Password")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Enter a custom password for remote connections.\nMinimum 6 characters required."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Password input
        password_label = QLabel("Password:")
        password_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter password (min 6 characters)")
        self.password_input.setMinimumHeight(35)
        self.password_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.password_input)

        # Confirm password input
        confirm_label = QLabel("Confirm Password:")
        confirm_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(confirm_label)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Re-enter password")
        self.confirm_input.setMinimumHeight(35)
        self.confirm_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.confirm_input)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 11px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton("Set Password")
        self.ok_button.setMinimumHeight(35)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setStyleSheet(
            """
            QPushButton:enabled {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """
        )
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Focus on first input
        self.password_input.setFocus()

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
            self.error_label.setText("⚠ Password must be at least 6 characters")
            self.ok_button.setEnabled(False)
            return

        if len(confirm) == 0:
            self.ok_button.setEnabled(False)
            return

        if password != confirm:
            self.error_label.setText("⚠ Passwords do not match")
            self.ok_button.setEnabled(False)
            return

        # All good
        self.error_label.setText("✓ Passwords match")
        self.error_label.setStyleSheet("color: green; font-size: 11px;")
        self.ok_button.setEnabled(True)

    def _on_ok_clicked(self):
        """Xử lý khi click OK"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        # Final validation
        if len(password) < 6:
            self.error_label.setText("⚠ Password must be at least 6 characters")
            self.error_label.setStyleSheet("color: red; font-size: 11px;")
            return

        if password != confirm:
            self.error_label.setText("⚠ Passwords do not match")
            self.error_label.setStyleSheet("color: red; font-size: 11px;")
            return

        self.password = password
        self.accept()

    def get_password(self) -> str:
        """Lấy mật khẩu đã nhập"""
        return self.password
