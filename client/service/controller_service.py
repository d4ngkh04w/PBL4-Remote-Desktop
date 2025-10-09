from client.network.socket_client import SocketClient
import logging
from client.controllers.main_window_controller import MainWindowController
from common.packets import (
    ConnectionRequestPacket,
    ConnectionResponsePacket,
)
from client.network.socket_client import SocketClient
from client.service.auth_service import AuthService
from common.enums import Status

logger = logging.getLogger(__name__)


class ControllerService:  
    @classmethod
    def send_connection_request(cls, receiver_id: str, receiver_password: str) -> bool:
        """Gửi yêu cầu kết nối đến host"""
        try:
            sender_id = AuthService.get_client_id()
            if sender_id == "":
                logger.error("Client ID is not assigned")
                return False
            request_packet = ConnectionRequestPacket(
                sender_id=sender_id, receiver_id=receiver_id, password=receiver_password
            )
            success = SocketClient.send_packet(request_packet)
            if success:
                logger.info("Connection request sent to host %s", receiver_id)
            else:
                logger.error("Failed to send connection request")            
        except Exception as e:
            logger.error("Error sending connection request: %s", e)
            return False
        return True

    @classmethod
    def _handle_connection_response_packet(cls, packet: ConnectionResponsePacket):
        if not hasattr(packet, "connection_status"):
            logger.error("Invalid connection response packet")
            return
        if packet.connection_status == Status.INVALID_PASSWORD:
            logger.debug("Connection failed: Invalid password")
            MainWindowController.on_ui_update_status("Connection failed: Invalid password")

    @classmethod
    def _handle_session_packet(cls, packet):
        pass
   


