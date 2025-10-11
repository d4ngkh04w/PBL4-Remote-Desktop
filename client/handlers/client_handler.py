from typing import Any
from client.handlers.controller_handler import ControllerHandler
from client.handlers.host_handler import HostHandler
from common.packets import (
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    SessionPacket,
)
from common.enums import Status
from client.managers.client_manager import ClientManager
from client.controllers.main_window_controller import MainWindowController
import logging
from client.managers.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ClientHandler:
    @classmethod
    def handle_received_packet(cls, packet: Any):
        """Phân loại và xử lý packet nhận được."""
        packet_handlers = {
            AssignIdPacket: cls._handle_assign_id_packet,
            ConnectionResponsePacket: cls._handle_connection_response_packet,
            SessionPacket: cls._handle_session_packet,
            ConnectionRequestPacket: HostHandler.handle_connection_request_packet,
        }
        handler = packet_handlers.get(type(packet))
        if handler:
            handler(packet)
        else:
            logger.warning(f"Unhandled packet type: {type(packet)}")

    @staticmethod
    def _handle_assign_id_packet(packet: AssignIdPacket):
        """Xử lý AssignIdPacket"""
        if not hasattr(packet, "client_id"):
            logger.error("Invalid assign ID packet")
            return
        if not packet.client_id:
            logger.error("Received AssignIdPacket with empty fields.")
            return
        ClientManager.set_client_id(packet.client_id)
        MainWindowController.update_id_display

    @staticmethod
    def _handle_connection_response_packet(packet: ConnectionResponsePacket):
        """Xử lý ConnectionResponsePacket"""
        if not hasattr(packet, "connection_status") or not hasattr(packet, "message"):
            logger.error("Invalid connection response packet")
            return

        if packet.connection_status == Status.INVALID_PASSWORD:
            MainWindowController.on_ui_show_notification(
                "Connection rejected: Invalid password.", "error"
            )
            MainWindowController.on_ui_update_status(
                "Connection rejected: Invalid password."
            )

        elif packet.connection_status == Status.SERVER_FULL:
            logger.info("Connection rejected: Server is full.")
            MainWindowController.on_ui_show_notification(
                "Connection rejected: Server is full.", "error"
            )
            MainWindowController.on_ui_update_status(
                "Connection rejected: Server is full."
            )

        elif packet.connection_status == Status.RECEIVER_NOT_FOUND:
            logger.info("Connection rejected: Receiver not found.")
            if packet.message:
                MainWindowController.on_ui_show_notification(packet.message, "error")
                MainWindowController.on_ui_update_status(packet.message)
            else:
                MainWindowController.on_ui_show_notification(
                    "Receiver not found.", "error"
                )
                MainWindowController.on_ui_update_status("Receiver not found.")

    @staticmethod
    def _handle_session_packet(packet: SessionPacket):
        """Xử lý SessionPacket"""
        if (
            not hasattr(packet, "status")
            or not hasattr(packet, "session_id")
            or not hasattr(packet, "role")
        ):
            logger.error("Invalid session packet")
            return
        if not packet.status or not packet.session_id or not packet.role:
            logger.error("Received SessionPacket with empty fields.")
            return
        if packet.status == Status.SUCCESS:
            SessionManager.add_session(packet.session_id, packet.role)
            if packet.role == "controller":
                ControllerHandler.handle_session_created(packet.session_id)
