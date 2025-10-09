from client.network.socket_client import SocketClient
import logging
from client.controllers.main_window_controller import MainWindowController
from common.packets import (
    ConnectionRequestPacket,
    AuthenticationPasswordPacket,
    ConnectionResponsePacket,
)
from common.enums import Status
from client.network.socket_client import SocketClient
from client.service.auth_service import AuthService

logger = logging.getLogger(__name__)


class HostService:
    @classmethod
    def _handle_connection_request_packet(cls, packet: ConnectionRequestPacket):
        """Xử lý gói tin yêu cầu kết nối từ controller"""
        if (
            not hasattr(packet, "receiver_id")
            or not hasattr(packet, "sender_id")
            or not hasattr(packet, "password")
        ):
            logger.error("Invalid request connection packet")
            return

        logger.debug("Received connection request from %s", packet.sender_id)

        authentication_password_packet = AuthenticationPasswordPacket(
            receiver_id=packet.sender_id
        )

        if not AuthService.verify_password(packet.password):
            authentication_password_packet.status = Status.INVALID_PASSWORD

        SocketClient.send_packet(authentication_password_packet)

        logger.debug(
            "Sent authentication password response to %s with status %s",
            packet.sender_id,
            authentication_password_packet.status,
        )

    @classmethod
    def _handle_session_packet(cls, packet):
        pass