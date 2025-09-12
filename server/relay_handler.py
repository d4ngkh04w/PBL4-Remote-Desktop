import logging
from concurrent.futures import ThreadPoolExecutor
import queue
from typing import Dict, Callable
import socket
import ssl
import os

from common.packet import (
    Packet,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    ResponseConnectionPacket,
    AuthenticationResultPacket,
    ImagePacket,
    ImageChunkPacket,
    SessionPacket,
    SessionAction,
)
from server.client_manager import ClientManager
from server.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RelayHandler:
    _thread_pool = ThreadPoolExecutor(
        max_workers=min((os.cpu_count() or 4) * 2, 16),
        thread_name_prefix="RelayHandler",
    )
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
                ImageChunkPacket: cls._relay_image_packet,
            }

    @staticmethod
    def relay_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        """Xử lý và chuyển tiếp gói tin sử dụng thread pool"""
        try:
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
                if isinstance(
                    packet,
                    (ImageChunkPacket, ImagePacket),
                ):
                    handler(packet, sender_socket)
                else:
                    handler(packet)
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
    def _relay_request_connection(
        packet: RequestConnectionPacket,
    ):
        """Chuyển tiếp RequestConnectionPacket"""
        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)

        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)

        logger.info(f"Client {controller_id} requests connection to {host_id}")

        if not ClientManager.is_client_online(host_id):
            response = ResponseConnectionPacket(
                success=False, message=f"Target client {host_id} is not online"
            )

            if controller_queue:
                controller_queue.put(response)

        else:
            if host_queue:
                host_queue.put(packet)

    @staticmethod
    def _relay_request_password(
        packet: RequestPasswordPacket,
    ):
        """Chuyển tiếp RequestPasswordPacket - Host yêu cầu password từ controller"""
        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)
        logger.debug(f"Host {host_id} requests password from controller")

        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)

        if not controller_queue:
            logger.warning(f"Controller {controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            if host_queue:
                host_queue.put(response)
        else:
            if controller_queue:
                controller_queue.put(packet)

    @staticmethod
    def _relay_send_password(
        packet: SendPasswordPacket,
    ):
        """Chuyển tiếp SendPasswordPacket - Controller gửi password đến host"""
        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)
        # logger.debug(f"Controller {controller_id} sends password to host")
        logger.info(f"{packet}")

        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)

        if not host_queue:
            response = ResponseConnectionPacket(
                success=False, message=f"Target host {host_id} is not online"
            )
            if controller_queue:
                controller_queue.put(response)
        else:
            if host_queue:
                host_queue.put(packet)

    @staticmethod
    def _handle_authentication_result(
        packet: AuthenticationResultPacket,
    ):
        """Chuyển tiếp AuthenticationResultPacket - Host gửi kết quả xác thực đến controller"""
        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)

        logger.debug(f"Host {host_id} authentication result: {packet.success}")

        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)

        if not controller_queue:
            logger.warning(f"Controller {controller_id} not found")
            response = ResponseConnectionPacket(
                success=False, message="Controller not available"
            )
            if host_queue:
                host_queue.put(response)
            return

        if packet.success:
            try:
                session_id = ""
                if not SessionManager.is_client_in_session(
                    host_id
                ) and not SessionManager.is_client_in_session(controller_id):
                    session_id = SessionManager.create_session(
                        host_id=host_id, controller_id=controller_id
                    )
                else:
                    if SessionManager.is_client_in_session(host_id):
                        response = ResponseConnectionPacket(
                            success=False,
                            message=f"Host {host_id} is already in a session",
                        )
                        if controller_queue:
                            controller_queue.put(response)
                        return
                    if SessionManager.is_client_in_session(controller_id):
                        response = ResponseConnectionPacket(
                            success=False,
                            message=f"Controller {controller_id} is already in a session",
                        )
                        if host_queue:
                            host_queue.put(response)
                        return

                session_packet = SessionPacket(
                    session_id=session_id,
                    action=SessionAction.CREATED,
                )

                if controller_queue:
                    controller_queue.put(session_packet)
                    logger.debug(
                        f"Session {session_id} creation notified to controller {controller_id}"
                    )

                if host_queue:
                    host_queue.put(session_packet)
                    logger.debug(
                        f"Session {session_id} creation notified to host {host_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                response = ResponseConnectionPacket(
                    success=False, message="Failed to create session"
                )

                if controller_queue:
                    controller_queue.put(response)
                if host_queue:
                    host_queue.put(response)
                return
        else:
            if controller_queue:
                controller_queue.put(packet)
                logger.debug(
                    f"Authentication result sent to controller {controller_id}"
                )

    @staticmethod
    def _relay_image_packet(
        packet: ImagePacket | ImageChunkPacket,
        host_socket: socket.socket | ssl.SSLSocket,
    ):
        """Chuyển tiếp các gói tin stream (ImagePacket, ImageChunkPacket) từ host đến controller"""
        host_info = ClientManager.get_client_info(host_socket)
        if host_info is None:
            logger.warning(f"Host socket not found in client manager")
            return

        host_id = host_info["id"]
        host_queue = ClientManager.get_client_queue(host_id)

        session_id, session_info = SessionManager.get_client_sessions(host_id)
        if not session_info or not session_id:
            return

        controller_id = session_info["controller_id"]
        controller_queue = ClientManager.get_client_queue(str(controller_id))

        if controller_queue:
            try:
                controller_queue.put_nowait(packet)
            except queue.Full:
                logger.warning(
                    f"Controller {controller_id}'s send queue is full. Dropping packet."
                )

        session_packet = SessionPacket(
            session_id=session_id,
            action=SessionAction.ENDED,
        )

        if not SessionManager.is_client_in_session(
            host_id
        ) or not SessionManager.is_client_in_session(str(controller_id)):
            logger.warning(
                f"One of the clients is no longer in session, ending session {session_id}"
            )
            SessionManager.end_session(session_id)
            if host_queue:
                host_queue.put(session_packet)
            if controller_queue:
                controller_queue.put(session_packet)
