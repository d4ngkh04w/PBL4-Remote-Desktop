import lz4.frame as lz4

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, pyqtSignal
from client.network.network_client import NetworkClient


class RemoteWidget(QWidget):
    # Signals for remote control events
    disconnect_requested = pyqtSignal()

    def __init__(self, network_client: NetworkClient, parent=None):
        super().__init__(parent)
        self.network_client = network_client
        self.current_pixmap = None
        self.original_width = 0
        self.original_height = 0

        self.init_ui()

    def init_ui(self):
        """Initialize the remote desktop UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Control toolbar
        self.create_control_toolbar(main_layout)

        # Remote screen area
        self.create_screen_area(main_layout)

        # Status bar
        self.create_status_area(main_layout)

    def create_control_toolbar(self, parent_layout):
        """Create control toolbar with connection status and actions"""
        toolbar_group = QGroupBox("Remote Control")
        toolbar_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #0066cc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )

        toolbar_layout = QHBoxLayout(toolbar_group)
        toolbar_layout.setSpacing(10)

        # Connection status
        self.status_label = QLabel("🔗 Connected")
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }
        """
        )
        toolbar_layout.addWidget(self.status_label)

        # Spacer
        toolbar_layout.addStretch()

        # Control buttons
        self.fit_screen_btn = QPushButton("🔍 Fit to Screen")
        self.fit_screen_btn.setStyleSheet(self.get_button_style())
        self.fit_screen_btn.clicked.connect(self.fit_to_screen)
        toolbar_layout.addWidget(self.fit_screen_btn)

        self.actual_size_btn = QPushButton("📐 Actual Size")
        self.actual_size_btn.setStyleSheet(self.get_button_style())
        self.actual_size_btn.clicked.connect(self.actual_size)
        toolbar_layout.addWidget(self.actual_size_btn)

        self.disconnect_btn = QPushButton("❌ Disconnect")
        self.disconnect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 8px 15px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """
        )
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        toolbar_layout.addWidget(self.disconnect_btn)

        parent_layout.addWidget(toolbar_group)

    def create_screen_area(self, parent_layout):
        """Create scrollable screen area for remote desktop"""
        screen_group = QGroupBox("Remote Screen")
        screen_group.setStyleSheet(
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

        screen_layout = QVBoxLayout(screen_group)
        screen_layout.setContentsMargins(5, 5, 5, 5)

        # Scroll area for large screens
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: 1px solid #ced4da;
                background-color: #2c2c2c;
            }
        """
        )

        # Image label for displaying remote screen
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            """
            QLabel {
                background-color: #2c2c2c;
                color: #ffffff;
                font-size: 16px;
                padding: 20px;
                border: 2px dashed #6c757d;
                border-radius: 8px;
            }
        """
        )
        self.image_label.setText(
            "🖥️ Waiting for remote screen...\n\nThe host will start sharing their screen shortly."
        )
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Enable mouse events on image label
        self.image_label.setMouseTracking(True)

        self.scroll_area.setWidget(self.image_label)
        screen_layout.addWidget(self.scroll_area)

        parent_layout.addWidget(screen_group)

    def create_status_area(self, parent_layout):
        """Create status information area"""
        status_layout = QHBoxLayout()

        self.info_label = QLabel(
            "Resolution: Not connected | Quality: High | Latency: -- ms"
        )
        self.info_label.setStyleSheet(
            """
            QLabel {
                color: #6c757d;
                font-size: 12px;
                padding: 5px;
            }
        """
        )
        status_layout.addWidget(self.info_label)

        status_layout.addStretch()

        parent_layout.addLayout(status_layout)

    def get_button_style(self):
        """Get standard button style"""
        return """
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 8px 15px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """

    def handle_image_packet(self, packet):
        """Handle incoming image packet from remote host"""
        try:
            # Giải nén dữ liệu
            decompressed_data = lz4.decompress(packet.image_data)

            # Tạo QImage từ dữ liệu
            image = QImage.fromData(decompressed_data)

            if not image.isNull():
                self.current_pixmap = QPixmap.fromImage(image)

                # Lưu thông tin kích thước gốc để hiển thị chính xác
                self.original_width = (
                    packet.original_width
                    if packet.original_width > 0
                    else image.width()
                )
                self.original_height = (
                    packet.original_height
                    if packet.original_height > 0
                    else image.height()
                )

                self.update_display()

                # Update status info với kích thước gốc
                self.info_label.setText(
                    f"Resolution: {self.original_width}x{self.original_height} | "
                    f"Quality: High | Size: {len(packet.image_data)} bytes"
                )

                # Update connection status
                self.status_label.setText("🔗 Connected - Receiving")
                self.status_label.setStyleSheet(
                    """
                    QLabel {
                        color: #28a745;
                        font-weight: bold;
                        font-size: 14px;
                        padding: 5px;
                    }
                """
                )
            else:
                self.show_error("Failed to decode image data")
        except Exception as e:
            self.show_error(f"Error handling image: {str(e)}")

    def update_display(self):
        """Update the display with the current pixmap"""
        if not self.current_pixmap:
            return

        # Default to fit screen mode
        self.fit_to_screen()

    def fit_to_screen(self):
        """Fit image to screen size maintaining aspect ratio based on original resolution"""
        if not self.current_pixmap:
            return

        # Get available size (subtract some padding)
        available_size = self.scroll_area.size()
        available_size.setWidth(available_size.width() - 20)
        available_size.setHeight(available_size.height() - 20)

        # Scale dựa trên tỷ lệ giữa kích thước gốc và kích thước hiển thị
        if self.original_width > 0 and self.original_height > 0:
            # Tính tỷ lệ scale để ảnh fit vào available_size
            scale_x = available_size.width() / self.original_width
            scale_y = available_size.height() / self.original_height
            scale = min(scale_x, scale_y)  # Giữ tỷ lệ khung hình

            target_width = int(self.original_width * scale)
            target_height = int(self.original_height * scale)

            scaled_pixmap = self.current_pixmap.scaled(
                target_width,
                target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            # Fallback nếu không có thông tin kích thước gốc
            scaled_pixmap = self.current_pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def actual_size(self):
        """Show image at actual original size"""
        if not self.current_pixmap:
            return

        # Hiển thị với kích thước gốc thực tế (trước khi resize)
        if self.original_width > 0 and self.original_height > 0:
            scaled_pixmap = self.current_pixmap.scaled(
                self.original_width,
                self.original_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            # Fallback - hiển thị với kích thước hiện tại
            scaled_pixmap = self.current_pixmap

        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def show_error(self, message):
        """Show error message"""
        self.image_label.clear()
        self.image_label.setText(f"❌ Error: {message}")
        self.status_label.setText("⚠️ Connection Error")
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }
        """
        )

    def show_waiting(self):
        """Show waiting state"""
        self.image_label.clear()
        self.image_label.setText(
            "🖥️ Waiting for remote screen...\n\nThe host will start sharing their screen shortly."
        )
        self.status_label.setText("🔗 Connected - Waiting")

    def show_disconnected(self):
        """Show disconnected state"""
        self.image_label.clear()
        self.image_label.setText(
            "❌ Disconnected\n\nConnection to remote host has been lost."
        )
        self.status_label.setText("❌ Disconnected")
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }
        """
        )

    def resizeEvent(self, event):
        """Handle widget resize"""
        super().resizeEvent(event)
        # Auto-fit when window is resized
        if self.current_pixmap and self.fit_screen_btn:
            self.fit_to_screen()

    def cleanup(self):
        """Clean up resources when closing"""
        self.current_pixmap = None
        if hasattr(self, "image_label"):
            self.image_label.clear()
