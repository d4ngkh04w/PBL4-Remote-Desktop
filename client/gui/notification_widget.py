import logging
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class NotificationWidget(QWidget):
    """
    Custom notification widget that appears at bottom-right of screen
    Auto-closes after timeout or can be manually closed
    """

    def __init__(
        self,
        message: str,
        notification_type: str = "info",
        timeout: int = 5000,
        parent=None,
    ):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self.timeout = timeout

        self.init_ui()
        self.position_at_bottom_right()

        # Auto-close timer
        if timeout > 0:
            QTimer.singleShot(timeout, self.fade_out)

    def init_ui(self):
        """Initialize the notification UI"""
        # Window flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Fixed size
        self.setFixedSize(350, 80)

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 10, 10)
        main_layout.setSpacing(10)

        # Icon/Type indicator
        type_label = QLabel()
        type_label.setFixedSize(40, 40)
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.notification_type == "info":
            type_label.setText("ℹ")
            type_label.setStyleSheet(
                "color: #0078d4; font-size: 28px; font-weight: bold;"
            )
            border_color = "#0078d4"
        elif self.notification_type == "warning":
            type_label.setText("⚠")
            type_label.setStyleSheet(
                "color: #ff8c00; font-size: 28px; font-weight: bold;"
            )
            border_color = "#ff8c00"
        elif self.notification_type == "error":
            type_label.setText("✖")
            type_label.setStyleSheet(
                "color: #e81123; font-size: 24px; font-weight: bold;"
            )
            border_color = "#e81123"
        else:
            type_label.setText("✓")
            type_label.setStyleSheet(
                "color: #107c10; font-size: 28px; font-weight: bold;"
            )
            border_color = "#107c10"

        main_layout.addWidget(type_label)

        # Message text
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            "color: #000; font-size: 12px; font-weight: normal; background: transparent;"
        )
        font = QFont("Arial", 11)
        font.setWeight(QFont.Weight.Normal)
        message_label.setFont(font)
        main_layout.addWidget(message_label, 1)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: #666;
                border: none;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {border_color};
                color: white;
                border-radius: 3px;
            }}
        """
        )
        close_btn.clicked.connect(self.fade_out)
        main_layout.addWidget(close_btn)

        # Widget styling
        self.setStyleSheet(
            f"""
            NotificationWidget {{
                background-color: white;
                border: 2px solid {border_color};
                border-radius: 5px;
            }}
        """
        )

        # Set initial window opacity
        self.setWindowOpacity(1.0)

    def position_at_bottom_right(self):
        """Position the notification at bottom-right of screen"""
        from PyQt5.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = screen_geometry.width() - self.width() - 20
            y = screen_geometry.height() - self.height() - 20
            self.move(x, y)

    def fade_out(self):
        """Fade out animation before closing"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.finished.connect(self.close)
        self.animation.start()
