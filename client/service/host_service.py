import logging

from client.network.socket_client import SocketClient
from client.controllers.main_window_controller import MainWindowController
from common.packets import (
    ConnectionRequestPacket,
    AuthenticationPasswordPacket,
    ConnectionResponsePacket,
    SessionPacket,
)
from common.enums import Status
from client.service.auth_service import AuthService
from client.service.screen_share_servive import ScreenShareService
from common.config import Config

logger = logging.getLogger(__name__)


class HostService:
    screen_share_service: ScreenShareService = ScreenShareService(fps=Config.fps)

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
    def _handle_session_packet(cls, packet: SessionPacket):
        if packet.status == Status.SESSION_STARTED:
            cls.screen_share_service.start()
        elif packet.status == Status.SESSION_ENDED:
            cls.screen_share_service.stop()
