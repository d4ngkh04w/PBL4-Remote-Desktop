import logging
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QFileDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class ChatWindow(QWidget):
    """
    Cửa sổ chat cho cả host và controller
    Hiển thị thông báo kết nối, chat messages, file transfers
    """

    # Signals
    send_chat_message = pyqtSignal(str)  # message
    send_file = pyqtSignal(str)  # file_path
    disconnect_requested = pyqtSignal()

    def __init__(
        self, parent=None, partner_hostname="Unknown", role="host", session_id=None
    ):
        super().__init__(parent)
        self.partner_hostname = partner_hostname
        self.role = role  # "host" or "controller"
        self.session_id = session_id  # Current session ID
        self.is_visible = True
        self.is_collapsed = False  # Collapsed state
        self.expanded_width = 600  # Store expanded width
        self.sessions_list_layout = None

        # Drag window variables
        self._drag_pos = None
        self._is_dragging = False

        self.init_ui()
        self.position_at_right()
        self.update_sessions_list()

    def init_ui(self):
        """Initialize the chat window UI"""
        # Remove window frame for custom styling and stay on top
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Set window properties
        self.setWindowTitle("Remote Desktop Chat")
        self.setFixedSize(600, 600)  # Wider to accommodate sidebar

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create main container
        self.main_container = QFrame()
        self.main_container.setObjectName("mainContainer")
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        main_layout.addWidget(self.main_container)

        # Collapse toggle button (separate top-level widget protruding outside)
        self.collapse_toggle_btn = QPushButton()
        self.collapse_toggle_btn.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.collapse_toggle_btn.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )
        self.collapse_toggle_btn.setFixedSize(30, 60)
        self.collapse_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_toggle_btn.setText("▶")
        self.collapse_toggle_btn.setToolTip("Collapse")
        self.collapse_toggle_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #000;
                color: #fff;
                border: 1px solid #333;
                border-right: none;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333;
            }
        """
        )
        self.collapse_toggle_btn.clicked.connect(self.toggle_collapse)
        self.collapse_toggle_btn.show()

        # Position will be updated in update_collapse_button_position()

        # Horizontal layout for sidebar and content
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Sidebar for sessions list
        self.sidebar = self.create_sidebar()
        h_layout.addWidget(self.sidebar)

        # Content area (will be hidden when minimized)
        self.content_area = QWidget()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        # Chat history area (scrollable)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.chat_scroll.setStyleSheet(
            """
            QScrollArea {
                border: 1px solid #ccc;
                background-color: #fff;
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background: #f5f5f5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #999;
            }
        """
        )

        # Chat content widget
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(5, 5, 5, 5)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_content)
        content_layout.addWidget(self.chat_scroll, 1)

        # Input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(5)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setStyleSheet(
            """
            QLineEdit {
                background-color: #fff;
                color: #000;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #666;
            }
        """
        )
        self.message_input.returnPressed.connect(self.on_send_message)
        input_layout.addWidget(self.message_input)

        # Send button
        send_btn = QPushButton("Send")
        send_btn.setFixedSize(60, 35)
        send_btn.setToolTip("Send message")
        send_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #000;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #333;
            }
            QPushButton:pressed {
                background-color: #555;
            }
        """
        )
        send_btn.clicked.connect(self.on_send_message)
        input_layout.addWidget(send_btn)

        content_layout.addWidget(input_container)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(5)

        # Send file button
        file_btn = QPushButton("Send File")
        file_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #fff;
                color: #000;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 8px 15px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """
        )
        file_btn.clicked.connect(self.on_send_file)
        action_layout.addWidget(file_btn)

        # Disconnect button
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #000;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #333;
            }
            QPushButton:pressed {
                background-color: #555;
            }
        """
        )
        disconnect_btn.clicked.connect(self.on_disconnect)
        action_layout.addWidget(disconnect_btn)

        content_layout.addLayout(action_layout)

        h_layout.addWidget(self.content_area)
        container_layout.addLayout(h_layout)

        # Add main container to layout
        main_layout.addWidget(self.main_container)

        # Apply simple black and white theme
        self.setStyleSheet(
            """
            #mainContainer {
                background-color: #fff;
                border: 2px solid #000;
                border-radius: 5px;
            }
        """
        )

    def position_at_right(self):
        """Position window at right side of screen"""
        from PyQt5.QtWidgets import QApplication

        screen = QApplication.primaryScreen().availableGeometry()
        # Use screen offset for multi-monitor and Linux compatibility
        x = screen.x() + screen.width() - self.width()
        y = screen.y() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def toggle_collapse(self):
        """Toggle between collapsed and expanded state"""
        if self.is_collapsed:
            # Expand
            self.expand_window()
        else:
            # Collapse
            self.collapse_window()

    def collapse_window(self):
        """Collapse window to edge"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve

        self.is_collapsed = True

        # Hide main container
        self.main_container.hide()

        # Change button text and tooltip
        self.collapse_toggle_btn.setText("◀")
        self.collapse_toggle_btn.setToolTip("Expand")

        # Get screen geometry
        screen = QApplication.primaryScreen().availableGeometry()

        # Animate to collapsed position - only button visible
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        start_rect = self.geometry()
        end_rect = self.geometry()
        # Move window completely off-screen (hide it)
        end_rect.moveLeft(screen.x() + screen.width())

        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.finished.connect(self.update_collapse_button_position)
        self.animation.start()

    def expand_window(self):
        """Expand window from edge"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve

        self.is_collapsed = False

        # Change button text and tooltip
        self.collapse_toggle_btn.setText("▶")
        self.collapse_toggle_btn.setToolTip("Collapse")

        # Get screen geometry
        screen = QApplication.primaryScreen().availableGeometry()

        # Animate to expanded width
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        start_rect = self.geometry()
        end_rect = self.geometry()
        end_rect.setWidth(self.expanded_width)
        end_rect.moveLeft(screen.x() + screen.width() - self.expanded_width)

        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)

        # Show main container and update button position after animation
        def on_expand_finished():
            self.main_container.show()
            self.update_collapse_button_position()

        self.animation.finished.connect(on_expand_finished)
        self.animation.start()

    def toggle_visibility(self):
        """Toggle chat window visibility"""
        if self.is_visible:
            self.hide()
            self.collapse_toggle_btn.hide()
            self.is_visible = False
        else:
            self.show()
            self.collapse_toggle_btn.show()
            self.position_at_right()
            self.is_visible = True

    def update_collapse_button_position(self):
        """Update collapse button position (protruding outside on left edge)"""
        if not self.isVisible():
            return

        # Position button just outside the left edge of the window
        # Use geometry() instead of frameGeometry() for Linux compatibility
        window_pos = self.geometry().topLeft()
        y = self.geometry().top() + (self.height() - 60) // 2  # 60 is button height
        x = window_pos.x() - 30  # 30px to the left of window

        self.collapse_toggle_btn.move(x, y)

    def showEvent(self, event):
        """Handle show event to position button correctly"""
        super().showEvent(event)
        self.collapse_toggle_btn.show()
        self.update_collapse_button_position()

    def hideEvent(self, event):
        """Handle hide event to hide button"""
        super().hideEvent(event)
        self.collapse_toggle_btn.hide()

    def closeEvent(self, event):
        """Handle close event to cleanup button"""
        self.collapse_toggle_btn.close()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        """Start dragging window"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Drag window"""
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            self.update_collapse_button_position()
            event.accept()

    def mouseReleaseEvent(self, event):
        """Stop dragging window"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

    def resizeEvent(self, event):
        """Handle resize event to reposition button"""
        super().resizeEvent(event)
        self.update_collapse_button_position()

    @pyqtSlot(str, str, float)
    def add_message(self, sender_role: str, message: str, timestamp: float = 0.0):
        """Add a chat message to the history"""
        if timestamp == 0.0:
            timestamp = datetime.now().timestamp()

        msg_widget = QFrame()
        msg_widget.setStyleSheet(
            """
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 5px;
            }
        """
        )
        msg_layout = QVBoxLayout(msg_widget)
        msg_layout.setContentsMargins(8, 5, 8, 5)
        msg_layout.setSpacing(3)

        # Header (sender and time)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Determine sender name based on role
        if sender_role == "controller":
            sender_name = self.partner_hostname if self.role == "host" else "You"
        else:  # sender_role == "host"
            sender_name = self.partner_hostname if self.role == "controller" else "You"

        sender_label = QLabel(sender_name)
        sender_label.setStyleSheet("color: #000; font-weight: bold;")
        sender_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(sender_label)

        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #666; font-size: 9px;")
        header_layout.addWidget(time_label)

        header_layout.addStretch()
        msg_layout.addLayout(header_layout)

        # Message content
        content_label = QLabel(message)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #000; font-size: 11px;")
        msg_layout.addWidget(content_label)

        # Insert before stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, msg_widget)

        # Auto scroll to bottom
        QTimer.singleShot(
            100,
            lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ),
        )

    @pyqtSlot(str, str, str)
    def add_file_transfer(self, filename: str, status: str, sender_role: str):
        """Add a file transfer item to the history"""
        file_widget = QFrame()
        file_widget.setStyleSheet(
            """
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
        """
        )
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(8, 5, 8, 5)
        file_layout.setSpacing(3)

        # Sender
        if sender_role == "controller":
            sender_name = self.partner_hostname if self.role == "host" else "You"
        else:  # sender_role == "host"
            sender_name = self.partner_hostname if self.role == "controller" else "You"

        sender_label = QLabel(sender_name)
        sender_label.setStyleSheet("color: #000; font-weight: bold;")
        sender_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        file_layout.addWidget(sender_label)

        # File info
        info_layout = QHBoxLayout()
        file_icon = QLabel("[File]")
        file_icon.setStyleSheet("color: #000; font-weight: bold;")
        info_layout.addWidget(file_icon)

        file_info = QLabel(filename)
        file_info.setWordWrap(True)
        file_info.setStyleSheet("color: #000; font-size: 11px;")
        info_layout.addWidget(file_info, 1)
        file_layout.addLayout(info_layout)

        # Status
        status_label = QLabel(status)
        if status == "Canceled":
            status_label.setStyleSheet("color: #000; font-size: 10px;")
        elif status == "File Sent":
            status_label.setStyleSheet("color: #000; font-size: 10px;")
        else:
            status_label.setStyleSheet("color: #000; font-size: 10px;")
        file_layout.addWidget(status_label)

        # Insert before stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, file_widget)

        # Auto scroll to bottom
        QTimer.singleShot(
            100,
            lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ),
        )

    def on_send_message(self):
        """Handle send message button click"""
        message = self.message_input.text().strip()
        if message:
            self.send_chat_message.emit(message)
            self.add_message(self.role, message)
            self.message_input.clear()

    def on_send_file(self):
        """Handle send file button click"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file để gửi", "", "All Files (*.*)"
        )
        if file_path:
            # Send file and get file_id for tracking
            from client.managers.session_manager import SessionManager
            from client.services.file_transfer_service import FileTransferService

            # Get session_id
            session_id = None
            for sid, session in SessionManager._sessions.items():
                if session.chat_window == self:
                    session_id = sid
                    break

            if session_id:
                file_id = FileTransferService.send_file(
                    session_id, file_path, self.role
                )
                if file_id:
                    filename = os.path.basename(file_path)
                    # Show in chat with file_id for tracking
                    self.show_file_sending(file_id, filename, self.role)

    @pyqtSlot(str, str, str)
    def show_file_sending(self, file_id: str, filename: str, sender_role: str):
        """Show file being sent (for sender side)"""
        # Create file widget for sender
        file_widget = QFrame()
        file_widget.setObjectName(f"file_{file_id}")
        file_widget.setStyleSheet(
            """
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
        """
        )
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(8, 5, 8, 5)
        file_layout.setSpacing(3)

        # Sender label
        sender_label = QLabel("You")
        sender_label.setStyleSheet("color: #000; font-weight: bold;")
        sender_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        file_layout.addWidget(sender_label)

        # File info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(5)
        file_icon = QLabel("📁")
        file_icon.setStyleSheet("color: #000; font-size: 14px;")
        info_layout.addWidget(file_icon)

        file_info = QLabel(filename)
        file_info.setWordWrap(True)
        file_info.setStyleSheet("color: #000; font-size: 10px; font-weight: bold;")
        info_layout.addWidget(file_info, 1)
        file_layout.addLayout(info_layout)

        # Status
        status_label = QLabel("Waiting for response...")
        status_label.setStyleSheet("color: #666; font-size: 9px;")
        file_layout.addWidget(status_label)

        # Insert before stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, file_widget)

        # Auto scroll to bottom
        QTimer.singleShot(
            100,
            lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ),
        )

    def on_disconnect(self):
        """Handle disconnect button click"""
        self.disconnect_requested.emit()

    def update_partner_name(self, hostname: str):
        """Update the partner hostname display"""
        self.partner_hostname = hostname

    @pyqtSlot(str, str, int, str)
    def show_file_accept_dialog(
        self, file_id: str, filename: str, filesize: int, sender_role: str
    ):
        """Show file transfer request in chat with Save/Cancel buttons"""
        # Determine sender name
        if sender_role == "controller":
            sender_name = self.partner_hostname if self.role == "host" else "You"
        else:  # sender_role == "host"
            sender_name = self.partner_hostname if self.role == "controller" else "You"

        # Format file size
        if filesize < 1024:
            size_str = f"{filesize} B"
        elif filesize < 1024 * 1024:
            size_str = f"{filesize / 1024:.1f} KB"
        else:
            size_str = f"{filesize / (1024 * 1024):.1f} MB"

        # Create file transfer widget with buttons
        file_widget = QFrame()
        file_widget.setObjectName(f"file_{file_id}")
        file_widget.setStyleSheet(
            """
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
        """
        )
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(8, 5, 8, 5)
        file_layout.setSpacing(5)

        # Sender
        sender_label = QLabel(sender_name)
        sender_label.setStyleSheet("color: #000; font-weight: bold;")
        sender_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        file_layout.addWidget(sender_label)

        # File info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(5)
        file_icon = QLabel("📁")
        file_icon.setStyleSheet("color: #000; font-size: 14px;")
        info_layout.addWidget(file_icon)

        file_info = QLabel(f"{filename}")
        file_info.setWordWrap(True)
        file_info.setStyleSheet("color: #000; font-size: 10px; font-weight: bold;")
        info_layout.addWidget(file_info, 1)
        file_layout.addLayout(info_layout)

        # File size
        size_label = QLabel(size_str)
        size_label.setStyleSheet("color: #666; font-size: 9px;")
        file_layout.addWidget(size_label)

        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # Save button
        save_btn = QPushButton("💾 Save")
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #000;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #333;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """
        )
        save_btn.clicked.connect(
            lambda: self._on_file_save(
                file_id, filename, filesize, sender_role, file_widget
            )
        )
        button_layout.addWidget(save_btn)

        # Cancel button
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #fff;
                color: #000;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            QPushButton:disabled {
                background-color: #eee;
                color: #999;
            }
        """
        )
        cancel_btn.clicked.connect(
            lambda: self._on_file_cancel(file_id, filename, sender_role, file_widget)
        )
        button_layout.addWidget(cancel_btn)

        file_layout.addLayout(button_layout)

        # Insert before stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, file_widget)

        # Auto scroll to bottom
        QTimer.singleShot(
            100,
            lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ),
        )

    def _on_file_save(
        self,
        file_id: str,
        filename: str,
        filesize: int,
        sender_role: str,
        widget: QFrame,
    ):
        """Handle Save button click"""
        # Disable buttons immediately to prevent double-click
        self._disable_file_buttons(widget)

        # Show file dialog to choose save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", filename, "All Files (*.*)"
        )

        if save_path:
            from client.handlers.send_handler import SendHandler
            from client.managers.session_manager import SessionManager

            # Get session_id
            session_id = None
            for sid, session in SessionManager._sessions.items():
                if session.chat_window == self:
                    session_id = sid
                    break

            if session_id:
                # Update transfer info with save_path
                session = SessionManager._sessions.get(session_id)
                if session:
                    transfer = session.pending_file_transfers.get(file_id)
                    if transfer:
                        transfer["save_path"] = save_path

                SendHandler.send_file_accept_packet(session_id, file_id)

                # Update widget to show "Receiving..."
                self._update_file_widget_status(
                    widget, filename, "Receiving...", sender_role
                )
        else:
            # User canceled save dialog - treat as reject
            self._on_file_cancel(file_id, filename, sender_role, widget)

    def _on_file_cancel(
        self, file_id: str, filename: str, sender_role: str, widget: QFrame
    ):
        """Handle Cancel button click"""
        # Disable buttons immediately to prevent double-click
        self._disable_file_buttons(widget)

        from client.handlers.send_handler import SendHandler
        from client.managers.session_manager import SessionManager

        # Get session_id
        session_id = None
        for sid, session in SessionManager._sessions.items():
            if session.chat_window == self:
                session_id = sid
                break

        if session_id:
            SendHandler.send_file_reject_packet(session_id, file_id)

            # Update widget to show "Rejected"
            self._update_file_widget_status(widget, filename, "Rejected", sender_role)

    def _disable_file_buttons(self, widget: QFrame):
        """Remove Save and Cancel buttons from the file widget"""
        layout = widget.layout()
        if layout and layout.count() > 3:
            # Button layout should be at index 3 (after sender, file info, size)
            button_layout_item = layout.takeAt(3)
            if button_layout_item:
                # Delete the button layout and all its widgets
                if button_layout_item.layout():
                    button_layout = button_layout_item.layout()
                    while button_layout.count():
                        item = button_layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    button_layout.deleteLater()
                elif button_layout_item.widget():
                    button_layout_item.widget().deleteLater()

    def _update_file_widget_status(
        self, widget: QFrame, filename: str, status: str, sender_role: str
    ):
        """Update file transfer widget to show only status (remove buttons)"""
        # Clear existing layout
        layout = widget.layout()
        if layout:
            # Remove all widgets except sender and file info
            while layout.count() > 2:
                item = layout.takeAt(2)
                if item.widget():
                    item.widget().deleteLater()

            # Add status label
            status_label = QLabel(status)
            status_label.setStyleSheet("color: #000; font-size: 10px;")
            layout.addWidget(status_label)

    @pyqtSlot(str, str)
    def update_file_transfer_status(self, file_id: str, status: str):
        """Update status of a file transfer by file_id"""
        # Find widget with matching file_id
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if (
                    isinstance(widget, QFrame)
                    and widget.objectName() == f"file_{file_id}"
                ):
                    # Found the widget, update its status
                    layout = widget.layout()
                    if layout:
                        # Remove button layout (should be at index 2)
                        while layout.count() > 2:
                            child_item = layout.takeAt(2)
                            if child_item.widget():
                                child_item.widget().deleteLater()
                            elif child_item.layout():
                                # Remove buttons from layout
                                while child_item.layout().count() > 0:
                                    btn_item = child_item.layout().takeAt(0)
                                    if btn_item.widget():
                                        btn_item.widget().deleteLater()

                        # Add status label
                        status_label = QLabel(status)
                        status_label.setStyleSheet("color: #000; font-size: 10px;")
                        layout.addWidget(status_label)
                    break

    def create_sidebar(self):
        """Create sidebar for sessions list"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(
            """
            #sidebar {
                background-color: #f5f5f5;
                border-right: 1px solid #ccc;
            }
        """
        )

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header
        header = QLabel("Máy tính bạn đang xem")
        header.setStyleSheet(
            """
            color: #000;
            font-size: 12px;
            font-weight: bold;
            padding: 5px 0px;
        """
        )
        layout.addWidget(header)

        # Sessions list container
        sessions_widget = QWidget()
        self.sessions_list_layout = QVBoxLayout(sessions_widget)
        self.sessions_list_layout.setSpacing(5)
        self.sessions_list_layout.setContentsMargins(0, 0, 0, 0)
        self.sessions_list_layout.addStretch()

        layout.addWidget(sessions_widget)
        layout.addStretch()

        return sidebar

    def update_sessions_list(self):
        """Update the sessions list"""
        if not self.sessions_list_layout:
            return

        # Clear existing items
        while self.sessions_list_layout.count() > 1:  # Keep stretch
            item = self.sessions_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from client.managers.session_manager import SessionManager

        sessions = SessionManager.get_all_sessions_info()

        if not sessions:
            no_sessions_label = QLabel("Không có kết nối")
            no_sessions_label.setStyleSheet("color: #999; font-size: 11px;")
            self.sessions_list_layout.insertWidget(0, no_sessions_label)
            return

        # Add session items
        for sid, info in sessions.items():
            session_btn = self.create_session_button(sid, info)
            self.sessions_list_layout.insertWidget(
                self.sessions_list_layout.count() - 1, session_btn
            )

    def create_session_button(self, session_id: str, info: dict):
        """Create a button for a session"""
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(40)

        # Create layout
        layout = QHBoxLayout(btn)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        # Role icon
        role = info.get("role", "unknown")
        icon_label = QLabel("🖥️" if role == "host" else "🎮")
        icon_label.setFixedWidth(20)

        # Partner name
        partner_name = info.get("partner_hostname", "Unknown")
        name_label = QLabel(partner_name)
        name_label.setStyleSheet("color: #000; font-size: 11px; font-weight: 500;")

        layout.addWidget(icon_label)
        layout.addWidget(name_label, 1)

        # Highlight current session
        if session_id == self.session_id:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #999;
                    border-radius: 4px;
                    text-align: left;
                }
            """
            )
        else:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #fff;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-color: #bbb;
                }
                QPushButton:pressed {
                    background-color: #e5e5e5;
                }
            """
            )

        btn.clicked.connect(lambda: self.switch_to_session(session_id))

        return btn

    def switch_to_session(self, session_id: str):
        """Switch to another session"""
        if session_id == self.session_id:
            return  # Already viewing this session

        from client.controllers.main_window_controller import main_window_controller

        main_window_controller.open_chat_for_session(session_id)

    def _reject_file(self, file_id: str, filename: str, sender_role: str):
        """Reject an incoming file"""
        from client.handlers.send_handler import SendHandler
        from client.managers.session_manager import SessionManager

        # Get session_id
        session_id = None
        for sid, session in SessionManager._sessions.items():
            if session.chat_window == self:
                session_id = sid
                break

        if session_id:
            SendHandler.send_file_reject_packet(session_id, file_id)
            # Update status in chat
            self.add_file_transfer(filename, "Rejected", sender_role)
