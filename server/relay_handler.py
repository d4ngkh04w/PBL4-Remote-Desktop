import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Callable
import socket
import ssl

from common.protocol import Protocol
from common.packet import (
    Packet,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    ResponseConnectionPacket,
    AuthenticationResultPacket,
    ImagePacket,
    SessionPacket,
    SessionAction,
)
from server.client_manager import ClientManager
from server.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RelayHandler:
    _thread_pool = ThreadPoolExecutor(max_workers=25, thread_name_prefix="RelayHandler")
    _packet_handlers: Dict[type, Callable] = {}
    _shutdown_called = False

    @classmethod
    def _initialize_handlers(cls):
        """Khởi tạo mapping giữa packet types và handlers"""
        if not cls._packet_handlers:
            cls._packet_handlers = {
                RequestConnectionPacket: cls._relay_request_connection,
                RequestPasswordPacket: cls._relay_request_password,
                SendPasswordPacket: cls._relay_send_password,
                AuthenticationResultPacket: cls._handle_authentication_result,
                ImagePacket: cls._relay_image_packet,
            }

    @staticmethod
    def relay_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        """Xử lý và chuyển tiếp gói tin sử dụng thread pool"""
        try:
            if isinstance(packet, ImagePacket):
                RelayHandler._thread_pool.submit(
                    RelayHandler._relay_image_packet, packet, sender_socket
                )
            else:
                RelayHandler._thread_pool.submit(
                    RelayHandler._process_packet, packet, sender_socket
                )

        except Exception as e:
            logger.error(f"Failed to submit packet for processing: {e}")

    @staticmethod
    def _process_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        try:
            RelayHandler._initialize_handlers()

            packet_type = type(packet)
            handler = RelayHandler._packet_handlers.get(packet_type)

            if handler:
                handler(packet, sender_socket)
            else:
                logger.warning(
                    f"Unknown packet type: {packet.packet_type} or sender not found"
                )
        except Exception as e:
            logger.error(f"Failed to submit packet for processing: {e}")

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên khi shutdown server"""
        if cls._shutdown_called:
            return

        cls._shutdown_called = True
        try:
            cls._thread_pool.shutdown(wait=True)
            logger.info("RelayHandler thread pool shutdown completed")
        except Exception as e:
            logger.error(f"Error during RelayHandler shutdown: {e}")

    @staticmethod
    def _send(packet: Packet, target_socket: socket.socket | ssl.SSLSocket) -> bool:
        """Gửi gói tin đến client đích"""
        if target_socket:
            send_lock = ClientManager.get_client_lock(target_socket)
            if send_lock:
                with send_lock:
                    try:
                        Protocol.send_packet(target_socket, packet)
                        return True
                    except (ConnectionError, BrokenPipeError) as e:
                        logger.warning(
                            f"Connection error while sending to target socket: {e}. Client might have disconnected."
                        )
                        return False
        return False

    @staticmethod
    def _relay_request_connection(
        packet: RequestConnectionPacket,
        controller_socket: socket.socket | ssl.SSLSocket,
    ):
        """Chuyển tiếp RequestConnectionPacket"""
        controller_id = packet.controller_id
        host_id = packet.host_id
        logger.info(f"Client {controller_id} requests connection to {host_id}")

        if not ClientManager.is_client_online(host_id):
            response = ResponseConnectionPacket(
                success=False, message=f"Target client {host_id} is not online"
            )

            if RelayHandler._send(response, controller_socket):
                logger.debug(
                    f"Client {controller_id} connection to {host_id} failed: Target offline"
                )
        else:
            host_socket = ClientManager.get_client_socket(host_id)
            if host_socket and RelayHandler._send(packet, host_socket):
                logger.debug(
                    f"Client {controller_id} connection request sent to {host_id}"
                )
            else:
                response = ResponseConnectionPacket(
                    success=False, message="Target host not found"
                )
                RelayHandler._send(response, controller_socket)

    @staticmethod
    def _relay_request_password(
        packet: RequestPasswordPacket,
        host_socket: socket.socket | ssl.SSLSocket,
    ):
        """Chuyển tiếp RequestPasswordPacket - Host yêu cầu password từ controller"""
        host_id = packet.host_id
        logger.debug(f"Host {host_id} requests password from controller")

        controller_socket = ClientManager.get_client_socket(packet.controller_id)
        if not controller_socket:
            logger.warning(f"Controller {packet.controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            RelayHandler._send(response, host_socket)
        else:
            if RelayHandler._send(packet, controller_socket):
                logger.debug(
                    f"Password request sent to controller {packet.controller_id}"
                )
            else:
                logger.warning(
                    f"Failed to send password request to controller {packet.controller_id}"
                )
                response = ResponseConnectionPacket(
                    success=False, message="Controller not available"
                )
                RelayHandler._send(response, host_socket)

    @staticmethod
    def _relay_send_password(
        packet: SendPasswordPacket,
        controller_socket: socket.socket | ssl.SSLSocket,
    ):
        """Chuyển tiếp SendPasswordPacket - Controller gửi password đến host"""
        controller_id = packet.controller_id
        logger.debug(f"Client {controller_id} sends password")

        host_socket = ClientManager.get_client_socket(packet.host_id)
        if not host_socket:
            logger.warning(f"Host {packet.host_id} not found")
            response = ResponseConnectionPacket(
                success=False, message=f"Target host {packet.host_id} is not online"
            )
            RelayHandler._send(response, controller_socket)
        else:
            if RelayHandler._send(packet, host_socket):
                logger.debug(f"Password sent to host {packet.host_id}")
            else:
                logger.warning(f"Failed to send password to host {packet.host_id}")
                response = ResponseConnectionPacket(
                    success=False, message=f"Target host {packet.host_id} is not online"
                )
                RelayHandler._send(response, controller_socket)

    @staticmethod
    def _handle_authentication_result(
        packet: AuthenticationResultPacket,
        host_socket: socket.socket | ssl.SSLSocket,
    ):
        """Chuyển tiếp AuthenticationResultPacket - Host gửi kết quả xác thực đến controller"""
        host_info = ClientManager.get_client_info(host_socket)
        if host_info is None:
            logger.warning(f"Host socket not found in client manager")
            return

        host_id = host_info["id"]

        logger.debug(f"Host {host_id} authentication result: {packet.success}")

        controller_socket = ClientManager.get_client_socket(packet.controller_id)
        if not controller_socket:
            logger.warning(f"Controller {packet.controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            RelayHandler._send(response, host_socket)
            return

        if packet.success:
            try:
                session_id = ""
                if not SessionManager.is_client_in_session(
                    host_id
                ) and not SessionManager.is_client_in_session(packet.controller_id):
                    session_id = SessionManager.create_session(
                        host_id=host_id, controller_id=packet.controller_id
                    )
                else:
                    if SessionManager.is_client_in_session(host_id):
                        response = ResponseConnectionPacket(
                            success=False,
                            message=f"Host {host_id} is already in a session",
                        )
                        RelayHandler._send(response, controller_socket)
                        return
                    if SessionManager.is_client_in_session(packet.controller_id):
                        response = ResponseConnectionPacket(
                            success=False,
                            message=f"Controller {packet.controller_id} is already in a session",
                        )
                        RelayHandler._send(response, host_socket)
                        return

                session_packet = SessionPacket(
                    session_id=session_id,
                    action=SessionAction.CREATED,
                )

                if not RelayHandler._send(session_packet, controller_socket):
                    logger.warning(f"Controller {packet.controller_id} not found")
                else:
                    logger.debug(
                        f"Session {session_id} creation notified to controller {packet.controller_id}"
                    )

                if not RelayHandler._send(session_packet, host_socket):
                    logger.warning(f"Host {packet.controller_id} not found")
                else:
                    logger.debug(
                        f"Session {session_id} creation notified to host {packet.controller_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                response = ResponseConnectionPacket(
                    success=False, message="Failed to create session"
                )

                RelayHandler._send(response, controller_socket)
                RelayHandler._send(response, host_socket)
                return
        else:
            if not RelayHandler._send(packet, controller_socket):
                logger.warning(f"Controller {packet.controller_id} not found")
                response = ResponseConnectionPacket(
                    success=False, message="Controller not available"
                )
                RelayHandler._send(response, host_socket)
            else:
                logger.debug(
                    f"Authentication result sent to controller {packet.controller_id}"
                )

    @staticmethod
    def _relay_image_packet(
        packet: ImagePacket, host_socket: socket.socket | ssl.SSLSocket
    ):
        """Chuyển tiếp ImagePacket từ host đến controller"""
        host_info = ClientManager.get_client_info(host_socket)
        if host_info is None:
            logger.warning(f"Host socket not found in client manager")
            return

        host_id = host_info["id"]
        session_id, session_info = SessionManager.get_client_sessions(host_id)
        if not session_info or not session_id:
            logger.warning(f"No active session found for host {host_id}")
            return

        controller_id = session_info["controller_id"]
        logger.debug(
            f"Relaying image packet from host {host_id} to controller {controller_id}"
        )

        controller_socket = ClientManager.get_client_socket(controller_id)
        if not controller_socket:
            logger.warning(f"Controller {controller_id} not found")
            return

        session_packet = SessionPacket(
            session_id=session_id,
            action=SessionAction.ENDED,
        )

        if not SessionManager.is_client_in_session(
            host_id
        ) or not SessionManager.is_client_in_session(controller_id):
            logger.warning(
                f"One of the clients is no longer in session, ending session {session_id}"
            )
            SessionManager.end_session(session_id)
            RelayHandler._send(session_packet, host_socket)
            RelayHandler._send(session_packet, controller_socket)
            return

        if not RelayHandler._send(packet, controller_socket):
            logger.warning(f"Controller {controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            RelayHandler._send(response, host_socket)
        else:
            logger.debug(f"Image packet relayed to controller {controller_id}")
