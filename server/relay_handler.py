import logging
from concurrent.futures import ThreadPoolExecutor
import queue
from typing import Dict, Callable
import socket
import ssl
import os
import threading


from common.packets import (
    Packet,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    ResponseConnectionPacket,
    AuthenticationResultPacket,
    ImagePacket,
    FrameUpdatePacket,
    SessionPacket,
    MousePacket,
    KeyBoardPacket,
)
from common.enums import SessionAction, ConnectionStatus, AuthenticationResult
from server.client_manager import ClientManager
from server.session_manager import SessionManager

# from options import args
from common.config import Config

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
                MousePacket: cls.__relay_stream_packet,
                KeyBoardPacket: cls.__relay_stream_packet,
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
        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)
        if not controller_queue:
            logger.warning(f"Client {controller_id} not found")
            return

        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)
        response = ResponseConnectionPacket(
            connection_status=ConnectionStatus.FAILED,
            message="",
        )
        if not host_queue:
            response.message = f"Client {host_id} not found"
            controller_queue.put(response)
            return

        logger.info(f"Client {controller_id} requests connection to {host_id}")

        if not ClientManager.is_client_online(host_id):
            response.message = f"Client {host_id} is not online"
            controller_queue.put(response)

        else:
            host_queue.put(packet)

    @staticmethod
    def __relay_request_password(
        packet: RequestPasswordPacket,
    ):
        """Chuyển tiếp RequestPasswordPacket - Host yêu cầu password từ controller"""
        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)
        if not host_queue:
            logger.warning(f"Client {host_id} not found")
            return

        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)
        response = ResponseConnectionPacket(
            connection_status=ConnectionStatus.FAILED,
            message="",
        )
        if not controller_queue:
            response.message = f"Client {controller_id} not found"
            host_queue.put(response)
            return

        if not ClientManager.is_client_online(controller_id):
            response.message = f"Client {controller_id} is not online"
            host_queue.put(response)
        else:
            controller_queue.put(packet)

    @staticmethod
    def __relay_send_password(
        packet: SendPasswordPacket,
    ):
        """Chuyển tiếp SendPasswordPacket - Controller gửi password đến host"""
        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)
        if not controller_queue:
            logger.warning(f"Client {controller_id} not found")
            return

        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)
        response = ResponseConnectionPacket(
            connection_status=ConnectionStatus.FAILED,
            message="",
        )
        if not host_queue:
            response.message = f"Client {host_id} not found"
            controller_queue.put(response)
            return

        if not ClientManager.is_client_online(host_id):
            response.message = f"Client {host_id} is not online"
            controller_queue.put(response)
        else:
            host_queue.put(packet)

    @staticmethod
    def __handle_authentication_result(
        packet: AuthenticationResultPacket,
    ):
        """Chuyển tiếp AuthenticationResultPacket - Host gửi kết quả xác thực đến controller"""
        host_id = packet.host_id
        host_queue = ClientManager.get_client_queue(host_id)
        if not host_queue:
            logger.warning(f"Host {host_id} not found")
            return

        logger.debug(f"Host {host_id} authentication result: {packet.success}")

        controller_id = packet.controller_id
        controller_queue = ClientManager.get_client_queue(controller_id)

        response = ResponseConnectionPacket(
            connection_status=ConnectionStatus.FAILED,
            message="",
        )
        if not controller_queue:
            response.message = f"Client {controller_id} not found"
            host_queue.put(response)
            return

        if packet.success:
            try:
                session_id = ""
                if not SessionManager.is_client_in_session(
                    host_id
                ) and not SessionManager.is_client_in_session(controller_id):
                    session_id = SessionManager.create_session(
                        host_id=host_id,
                        controller_id=controller_id,
                        timeout=Config.session_timeout,
                    )
                else:
                    response.connection_status = ConnectionStatus.REJECTED
                    if SessionManager.is_client_in_session(host_id):
                        response.message = f"Host {host_id} is already in a session"
                        controller_queue.put(response)
                        return
                    if SessionManager.is_client_in_session(controller_id):
                        response.message = (
                            f"Controller {controller_id} is already in a session"
                        )
                        controller_queue.put(response)
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
                response.connection_status = ConnectionStatus.FAILED
                response.message = "Failed to create session"
                controller_queue.put(response)
                host_queue.put(response)
                return
        else:
            controller_queue.put(packet)
            logger.debug(f"Authentication result sent to controller {controller_id}")

    @staticmethod
    def __relay_stream_packet(
        packet: ImagePacket | FrameUpdatePacket | MousePacket,
        sender_id: str,
    ):
        """Chuyển tiếp các gói tin stream"""

        session_id, session_info = SessionManager.get_client_sessions(sender_id)
        if not session_info or not session_id:
            return

        sender_role = SessionManager.get_client_role_in_session(sender_id)
        if not sender_role:
            return

        if sender_role == "HOST":
            receiver_id = session_info["controller_id"]
        else:
            receiver_id = session_info["host_id"]

        receiver_queue = ClientManager.get_client_queue(str(receiver_id))

        session_packet = SessionPacket(
            session_id=session_id,
            action=SessionAction.ENDED,
        )

        if not SessionManager.is_client_in_session(
            sender_id
        ) or not SessionManager.is_client_in_session(str(receiver_id)):
            logger.warning(
                f"One of the clients is no longer in session, ending session {session_id}"
            )
            SessionManager.end_session(session_id)
            sender_queue = ClientManager.get_client_queue(sender_id)
            if sender_queue:
                sender_queue.put(session_packet)
            if receiver_queue:
                receiver_queue.put(session_packet)

        if receiver_queue:
            try:
                receiver_queue.put_nowait(packet)
            except queue.Full:
                logger.warning(
                    f"Receiver {receiver_id}'s send queue is full. Dropping packet"
                )
