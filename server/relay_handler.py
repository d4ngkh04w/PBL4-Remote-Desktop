import logging
from concurrent.futures import ThreadPoolExecutor
import queue
from typing import Dict, Callable
import socket
import ssl
import os
import threading

from common.packet import (
    Packet,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    ResponseConnectionPacket,
    AuthenticationResultPacket,
    ImagePacket,
    FrameUpdatePacket,
    SessionPacket,
    SessionAction,
)
from server.client_manager import ClientManager
from server.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RelayHandler:
    __thread_pool = ThreadPoolExecutor(
        max_workers=min((os.cpu_count() or 4) * 4, 30),
        thread_name_prefix="RelayHandler",
    )
    __packet_handlers: Dict[type, Callable] = {}
    __shutdown_event = threading.Event()

    @staticmethod
    def relay_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        """Xử lý và chuyển tiếp gói tin sử dụng thread pool"""
        try:
            if RelayHandler.__shutdown_event.is_set():
                logger.warning("Server is shutting down. Dropping packet.")
                return

            RelayHandler.__thread_pool.submit(
                RelayHandler.__process_packet, packet, sender_socket
            )
        except RuntimeError as e:
            if RelayHandler.__shutdown_event.is_set():
                logger.warning("Packet submitted during shutdown. Dropping.")
            else:
                raise e

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên khi shutdown server"""
        if cls.__shutdown_event.is_set():
            return

        cls.__shutdown_event.set()
        try:
            cls.__thread_pool.shutdown(wait=True)
            logger.info("RelayHandler shutdown completed")
        except Exception as e:
            logger.error(f"Error during RelayHandler shutdown: {e}")

    @classmethod
    def __initialize_handlers(cls):
        """Khởi tạo mapping giữa packet types và handlers"""
        if not cls.__packet_handlers:
            cls.__packet_handlers = {
                RequestConnectionPacket: cls.__relay_request_connection,
                RequestPasswordPacket: cls.__relay_request_password,
                SendPasswordPacket: cls.__relay_send_password,
                AuthenticationResultPacket: cls.__handle_authentication_result,
                ImagePacket: cls.__relay_stream_packet,
                FrameUpdatePacket: cls.__relay_stream_packet,
            }

    @staticmethod
    def __process_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        sender_info = ClientManager.get_client_info(sender_socket)
        if not sender_info:
            logger.warning(
                "Could not find sender info for the socket. Dropping packet."
            )
            return

        sender_id = sender_info["id"]
        try:
            RelayHandler.__initialize_handlers()

            packet_type = type(packet)
            handler = RelayHandler.__packet_handlers.get(packet_type)

            if handler:
                if isinstance(
                    packet,
                    (ImagePacket, FrameUpdatePacket),
                ):
                    handler(packet, sender_id)
                else:
                    handler(packet)
            else:
                logger.warning(
                    f"Unknown packet type: {packet.packet_type} or sender not found"
                )
        except Exception:
            raise

    @staticmethod
    def __relay_request_connection(
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
    def __relay_request_password(
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
    def __relay_send_password(
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
    def __handle_authentication_result(
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
    def __relay_stream_packet(
        packet: ImagePacket | FrameUpdatePacket,
        host_id: str,
    ):
        """Chuyển tiếp các gói tin stream từ host đến controller"""

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
            host_queue = ClientManager.get_client_queue(host_id)
            if host_queue:
                host_queue.put(session_packet)
            if controller_queue:
                controller_queue.put(session_packet)
