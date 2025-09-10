import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Callable

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
    _thread_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="RelayHandler")
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
    def relay_packet(packet: Packet, sender_id: str):
        """Xử lý và chuyển tiếp gói tin sử dụng thread pool"""
        try:
            if isinstance(packet, ImagePacket):
                RelayHandler._thread_pool.submit(
                    RelayHandler._relay_image_packet, packet
                )
            else:
                RelayHandler._thread_pool.submit(
                    RelayHandler._process_packet, packet, sender_id
                )
        except Exception as e:
            logger.error(f"Failed to submit packet for processing: {e}")

    @staticmethod
    def _process_packet(packet: Packet, sender_id: str):
        """Xử lý packet"""
        try:
            RelayHandler._initialize_handlers()

            packet_type = type(packet)
            handler = RelayHandler._packet_handlers.get(packet_type)

            if handler:
                handler(packet, sender_id)
            else:
                logger.warning(f"Unknown packet type: {packet.packet_type}")
        except Exception as e:
            logger.error(f"Error processing packet {type(packet).__name__}: {e}")

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
    def _send(packet: Packet, target_id: str) -> bool:
        """Gửi gói tin đến client đích"""
        target_socket, send_lock = ClientManager.get_client_socket_and_lock(target_id)
        if target_socket and send_lock:
            with send_lock:
                try:
                    Protocol.send_packet(target_socket, packet)
                    return True
                except (ConnectionError, BrokenPipeError) as e:
                    logger.warning(
                        f"Connection error while sending to {target_id}: {e}. Client might have disconnected."
                    )
                    ClientManager.remove_client(target_id)
                    return False
        else:
            return False

    @staticmethod
    def _relay_request_connection(packet: RequestConnectionPacket, controller_id: str):
        """Chuyển tiếp RequestConnectionPacket"""
        logger.info(f"Client {controller_id} requests connection to {packet.host_id}")

        if not ClientManager.is_client_online(packet.host_id):
            response = ResponseConnectionPacket(
                success=False, message=f"Target client {packet.host_id} is not online"
            )

            if RelayHandler._send(response, controller_id):
                logger.debug(
                    f"Client {controller_id} connection to {packet.host_id} failed: Target offline"
                )
        else:
            if RelayHandler._send(packet, packet.host_id):
                logger.debug(
                    f"Client {controller_id} connection request sent to {packet.host_id}"
                )
            else:
                response = ResponseConnectionPacket(
                    success=False, message="Target host not found"
                )
                RelayHandler._send(response, controller_id)

    @staticmethod
    def _relay_request_password(packet: RequestPasswordPacket, host_id: str):
        """Chuyển tiếp RequestPasswordPacket - Host yêu cầu password từ controller"""
        logger.debug(f"Host {host_id} requests password from controller")

        success = RelayHandler._send(packet, packet.controller_id)
        if not success:
            logger.warning(f"Controller {packet.controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            RelayHandler._send(response, host_id)
        else:
            logger.debug(f"Password request sent to controller {packet.controller_id}")

    @staticmethod
    def _relay_send_password(packet: SendPasswordPacket, controller_id: str):
        """Chuyển tiếp SendPasswordPacket - Controller gửi password đến host"""
        logger.debug(f"Client {controller_id} sends password")

        success = RelayHandler._send(packet, packet.host_id)
        if not success:
            logger.warning(f"Host {packet.host_id} not found")
            response = ResponseConnectionPacket(
                success=False, message=f"Target host {packet.host_id} is not online"
            )
            RelayHandler._send(response, controller_id)
        else:
            logger.debug(f"Password sent to host {packet.host_id}")

    @staticmethod
    def _handle_authentication_result(packet: AuthenticationResultPacket, host_id: str):
        """Chuyển tiếp AuthenticationResultPacket - Host gửi kết quả xác thực đến controller"""
        logger.debug(f"Host {host_id} authentication result: {packet.success}")

        if packet.success:
            try:
                session_id = SessionManager.create_session(
                    host_id=host_id, controller_id=packet.controller_id
                )

                if not RelayHandler._send(packet, packet.controller_id):
                    logger.warning(f"Controller {packet.controller_id} not found")
                    response = ResponseConnectionPacket(
                        success=False, message="Controller not available"
                    )
                    RelayHandler._send(response, host_id)
                    SessionManager.end_session(session_id)
                    return

                session_packet = SessionPacket(
                    session_id=session_id,
                    action=SessionAction.CREATED,
                )

                if not RelayHandler._send(session_packet, packet.controller_id):
                    logger.warning(f"Controller {packet.controller_id} not found")
                else:
                    logger.debug(
                        f"Session {session_id} creation notified to controller {packet.controller_id}"
                    )

                if not RelayHandler._send(session_packet, host_id):
                    logger.warning(f"Host {host_id} not found")
                else:
                    logger.debug(
                        f"Session {session_id} creation notified to host {host_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                response = ResponseConnectionPacket(
                    success=False, message="Failed to create session"
                )
                RelayHandler._send(response, packet.controller_id)
                RelayHandler._send(response, host_id)
                return

        else:
            if not RelayHandler._send(packet, packet.controller_id):
                logger.warning(f"Controller {packet.controller_id} not found")
                response = ResponseConnectionPacket(
                    success=False, message="Controller not available"
                )
                RelayHandler._send(response, host_id)
            else:
                logger.debug(
                    f"Authentication result sent to controller {packet.controller_id}"
                )

    @staticmethod
    def _relay_image_packet(packet: ImagePacket):
        """Chuyển tiếp ImagePacket từ host đến controller"""
        session_id = packet.session_id
        session_info = SessionManager.get_session_info(session_id)

        if not session_info:
            logger.warning(f"No active session found for session {session_id}")
            return

        host_id = session_info["host_id"]
        controller_id = session_info["controller_id"]

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
            RelayHandler._send(session_packet, host_id)
            RelayHandler._send(session_packet, controller_id)
            return

        if not RelayHandler._send(packet, controller_id):
            logger.warning(f"Controller {controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            RelayHandler._send(response, host_id)
        else:
            logger.debug(f"Image packet relayed to controller {controller_id}")
