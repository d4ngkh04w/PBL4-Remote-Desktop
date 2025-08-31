#!/usr/bin/env python3
"""
Test UI đơn giản cho Remote Desktop Client
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SimpleTestUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Khởi tạo giao diện test đơn giản"""
        self.setWindowTitle("Remote Desktop Client - UI Test")
        self.setGeometry(200, 200, 800, 600)

        # Central widget với tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Host (Your ID)
        self.create_host_tab()

        # Tab 2: Controller (Connect to Partner)
        self.create_controller_tab()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("UI Test Mode - Ready")

        # Apply simple styling
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
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

    def create_host_tab(self):
        """Tab hiển thị ID của mình - Test Version"""
        host_widget = QWidget()
        layout = QVBoxLayout()

        # Title
        title = QLabel("Your Computer ID")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        # ID Display
        id_group = QGroupBox("Your ID")
        id_layout = QVBoxLayout()

        self.id_display = QLabel("123 456 789")
        self.id_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.id_display.setStyleSheet(
            """
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #0066cc;
                background-color: #f8f8f8;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            }
        """
        )
        id_layout.addWidget(self.id_display)
        id_group.setLayout(id_layout)
        layout.addWidget(id_group)

        # Password Display
        pass_group = QGroupBox("Password")
        pass_layout = QVBoxLayout()

        self.password_display = QLabel("abc123")
        self.password_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_display.setStyleSheet(
            """
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #009900;
                background-color: #f8f8f8;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                margin: 10px;
            }
        """
        )
        pass_layout.addWidget(self.password_display)
        pass_group.setLayout(pass_layout)
        layout.addWidget(pass_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 Refresh Password")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        )
        self.refresh_btn.clicked.connect(self.refresh_password)
        btn_layout.addWidget(self.refresh_btn)

        self.copy_id_btn = QPushButton("📋 Copy ID")
        self.copy_id_btn.setMinimumHeight(40)
        self.copy_id_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """
        )
        self.copy_id_btn.clicked.connect(self.copy_id)
        btn_layout.addWidget(self.copy_id_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        host_widget.setLayout(layout)
        self.tabs.addTab(host_widget, "🏠 Your ID")

    def create_controller_tab(self):
        """Tab kết nối đến partner - Test Version"""
        controller_widget = QWidget()
        layout = QVBoxLayout()

        # Title
        title = QLabel("Connect to Partner Computer")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        # Connect Section
        connect_group = QGroupBox("Enter Partner Information")
        connect_layout = QFormLayout()

        # Partner ID
        self.partner_id_input = QLineEdit()
        self.partner_id_input.setPlaceholderText("Enter Partner ID (e.g. 123456789)")
        self.partner_id_input.setMaxLength(9)
        self.partner_id_input.setStyleSheet(
            """
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
        """
        )
        connect_layout.addRow("Partner ID:", self.partner_id_input)

        # Password
        self.partner_pass_input = QLineEdit()
        self.partner_pass_input.setPlaceholderText("Enter Password")
        self.partner_pass_input.setEchoMode(QLineEdit.Password)
        self.partner_pass_input.setStyleSheet(
            """
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
        """
        )
        connect_layout.addRow("Password:", self.partner_pass_input)

        # Connect Button
        self.connect_btn = QPushButton("🔗 Connect to Partner")
        self.connect_btn.setMinimumHeight(50)
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton:pressed {
                background-color: #D84315;
            }
        """
        )
        self.connect_btn.clicked.connect(self.connect_to_partner)
        connect_layout.addRow("", self.connect_btn)

        connect_group.setLayout(connect_layout)
        layout.addWidget(connect_group)

        # Connection Status
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Ready to connect")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            """
            QLabel {
                padding: 10px;
                font-size: 14px;
                color: #666;
                background-color: #f5f5f5;
                border-radius: 4px;
            }
        """
        )
        status_layout.addWidget(self.status_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        layout.addStretch()
        controller_widget.setLayout(layout)
        self.tabs.addTab(controller_widget, "🎮 Control Partner")

    def refresh_password(self):
        """Test refresh password"""
        import random
        import string

        new_pass = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        self.password_display.setText(new_pass)
        QMessageBox.information(self, "Success", f"New password generated: {new_pass}")

    def copy_id(self):
        """Test copy ID"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.id_display.text().replace(" ", ""))
        QMessageBox.information(self, "Copied", "ID copied to clipboard!")

    def connect_to_partner(self):
        """Test connect to partner"""
        partner_id = self.partner_id_input.text().strip()
        password = self.partner_pass_input.text().strip()

        if not partner_id or not password:
            QMessageBox.warning(
                self, "Missing Information", "Please enter both Partner ID and Password"
            )
            self.status_label.setText("❌ Missing information")
            self.status_label.setStyleSheet(
                """
                QLabel {
                    padding: 10px;
                    font-size: 14px;
                    color: #d32f2f;
                    background-color: #ffebee;
                    border-radius: 4px;
                }
            """
            )
            return

        if len(partner_id) != 9 or not partner_id.isdigit():
            QMessageBox.warning(
                self, "Invalid ID", "Partner ID must be exactly 9 digits"
            )
            self.status_label.setText("❌ Invalid ID format")
            self.status_label.setStyleSheet(
                """
                QLabel {
                    padding: 10px;
                    font-size: 14px;
                    color: #d32f2f;
                    background-color: #ffebee;
                    border-radius: 4px;
                }
            """
            )
            return

        # Simulate connection
        self.status_label.setText("🔄 Connecting...")
        self.status_label.setStyleSheet(
            """
            QLabel {
                padding: 10px;
                font-size: 14px;
                color: #f57c00;
                background-color: #fff8e1;
                border-radius: 4px;
            }
        """
        )

        QMessageBox.information(
            self,
            "Test Mode",
            f"Would connect to Partner ID: {partner_id}\n"
            + f"With password: {password}\n\n"
            + "This is just a UI test!",
        )

        self.status_label.setText("✅ Connected (Test Mode)")
        self.status_label.setStyleSheet(
            """
            QLabel {
                padding: 10px;
                font-size: 14px;
                color: #2e7d32;
                background-color: #e8f5e8;
                border-radius: 4px;
            }
        """
        )


def main():
    """Test UI chính"""
    app = QApplication(sys.argv)
    app.setApplicationName("Remote Desktop Client - UI Test")

    # Create and show window
    window = SimpleTestUI()
    window.show()

    print("🎨 UI Test started!")
    print("📱 Window should be visible now")
    print("🔧 Test all buttons and inputs")

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
