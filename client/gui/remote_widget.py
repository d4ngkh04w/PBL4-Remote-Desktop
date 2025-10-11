import lz4.frame as lz4

from typing import Optional
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
from PyQt5.QtGui import QPixmap, QImage, QPainter
from PyQt5.QtCore import Qt, pyqtSignal
from common.packets import ImagePacket, FrameUpdatePacket


class RemoteWidget(QWidget):
    disconnect_requested = pyqtSignal()

    def __init__(self, network_client: Optional[SocketClient] = None, parent=None):
        super().__init__(parent)
        # With SocketClient as singleton, we don't need to store instance
        # Keep for backward compatibility but won't use it
        self.network_client = network_client
        self.original_width = 0
        self.original_height = 0
        self.full_screen_pixmap = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.create_control_toolbar(main_layout)
        self.create_screen_area(main_layout)
        self.create_status_area(main_layout)

    def create_control_toolbar(self, parent_layout):
        toolbar_group = QGroupBox("Remote Control")
        toolbar_layout = QHBoxLayout(toolbar_group)

        self.status_label = QLabel("🔗 Connected")
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addStretch()

        self.fit_screen_btn = QPushButton("🔍 Fit to Window")
        self.fit_screen_btn.clicked.connect(self.fit_to_screen)
        toolbar_layout.addWidget(self.fit_screen_btn)

        self.actual_size_btn = QPushButton("📐 Actual Size")
        self.actual_size_btn.clicked.connect(self.actual_size)
        toolbar_layout.addWidget(self.actual_size_btn)

        self.fullscreen_btn = QPushButton("🔲 Fullscreen")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        toolbar_layout.addWidget(self.fullscreen_btn)

        self.disconnect_btn = QPushButton("❌ Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        toolbar_layout.addWidget(self.disconnect_btn)

        parent_layout.addWidget(toolbar_group)

    def create_screen_area(self, parent_layout):
        screen_group = QGroupBox("Remote Screen")
        screen_layout = QVBoxLayout(screen_group)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("🖥️ Waiting for remote screen...")
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.scroll_area.setWidget(self.image_label)
        screen_layout.addWidget(self.scroll_area)
        parent_layout.addWidget(screen_group)

    def create_status_area(self, parent_layout):
        status_layout = QHBoxLayout()
        self.info_label = QLabel("Resolution: Not connected")
        status_layout.addWidget(self.info_label)
        status_layout.addStretch()
        parent_layout.addLayout(status_layout)

    def handle_full_image_packet(self, packet: ImagePacket):
        try:
            decompressed_data = lz4.decompress(packet.image_data)
            image = QImage.fromData(decompressed_data)
            if not image.isNull():
                self.full_screen_pixmap = QPixmap.fromImage(image)
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
                self.info_label.setText(
                    f"Resolution: {self.original_width}x{self.original_height}"
                )
                self.status_label.setText("🔗 Connected - Receiving")
        except Exception as e:
            self.show_error(f"Error handling image: {str(e)}")

    def handle_frame_update_packet(self, packet: FrameUpdatePacket):
        if self.full_screen_pixmap is None:
            return
        try:
            back_buffer = self.full_screen_pixmap.copy()
            painter = QPainter(back_buffer)
            for x, y, width, height, image_data in packet.chunks:
                decompressed_data = lz4.decompress(image_data)
                chunk_image = QImage.fromData(decompressed_data)
                if not chunk_image.isNull():
                    painter.drawImage(x, y, chunk_image)
            painter.end()
            self.full_screen_pixmap = back_buffer
            self.update_display()
        except Exception as e:
            print(f"Error handling frame update packet: {e}")

    def update_display(self):
        if not self.full_screen_pixmap:
            return
        self.fit_to_screen()

    def fit_to_screen(self):
        if not self.full_screen_pixmap:
            return
        available_size = self.scroll_area.size()
        available_size.setWidth(available_size.width() - 20)
        available_size.setHeight(available_size.height() - 20)
        scaled_pixmap = self.full_screen_pixmap.scaled(
            available_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def actual_size(self):
        if not self.full_screen_pixmap:
            return
        if self.original_width > 0 and self.original_height > 0:
            scaled_pixmap = self.full_screen_pixmap.scaled(
                self.original_width,
                self.original_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled_pixmap = self.full_screen_pixmap
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def toggle_fullscreen(self):
        """Toggle between fullscreen and normal window mode"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("🔲 Fullscreen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("🔳 Exit Fullscreen")

    def show_error(self, message):
        self.image_label.clear()
        self.image_label.setText(f"❌ Error: {message}")
        self.status_label.setText("⚠️ Connection Error")

    def show_waiting(self):
        self.image_label.clear()
        self.image_label.setText("🖥️ Waiting for remote screen...")
        self.status_label.setText("🔗 Connected - Waiting")

    def show_disconnected(self):
        self.image_label.clear()
        self.image_label.setText("❌ Disconnected")
        self.status_label.setText("❌ Disconnected")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                self.fullscreen_btn.setText("🔲 Fullscreen")
            else:
                self.disconnect_requested.emit()
        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_F:
            self.fit_to_screen()
        elif event.key() == Qt.Key.Key_A:
            self.actual_size()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.disconnect_requested.emit()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.full_screen_pixmap and hasattr(self, "fit_screen_btn"):
            self.fit_to_screen()

    def cleanup(self):
        self.full_screen_pixmap = None
        if hasattr(self, "image_label"):
            self.image_label.clear()
