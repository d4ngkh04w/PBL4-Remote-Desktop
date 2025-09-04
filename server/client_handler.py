import socket
import ssl
from common.protocol import Protocol
from common.packet import (
    Packet,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    ResponseConnectionPacket,
)
from common.logger import logger
from server.client_manager import ClientManager


class ClientHandler:
    __client_manager = ClientManager()

    @classmethod
    def handle(
        cls,
        client_socket: socket.socket | ssl.SSLSocket,
        client_id: str,
        client_addr: str,
    ):
        """Main handler loop cho client"""
        try:
            cls.__client_manager.add_client(client_socket, client_id, client_addr)
            logger.info(f"Client {client_id} connected from {client_addr}")

            while True:
                packet = Protocol.receive_packet(client_socket)
                if not packet:
                    break
                cls.__relay_packet(packet, client_id)

        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            client_socket.close()
            cls.__client_manager.remove_client(client_id)
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
            case _:
                logger.warning(
                    f"Unknown packet type from client {client_id}: {packet.__class__.__name__}"
                )

    @classmethod
    def __relay_request_connection(
        cls,
        packet: RequestConnectionPacket,
        client_id: str,
    ):
        """Chuyển tiếp RequestConnectionPacket"""
        logger.info(f"Client {client_id} requests connection to {packet.target_id}")
        # Kiểm tra trạng thái online của client đích
        if not cls.__client_manager.is_client_online(packet.target_id):
            response = ResponseConnectionPacket(
                success=False, message=f"Target client {packet.target_id} is not online"
            )
            socket = cls.__client_manager.get_client_socket(client_id)
            if socket:
                Protocol.send_packet(socket, response)
                logger.info(
                    f"Client {client_id} connection to {packet.target_id} failed: Target offline"
                )
        else:
            target_socket = cls.__client_manager.get_client_socket(packet.target_id)
            if target_socket:
                Protocol.send_packet(target_socket, packet)
                logger.info(
                    f"Client {client_id} connection request sent to {packet.target_id}"
                )

    @classmethod
    def __relay_request_password(cls, packet: RequestPasswordPacket, client_id: str):
        """Chuyển tiếp RequestPasswordPacket - Host yêu cầu password từ controller"""
        logger.info(f"Host {client_id} requests password from controller")
        # Gửi yêu cầu mật khẩu đến controller
        controller_socket = cls.__client_manager.get_client_socket(packet.controller_id)
        if controller_socket:
            Protocol.send_packet(controller_socket, packet)
            logger.info(f"Password request sent to controller {packet.controller_id}")
        else:
            logger.warning(f"Controller {packet.controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            host_socket = cls.__client_manager.get_client_socket(client_id)
            if host_socket:
                Protocol.send_packet(host_socket, response)

    @classmethod
    def __relay_send_password(cls, packet: SendPasswordPacket, client_id: str):
        """Chuyển tiếp SendPasswordPacket - Controller gửi password đến host"""
        logger.info(f"Client {client_id} sends password")

        # Forward password đến host
        host_socket = cls.__client_manager.get_client_socket(packet.host_id)
        if host_socket:
            Protocol.send_packet(host_socket, packet)
            logger.info(f"Password sent to host {packet.host_id}")
        else:
            logger.warning(f"Host {packet.host_id} not found")
            response = ResponseConnectionPacket(
                success=False, message=f"Target host {packet.host_id} is not online"
            )
            controller_socket = cls.__client_manager.get_client_socket(client_id)
            if controller_socket:
                Protocol.send_packet(controller_socket, response)
