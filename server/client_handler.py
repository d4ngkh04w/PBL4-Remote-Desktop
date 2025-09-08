import socket
import ssl
import logging

from common.protocol import Protocol
from common.packet import (
    Packet,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    ResponseConnectionPacket,
    AuthenticationResultPacket,
    ImagePacket,
)

from server.client_manager import ClientManager
from server.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ClientHandler:

    @classmethod
    def handle(
        cls,
        client_socket: socket.socket | ssl.SSLSocket,
        client_id: str,
        client_addr: str,
    ):
        """Main handler loop cho client"""
        try:
            ClientManager.add_client(client_socket, client_id, client_addr)
            logger.info(f"Client {client_id} connected from {client_addr}")

            while True:
                packet = Protocol.receive_packet(client_socket)
                if not packet:
                    break
                cls.__relay_packet(packet, client_id)

        except Exception:
            pass
        finally:
            client_socket.close()
            session_id, _ = SessionManager.get_client_sessions(client_id)
            if session_id:
                SessionManager.end_session(session_id)
            ClientManager.remove_client(client_id)
            logger.info(f"Client {client_id} disconnected from {client_addr}")

    @classmethod
    def __relay_packet(
        cls,
        packet: Packet,
        client_id: str,
    ):
        """Chuyển tiếp gói tin đến client đích"""
        match packet:
            case RequestConnectionPacket():
                cls.__relay_request_connection(packet, client_id)
            case RequestPasswordPacket():
                cls.__relay_request_password(packet, client_id)
            case SendPasswordPacket():
                cls.__relay_send_password(packet, client_id)
            case AuthenticationResultPacket():
                cls.__relay_authentication_result(packet, client_id)
            case ImagePacket():
                cls.__relay_image_packet(packet, client_id)
            case _:
                logger.warning(
                    f"Unknown packet type from client {client_id}: {packet.__class__.__name__}"
                )

    @classmethod
    def __relay_request_connection(
        cls,
        packet: RequestConnectionPacket,
        controller_id: str,
    ):
        """Chuyển tiếp RequestConnectionPacket"""
        logger.info(f"Client {controller_id} requests connection to {packet.host_id}")
        # Kiểm tra trạng thái online của client đích
        if not ClientManager.is_client_online(packet.host_id):
            response = ResponseConnectionPacket(
                success=False, message=f"Target client {packet.host_id} is not online"
            )
            socket = ClientManager.get_client_socket(controller_id)
            if socket:
                Protocol.send_packet(socket, response)
                logger.debug(
                    f"Client {controller_id} connection to {packet.host_id} failed: Target offline"
                )
        else:
            target_socket = ClientManager.get_client_socket(packet.host_id)
            if target_socket:
                Protocol.send_packet(target_socket, packet)
                logger.debug(
                    f"Client {controller_id} connection request sent to {packet.host_id}"
                )

    @classmethod
    def __relay_request_password(cls, packet: RequestPasswordPacket, host_id: str):
        """Chuyển tiếp RequestPasswordPacket - Host yêu cầu password từ controller"""
        logger.debug(f"Host {host_id} requests password from controller")
        # Gửi yêu cầu mật khẩu đến controller
        controller_socket = ClientManager.get_client_socket(packet.controller_id)
        if controller_socket:
            Protocol.send_packet(controller_socket, packet)
            logger.debug(f"Password request sent to controller {packet.controller_id}")
        else:
            logger.warning(f"Controller {packet.controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            host_socket = ClientManager.get_client_socket(host_id)
            if host_socket:
                Protocol.send_packet(host_socket, response)

    @classmethod
    def __relay_send_password(cls, packet: SendPasswordPacket, controller_id: str):
        """Chuyển tiếp SendPasswordPacket - Controller gửi password đến host"""
        logger.debug(f"Client {controller_id} sends password")

        # Forward password đến host
        host_socket = ClientManager.get_client_socket(packet.host_id)
        if host_socket:
            Protocol.send_packet(host_socket, packet)
            logger.debug(f"Password sent to host {packet.host_id}")
        else:
            logger.warning(f"Host {packet.host_id} not found")
            response = ResponseConnectionPacket(
                success=False, message=f"Target host {packet.host_id} is not online"
            )
            controller_socket = ClientManager.get_client_socket(controller_id)
            if controller_socket:
                Protocol.send_packet(controller_socket, response)

    @classmethod
    def __relay_authentication_result(
        cls, packet: AuthenticationResultPacket, host_id: str
    ):
        """Xử lý kết quả xác thực từ host"""
        logger.debug(f"Host {host_id} authentication result: {packet.success}")

        if packet.success:
            # Tạo session nếu xác thực thành công
            try:
                session_id = SessionManager.create_session(
                    packet.controller_id, host_id
                )
                logger.debug(
                    f"Session {session_id} created for controller {packet.controller_id} and host {host_id}"
                )

            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                response = ResponseConnectionPacket(
                    success=False, message="Failed to create session"
                )
                host_socket = ClientManager.get_client_socket(host_id)
                controller_socket = ClientManager.get_client_socket(
                    packet.controller_id
                )
                if controller_socket:
                    Protocol.send_packet(controller_socket, response)
                if host_socket:
                    Protocol.send_packet(host_socket, response)
                return

        # Gửi kết quả xác thực đến controller
        controller_socket = ClientManager.get_client_socket(packet.controller_id)
        if controller_socket:
            Protocol.send_packet(controller_socket, packet)
            logger.debug(
                f"Authentication result sent to controller {packet.controller_id}: {packet.success}"
            )
        else:
            logger.warning(f"Controller {packet.controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            host_socket = ClientManager.get_client_socket(host_id)
            if host_socket:
                Protocol.send_packet(host_socket, response)

    @classmethod
    def __relay_image_packet(cls, packet: ImagePacket, host_id: str):
        """Chuyển tiếp ImagePacket từ host đến controller"""
        session_id, session_info = SessionManager.get_client_sessions(host_id)
        if not session_id or not session_info:
            logger.warning(f"No active session found for client {host_id}")
            return

        controller_id = session_info["controller_id"]
        controller_socket = ClientManager.get_client_socket(controller_id)
        if controller_socket:
            Protocol.send_packet(controller_socket, packet)
            logger.debug(
                f"Image packet from host {host_id} sent to controller {controller_id}"
            )
        else:
            logger.warning(
                f"Controller {controller_id} not found for session {session_id}"
            )
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            host_socket = ClientManager.get_client_socket(host_id)
            if host_socket:
                Protocol.send_packet(host_socket, response)
