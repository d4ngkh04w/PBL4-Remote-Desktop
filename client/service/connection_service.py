from client.network.socket_client import SocketClient
import logging
from client.controllers.main_window_controller import MainWindowController
from common.packets import (    
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    RequestPasswordPacket,
    SendPasswordPacket,
)
from common.enums import ConnectionStatus
from client.service.auth_service import get_client_id
from client.network.socket_client import SocketClient
from client.service.auth_service import AuthService

logger = logging.getLogger(__name__)


class ConnectionService:
    """Dịch vụ quản lý kết nối giữa các client (controller và host)"""

    @classmethod
    def _handle_response_connection_packet(cls, packet: ConnectionResponsePacket):
        """Xử lý gói tin phản hồi kết nối"""
        if not hasattr(packet, "connection_status") or not hasattr(packet, "message"):
            logger.error("Invalid response connection packet")
            return

        logger.info("Received connection response: %s", packet.message)

        if packet.connection_status == ConnectionStatus.SESSION_STARTED:
            MainWindowController.on_ui_update_status(
                {"message": "Connection established!", "type": "success"}
            )
            # Trigger session started event để controller tạo remote widget
            MainWindowController.on_connected_to_host(
                {
                    "controller_id": (
                        packet.controller_id
                        if hasattr(packet, "controller_id")
                        else None
                    ),
                    "host_id": packet.host_id if hasattr(packet, "host_id") else None,
                }
            )
        else:
            MainWindowController.on_ui_update_status(
                {"message": f"Connection error: {packet.message}", "type": "error"}
            )
            MainWindowController.on_disconnected_with_host({})

    # ====== Controller Methods ======
    @classmethod
    def send_connection_request(cls, host_id: str) -> bool:
        """Gửi yêu cầu kết nối đến host"""
        try:
            controller_id = get_client_id()
            if controller_id is None:
                logger.error("Client ID is not assigned")
                return False
            request_packet = ConnectionRequestPacket(
                controller_id=controller_id, host_id=host_id
            )
            success = SocketClient.send_packet(request_packet)
            if success:
                logger.info("Connection request sent to host %s", host_id)
            else:
                logger.error("Failed to send connection request")
            return success
        except Exception as e:
            logger.error("Error sending connection request: %s", e)
            return False

    @classmethod
    def _handle_request_password_packet(cls, packet: RequestPasswordPacket):
        """Xử lý gói tin yêu cầu xác thực password từ host"""
        if not hasattr(packet, "host_id") or not hasattr(packet, "controller_id"):
            logger.error("Invalid request password packet")
            return

        logger.debug("Received password_request from host %s", packet.host_id)

        controller_id = packet.controller_id
        host_id = packet.host_id
        password = MainWindowController.get_host_password()

        if password == "":
            logger.error("No password provided for authentication")
            return

        password_packet = SendPasswordPacket(
            controller_id=controller_id, host_id=host_id, password=password
        )
        SocketClient.send_packet(password_packet)

    # ====== Host Methods ======
    @classmethod
    def _handle_request_connection_packet(cls, packet: ConnectionRequestPacket):
        """Xử lý gói tin yêu cầu kết nối từ controller"""
        if not hasattr(packet, "controller_id") or not hasattr(packet, "host_id"):
            logger.error("Invalid request connection packet")
            return

        logger.debug(
            "Received connection request from controller %s", packet.controller_id
        )
        MainWindowController.on_ui_show_notification_suggestion(
            {
                "controller_id": packet.controller_id,
                "host_id": packet.host_id,
            }
        )

    @classmethod
    def _accept_connection_request(cls, controller_id, host_id):
        """Chấp nhận yêu cầu kết nối từ controller"""
        try:
            logger.debug(
                "Accepting connection request from controller %s", controller_id
            )
            request_password_packet = RequestPasswordPacket(
                controller_id=controller_id, host_id=host_id
            )
            SocketClient.send_packet(request_password_packet)
        except Exception as e:
            logger.error("Error accepting connection: %s", e)

    @classmethod
    def _reject_connection_request(cls, controller_id, host_id):
        """Từ chối yêu cầu kết nối từ controller"""
        try:
            logger.debug(
                "Rejecting connection request from controller %s", controller_id
            )
            response_packet = ConnectionResponsePacket(
                controller_id=controller_id,
                host_id=host_id,
                connection_status=ConnectionStatus.REJECTED,
                message="Connection rejected by host",
            )
            SocketClient.send_packet(response_packet)
            logger.info("Connection rejected for controller %s", controller_id)
        except Exception as e:
            logger.error("Error rejecting connection: %s", e)

    @classmethod
    def _handle_send_password_packet(cls, packet: SendPasswordPacket):
        """Xử lý gói tin gửi password"""
        logger.debug("Received send password packet")

        if (
            not hasattr(packet, "controller_id")
            or not hasattr(packet, "host_id")
            or not hasattr(packet, "password")
        ):
            logger.error("Invalid send password packet")
            return

        if AuthService.verify_password(packet.password):
            cls._handle_password_correct(
                {
                    "controller_id": packet.controller_id,
                    "host_id": packet.host_id,
                    "password": packet.password,
                }
            )
        else:
            cls._handle_password_incorrect(
                {
                    "controller_id": packet.controller_id,
                    "host_id": packet.host_id,
                    "password": packet.password,
                }
            )

    @classmethod
    def _handle_password_correct(cls, data):
        """Xử lý khi mật khẩu đúng"""
        try:
            logger.debug("Accepted password, sending authentication success")
            controller_id = data.get("controller_id")
            host_id = data.get("host_id")
            connectionResponsePacket = ConnectionResponsePacket(
                controller_id=controller_id,
                host_id=host_id,
                connection_status=ConnectionStatus.SUCCESS,
                message="Authentication successful",
            )
            SocketClient.send_packet(connectionResponsePacket)
            logger.debug("Sent authentication success to controller %s", controller_id)

        except Exception as e:
            logger.error("Error handling correct password: %s", e)

    @classmethod
    def _handle_password_incorrect(cls, data):
        """Xử lý khi mật khẩu sai"""
        try:
            logger.info("Password incorrect, sending authentication failure")
            controller_id = data.get("controller_id")
            host_id = data.get("host_id")
            connectionResponsePacket = ConnectionResponsePacket(
                controller_id=controller_id,
                host_id=host_id,
                connection_status=ConnectionStatus.INVALID_PASSWORD,
                message="Authentication failed",
            )
            SocketClient.send_packet(connectionResponsePacket)

        except Exception as e:
            logger.error("Error handling incorrect password: %s", e)


