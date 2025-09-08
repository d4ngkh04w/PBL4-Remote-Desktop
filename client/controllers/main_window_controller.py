from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal
from common.logger import logger
from common.packet import (
    Packet, RequestConnectionPacket, RequestPasswordPacket, SendPasswordPacket,
    AuthenticationResultPacket, ImagePacket, AssignIdPacket
)
from common.password_manager import PasswordManager
from common.utils import unformat_numeric_id, format_numeric_id


class MainWindowController(QObject):
    """
    Controller xử lý logic business cho MainWindow.
    Tách biệt hoàn toàn khỏi UI để dễ test và maintain.
    """

    # Signals để giao tiếp với main thread
    connection_request_received = pyqtSignal(
        str, str)  # controller_id, host_id

    def __init__(self, main_window, network_client, auth_manager):
        super().__init__()
        self.main_window = main_window
        self.network_client = network_client
        self.auth_manager = auth_manager

        # Setup network message handler
        self.network_client.on_message_received = self.handle_server_message

        # Connect signal to slot in main thread
        self.connection_request_received.connect(
            self.show_connection_request_dialog)    # ====== SERVER CONNECTION ======

    def connect_to_server(self):
        """Kết nối đến server để nhận ID"""
        try:
            if self.network_client.connect():
                self.main_window.status_bar.showMessage(
                    "Connected to server, waiting for ID...")
                logger.info("Connected to server, waiting for ID assignment")
            else:
                self.main_window.status_bar.showMessage(
                    "Failed to connect to server")
                self.show_connection_error()
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            self.show_connection_error()

    def show_connection_error(self):
        """Hiển thị lỗi kết nối server"""
        if self.main_window.id_display:
            self.main_window.id_display.setText("Connection Failed")
            self.main_window.id_display.setStyleSheet(
                """
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #dc3545;
                    background-color: #f8d7da;
                    border: 2px dashed #dc3545;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 5px;
                }
            """
            )
        # Disable controller tab if connection failed
        self.main_window.tabs.setTabEnabled(1, False)
        if self.main_window.password_display:
            self.main_window.password_display.setText(
                self.main_window.my_password)

    # ====== MESSAGE HANDLING ======
    def handle_server_message(self, packet: Packet):
        """Xử lý tin nhắn từ server - phân chia theo loại packet"""
        match packet:
            case AssignIdPacket():
                self.handle_host_assign_id(packet)
            case AuthenticationResultPacket():
                self.handle_controller_auth_response(packet)
            case RequestConnectionPacket():
                self.handle_host_connection_request(packet)
            case RequestPasswordPacket():
                self.handle_controller_password_request(packet)
            case SendPasswordPacket():
                self.handle_host_receive_password(packet)
            case ImagePacket(data):
                if self.main_window.remote_widget:
                    self.main_window.remote_widget.handle_image_packet(data)
            case _:
                logger.warning(
                    f"Unknown packet type: {packet.__class__.__name__}")

    # ====== HOST LOGIC ======
    def handle_host_assign_id(self, packet: AssignIdPacket):
        """Host: Nhận ID từ server"""
        if hasattr(packet, "client_id"):
            if self.main_window.id_display:
                self.main_window.id_display.setText(
                    format_numeric_id(packet.client_id))
            if self.main_window.status_bar:
                self.main_window.status_bar.showMessage(
                    "Ready - ID received from server")
            self.main_window.my_id = packet.client_id
            logger.info(f"Received ID: {packet.client_id}")
            # Enable controller tab when connected
            self.main_window.tabs.setTabEnabled(1, True)

    def handle_host_connection_request(self, packet: RequestConnectionPacket):
        """Host: Xử lý yêu cầu kết nối từ controller"""
        if hasattr(packet, "controller_id") and hasattr(packet, "host_id"):
            host_id = packet.host_id
            controller_id = packet.controller_id
            logger.info(f"Received connection request from: {controller_id}")

            # Emit signal để main thread hiển thị dialog
            self.connection_request_received.emit(
                str(controller_id), str(host_id))

    def show_connection_request_dialog(self, controller_id_str, host_id_str):
        """Hiển thị dialog trong main thread"""
        controller_id = controller_id_str
        host_id = host_id_str

        # Hiển thị hộp thoại chấp nhận hoặc từ chối kết nối
        reply = QMessageBox.question(
            self.main_window,
            "Connection Request",
            f"Controller with ID {format_numeric_id(controller_id)} wants to connect. Accept?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Gửi yêu cầu xác thực
            accept_connection_packet = RequestPasswordPacket(
                controller_id, host_id)
            self.network_client.send(accept_connection_packet)
            logger.info(
                f"Connection accepted for controller: {controller_id}")
        else:
            # Gửi phản hồi từ chối kết nối
            auth_packet = AuthenticationResultPacket(
                controller_id, False, "Connection refused by user")
            self.network_client.send(auth_packet)
            logger.info(
                f"Connection refused by user for controller: {controller_id}")

    def handle_host_receive_password(self, packet: SendPasswordPacket):
        """Host: Nhận và xác thực password từ controller"""
        if hasattr(packet, "password") and hasattr(packet, "controller_id"):
            received_password = packet.password
            controller_id = packet.controller_id
            logger.info(
                f"Received password from controller: {received_password}")

            # Xác thực password
            if received_password == self.main_window.my_password:
                auth_result_packet = AuthenticationResultPacket(
                    controller_id, True, "Authentication successful")
                self.network_client.send(auth_result_packet)
                logger.info("Password correct, authentication successful")
            else:
                auth_result_packet = AuthenticationResultPacket(
                    controller_id, False, "Incorrect password")
                self.network_client.send(auth_result_packet)
                logger.info("Password incorrect, authentication failed")

    # ====== CONTROLLER LOGIC ======
    def handle_controller_connect(self, host_id, password):
        """Controller: Gửi yêu cầu kết nối tới host"""
        # Validation
        if not host_id or not password:
            QMessageBox.warning(self.main_window, "Input Error",
                                "Please enter both Host ID and Password")
            return
        if len(host_id) != 9 or not host_id.isdigit():
            QMessageBox.warning(self.main_window, "Invalid ID",
                                "Host ID must be exactly 9 digits")
            return

        # Disable button during connection
        self.main_window.connect_btn.setEnabled(False)
        self.main_window.connect_btn.setText("🔄 Connecting...")

        try:
            connect_packet = RequestConnectionPacket(
                host_id, self.main_window.my_id)
            self.network_client.send(connect_packet)
            self.main_window.status_bar.showMessage(
                f"Connecting to Host ID: {host_id}")
            logger.info(f"Connection request sent for host: {host_id}")
        except Exception as e:
            logger.error(f"Error sending connect request: {e}")
            self.reset_connect_button()
            QMessageBox.critical(self.main_window, "Connection Error",
                                 f"Failed to send connection request: {str(e)}")

    def handle_controller_password_request(self, packet: RequestPasswordPacket):
        """Controller: Gửi password khi host yêu cầu"""
        if hasattr(packet, "host_id") and hasattr(packet, "controller_id"):
            host_id = packet.host_id
            controller_id = packet.controller_id
            logger.info(f"Received password request from host: {host_id}")

            # Gửi password đã nhập
            entered_password = self.main_window.host_pass_input.text().strip()
            logger.info(f"Entered password: {entered_password}")
            password_packet = SendPasswordPacket(
                host_id, controller_id, entered_password)
            self.network_client.send(password_packet)
            logger.info(
                f"Sent password: {entered_password} to host: {host_id}")

    def handle_controller_auth_response(self, packet: AuthenticationResultPacket):
        """Controller: Nhận phản hồi xác thực từ host"""
        if packet.success:
            self.on_connection_successful()
        else:
            error_msg = packet.message if packet.message else "Connection failed"
            self.show_connection_failed(error_msg)

    # ====== CONNECTION SUCCESS/FAILURE ======
    def on_connection_successful(self):
        """Xử lý khi kết nối thành công"""
        try:
            # TODO: Uncomment when RemoteWidget is ready
            # from client.gui.remote_widget import RemoteWidget
            # self.main_window.remote_widget = RemoteWidget(self.network_client)
            # tab_index = self.main_window.tabs.addTab(self.main_window.remote_widget, "🖥️ Remote Desktop")
            # self.main_window.tabs.setCurrentIndex(tab_index)

            # Update UI
            # self.main_window.connect_btn.setText("🔌 Disconnect")
            # self.main_window.connect_btn.clicked.disconnect()
            # self.main_window.connect_btn.clicked.connect(self.disconnect_from_partner)
            # self.main_window.connect_btn.setEnabled(True)

            self.main_window.statusBar().showMessage("✅ Connected - Remote desktop active")
            logger.info("Remote desktop connection established")

        except Exception as e:
            logger.error(f"Error creating remote widget: {e}")
            self.reset_connect_button()

    def show_connection_failed(self, error_message):
        """Hiển thị lỗi kết nối"""
        self.reset_connect_button()
        QMessageBox.critical(
            self.main_window, "Connection Failed", f"Failed to connect to partner:\n{error_message}"
        )
        self.main_window.statusBar().showMessage("❌ Connection failed")

    def disconnect_from_partner(self):
        """Ngắt kết nối khỏi partner"""
        if self.main_window.remote_widget:
            # Remove remote desktop tab
            for i in range(self.main_window.tabs.count()):
                if self.main_window.tabs.widget(i) == self.main_window.remote_widget:
                    self.main_window.tabs.removeTab(i)
                    break

            # Cleanup
            self.main_window.remote_widget.cleanup()
            self.main_window.remote_widget = None

        self.reset_connect_button()
        self.main_window.statusBar().showMessage("Disconnected from partner")
        logger.info("Disconnected from partner")

    def reset_connect_button(self):
        """Reset trạng thái nút kết nối"""
        self.main_window.connect_btn.setText("🔗 Connect to Partner")
        self.main_window.connect_btn.setEnabled(True)
        self.main_window.connect_btn.clicked.disconnect()
        self.main_window.connect_btn.clicked.connect(lambda: self.handle_controller_connect(
            self.main_window.host_id_input.text().strip(),
            self.main_window.host_pass_input.text().strip()
        ))

    # ====== PASSWORD MANAGEMENT ======
    def refresh_password(self):
        """Làm mới password"""
        self.main_window.my_password = PasswordManager.generate_password(6)
        if self.main_window.password_display:
            self.main_window.password_display.setText(
                self.main_window.my_password)
        if self.main_window.status_bar:
            self.main_window.status_bar.showMessage("Password refreshed", 2000)
        logger.info("Password refreshed")

    # ====== CLEANUP ======
    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        if hasattr(self.main_window, '_cleanup_done') and self.main_window._cleanup_done:
            logger.info("Cleanup already performed, skipping...")
            return

        try:
            logger.info("Starting cleanup process...")
            self.main_window._cleanup_done = True

            if self.main_window.remote_widget:
                logger.info("Cleaning up remote widget...")
                self.main_window.remote_widget.cleanup()

            if self.network_client:
                logger.info("Disconnecting from server...")
                self.network_client.disconnect()

            logger.info("MainWindow cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
