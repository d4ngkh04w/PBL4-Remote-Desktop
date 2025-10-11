from typing import Any
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


class HostHandler:
    @staticmethod
    def handle_connection_request_packet(packet: ConnectionRequestPacket):
        """Xử lý ConnectionRequestPacket"""

        if not hasattr (packet, 'password') or not hasattr(packet, 'sender_id'):
            logger.error("Invalid connection request packet")
            return

        if not packet.sender_id or not packet.password:
            logger.error("Received ConnectionRequestPacket with empty fields.")
            return

        if ClientManager.verify_password(packet.password):
            logger.debug(f"Connection request from {packet.sender_id} accepted.")
            authentication_password_packet = AuthenticationPasswordPacket(
                receiver_id=packet.sender_id,
                status=Status.SUCCESS,
            )
            ConnectionManager.send_packet(authentication_password_packet)

        else:
            logger.info(
                f"Connection request from {packet.sender_id} rejected due to wrong password."
            )
            response = ConnectionResponsePacket(
                connection_status=Status.INVALID_PASSWORD,
                message="Wrong password",
            )
            ConnectionManager.send_packet(response)
