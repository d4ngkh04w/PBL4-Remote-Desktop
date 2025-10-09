from common.packets import (
    AssignIdPacket,
    ConnectionResponsePacket
)
from common.enums import Status
from client.controllers.main_window_controller import MainWindowController
from client.service.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

class ClientService:
    @classmethod
    def _handle_assign_id_packet(cls, packet: AssignIdPacket):
        if not hasattr(packet, "client_id"):
            logger.error("Invalid assign ID packet")
            return

        AuthService.set_client_id(packet.client_id)
        logger.debug(f"Assigned client ID: {packet.client_id}")
        MainWindowController.on_client_id_received()
    @classmethod
    def _handle_connection_response_packet(cls, packet: ConnectionResponsePacket):
        if not hasattr(packet, "connection_status"):
            logger.error("Invalid connection response packet")
            return

        if packet.connection_status == Status.RECEIVER_NOT_FOUND:
            logger.debug(f"Connection failed: {packet.message}")
            MainWindowController.on_ui_update_status("Connection failed: %s" % packet.message)
            
        elif packet.connection_status == Status.SERVER_FULL:
            logger.debug("Connection failed: Server is full")
            MainWindowController.on_ui_update_status("Connection failed: Server is full")
            