from typing import Any
import logging
from common.packets import (
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    SessionPacket,
    AuthenticationPasswordPacket,
)
from common.enums import Status
from client.controllers.main_window_controller import MainWindowController
from client.managers.client_manager import ClientManager
from client.managers.connection_manager import ConnectionManager
import logging

logger = logging.getLogger(__name__)


class ControllerHandler:
    @staticmethod
    def send_connection_request(receiver_id: str, password: str):
        """Gửi ConnectionRequestPacket"""
        packet = ConnectionRequestPacket(
            sender_id=ClientManager.get_client_id(),
            receiver_id=receiver_id,
            password=password,
        )
        ConnectionManager.send_packet(packet)

    @staticmethod
    def handle_session_created(session_id: str):
        """Xử lý khi phiên kết nối được tạo thành công"""
        MainWindowController.on_create_remote_widget(session_id)
        