# ====== PUBLIC API FOR CLIENT CONNECTIONS ======


def send_connection_request(host_id: str) -> bool:
    """Send connection request to host"""
    return ConnectionService.send_connection_request(host_id)


def accept_connection_request(controller_id: str, host_id: str):
    """Accept connection request from controller"""
    ConnectionService._accept_connection_request(controller_id, host_id)


def reject_connection_request(controller_id: str, host_id: str):
    """Reject connection request from controller"""
    ConnectionService._reject_connection_request(controller_id, host_id)


class ConnectionServiceHandlers:
    """Public packet handlers for SocketClient to call"""

    @staticmethod
    def handle_connection_response_packet(packet: ConnectionResponsePacket):
        """Public method for handling connection response packet"""
        return ConnectionService._handle_response_connection_packet(packet)

    @staticmethod
    def handle_connection_request_packet(packet: ConnectionRequestPacket):
        """Public method for handling connection request packet"""
        return ConnectionService._handle_request_connection_packet(packet)

    @staticmethod
    def handle_request_password_packet(packet: RequestPasswordPacket):
        """Public method for handling request password packet"""
        return ConnectionService._handle_request_password_packet(packet)

    @staticmethod
    def handle_send_password_packet(packet: SendPasswordPacket):
        """Public method for handling send password packet"""
        return ConnectionService._handle_send_password_packet(packet)
