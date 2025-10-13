import logging

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

from client.controllers.remote_widget_controller import RemoteWidgetController
from common.packets import VideoStreamPacket, VideoConfigPacket
from common.h264 import H264Decoder

logger = logging.getLogger(__name__)


class RemoteWidget(QWidget):
    disconnect_requested = pyqtSignal(str)  # Emit session_id when disconnect

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.original_width = 0
        self.original_height = 0
        self.full_screen_pixmap = None
        self.controller = RemoteWidgetController(self, self.session_id)

        # Track cleanup state
        self._cleanup_done = False
        self.decoder = None
        self.frame_count = 0

        self._cleanup_done = False

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.create_control_toolbar(main_layout)
        self.create_screen_area(main_layout)
        self.create_status_area(main_layout)

        # Set window title with session ID
        self.setWindowTitle(f"Remote Desktop - Session: {self.session_id}")

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
        self.disconnect_btn.clicked.connect(
            lambda: self.disconnect_requested.emit(self.session_id)
        )
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

    def handle_video_config_packet(self, packet: VideoConfigPacket):
        """
        Nhận config packet và khởi tạo decoder.
        Được gọi TRƯỚC khi nhận video frames.
        """
        try:
            self.original_width = packet.width
            self.original_height = packet.height

            self.decoder = H264Decoder(extradata=packet.extradata)

            # Update UI
            self.info_label.setText(
                f"Resolution: {packet.width}x{packet.height} | "
                f"FPS: {packet.fps} | Codec: {packet.codec.upper()}"
            )
            self.status_label.setText("🎥 Streaming")

        except Exception as e:
            logger.error(f"Error initializing decoder: {e}", exc_info=True)
            self.show_error(f"Decoder init failed: {e}")

    def handle_video_stream_packet(self, packet: VideoStreamPacket):
        """
        Nhận video packet, decode và hiển thị.
        """
        try:
            if not self.decoder:
                logger.warning("Received video packet but decoder not initialized!")
                self.show_error("Decoder not ready")
                return

            pil_image = self.decoder.decode(packet.video_data)

            if not pil_image:
                logger.debug("No image decoded (might be B-frame)")
                return

            self.frame_count += 1

            # Convert PIL Image → QPixmap
            # PIL RGB → QImage
            img_data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(
                img_data,
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format.Format_RGB888,
            )

            # QImage → QPixmap
            self.full_screen_pixmap = QPixmap.fromImage(qimage)

            # Display
            self.update_display()

            # Update stats mỗi 30 frames
            if self.frame_count % 30 == 0:
                logger.debug(f"Decoded {self.frame_count} frames")

        except Exception as e:
            logger.error(f"Error handling video packet: {e}", exc_info=True)
            self.show_error(f"Decode error: {e}")

    # def handle_full_image_packet(self, packet):
    #     """Legacy method - redirect to video stream handler"""
    #     # For backward compatibility
    #     pass

    # def handle_frame_update_packet(self, packet):
    #     """Legacy method - redirect to video stream handler"""
    #     # For backward compatibility
    #     pass

    def update_display(self):
        """Update display với frame mới."""
        if not self.full_screen_pixmap:
            return
        self.fit_to_screen()

    def fit_to_screen(self):
        """Fit image to window size."""
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
        """Display at actual size."""
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
        """Toggle fullscreen."""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("🔲 Fullscreen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("🔳 Exit Fullscreen")

    def show_error(self, message):
        """Show error message."""
        self.image_label.clear()
        self.image_label.setText(f"❌ Error: {message}")
        self.status_label.setText("⚠️ Connection Error")

    def show_waiting(self):
        """Show waiting message."""
        self.image_label.clear()
        self.image_label.setText("🖥️ Waiting for remote screen...")
        self.status_label.setText("🔗 Connected - Waiting")

    def show_disconnected(self):
        """Show disconnected message."""
        self.image_label.clear()
        self.image_label.setText("❌ Disconnected")
        self.status_label.setText("❌ Disconnected")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                self.fullscreen_btn.setText("🔲 Fullscreen")
            else:
                self.disconnect_requested.emit(self.session_id)
        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_F:
            self.fit_to_screen()
        elif event.key() == Qt.Key.Key_A:
            self.actual_size()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close."""
        if not self._cleanup_done:
            self.disconnect_requested.emit(self.session_id)
            self.cleanup()
        event.accept()

    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        if self.full_screen_pixmap and hasattr(self, "fit_screen_btn"):
            self.fit_to_screen()

    def cleanup(self):
        """Clean up resources."""
        if self._cleanup_done:
            return

        try:
            self._cleanup_done = True

            # Close decoder
            if self.decoder:
                logger.info(f"Closing decoder (decoded {self.frame_count} frames)")
                self.decoder.close()
                self.decoder = None

            # Cleanup controller
            if self.controller:
                self.controller.cleanup()

            self.full_screen_pixmap = None
            if hasattr(self, "image_label"):
                self.image_label.clear()

            logger.info(
                f"RemoteWidget cleanup completed for session: {self.session_id}"
            )

        except Exception as e:
            logger.error(f"Error during RemoteWidget cleanup: {e}")
