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
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    ImagePacket,
    FrameUpdatePacket,
    MousePacket,
    KeyboardPacket,
    AuthenticationPasswordPacket,
    SessionPacket,
    SessionPacket,
)
from common.enums import Status
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
                ConnectionRequestPacket: cls.__relay_request_connection,
                AuthenticationPasswordPacket: cls.__handle_authentication_password,
                ImagePacket: cls.__relay_stream_packet,
                FrameUpdatePacket: cls.__relay_stream_packet,
                MousePacket: cls.__relay_stream_packet,
                KeyboardPacket: cls.__relay_stream_packet,
                SessionPacket: cls.__handle_session_packet,
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
                handler(packet, sender_id)
        except Exception:
            raise

    @staticmethod
    def __relay_request_connection(
        packet: ConnectionRequestPacket,
        sender_id: str,
    ):
        """Chuyển tiếp ConnectionRequestPacket"""
        logger.debug(f"Relaying ConnectionRequestPacket: {packet}")

        receiver_id = packet.receiver_id
        receiver_queue = ClientManager.get_client_queue(receiver_id)
        sender_queue = ClientManager.get_client_queue(sender_id)

        if not sender_queue:
            logger.warning(f"Sender {sender_id} not found")
            return

        if not receiver_queue:
            logger.warning(f"Receiver {receiver_id} not found")
            response = ConnectionResponsePacket(
                connection_status=Status.RECEIVER_NOT_FOUND,
                message="Receiver not found",
            )
            sender_queue.put(response)
            return
        else:
            receiver_queue.put(packet)

    @staticmethod
    def __handle_authentication_password(
        packet: AuthenticationPasswordPacket,
        sender_id: str,
    ):
        """Xử lý AuthenticationPasswordPacket"""
        logger.debug(f"Handling AuthenticationPasswordPacket: {packet}")

        receiver_id = packet.receiver_id
        receiver_queue = ClientManager.get_client_queue(receiver_id)
        sender_queue = ClientManager.get_client_queue(sender_id)

        if not sender_queue:
            logger.warning(f"Sender {sender_id} not found")
            return

        if not receiver_queue:
            logger.warning(f"Receiver {receiver_id} not found")
            response = ConnectionResponsePacket(
                connection_status=Status.RECEIVER_NOT_FOUND,
                message="Error during transmission, please try again later",
            )
            sender_queue.put(response)
            return

        if packet.status == Status.SUCCESS:
            session_id = SessionManager.create_session(
                controller_id=receiver_id,
                host_id=sender_id,
                timeout=Config.session_timeout,
            )
            session_packet = SessionPacket(
                status=Status.SESSION_STARTED, session_id=session_id
            )
            session_packet.role = "HOST"
            sender_queue.put(session_packet)
            session_packet.role = "CONTROLLER"
            receiver_queue.put(session_packet)
        else:
            receiver_queue.put(packet)

    @staticmethod
    def __handle_session_packet(
        packet: SessionPacket,
        sender_id: str,
    ):
        """Xử lý SessionPacket"""
        session_id = packet.session_id
        session_info = SessionManager.get_session(session_id)
        if not session_info:
            logger.warning(f"Session {session_id} not found. Dropping packet.")
            return

        if packet.status == Status.SESSION_ENDED:

            if not SessionManager.is_client_in_session(sender_id, session_id):
                logger.warning(
                    f"Sender {sender_id} not in session {session_id}. Dropping packet"
                )
                return

            SessionManager.end_session(session_id)
            receiver_id = (
                session_info["controller_id"]
                if session_info["host_id"] == sender_id
                else session_info["host_id"]
            )
            receiver_queue = ClientManager.get_client_queue(str(receiver_id))

            if receiver_queue:
                receiver_queue.put(packet)

    @staticmethod
    def __relay_stream_packet(
        packet: ImagePacket | FrameUpdatePacket | MousePacket,
        sender_id: str,
    ):
        """Chuyển tiếp các gói tin stream"""

        session_id, session_info = SessionManager.get_client_session(sender_id)
        if not session_info or not session_id:
            logger.warning(f"Session not found for sender {sender_id}. Dropping packet")
            return

        receiver_id = (
            session_info["controller_id"]
            if session_info["host_id"] == sender_id
            else session_info["host_id"]
        )

        receiver_queue = ClientManager.get_client_queue(str(receiver_id))
        sender_queue = ClientManager.get_client_queue(sender_id)

        response = SessionPacket(status=Status.SESSION_ENDED, session_id=session_id)

        if not SessionManager.is_client_in_session(
            sender_id, session_id
        ) or not SessionManager.is_client_in_session(str(receiver_id), session_id):
            logger.warning(
                f"One of the clients is no longer in session, ending session {session_id}"
            )
            SessionManager.end_session(session_id)
            if sender_queue:
                sender_queue.put(response)
            if receiver_queue:
                receiver_queue.put(response)

            return

        if receiver_queue:
            try:
                receiver_queue.put_nowait(packet)
            except queue.Full:
                logger.warning(
                    f"Receiver {receiver_id}'s send queue is full. Dropping packet"
                )
        else:
            logger.warning(f"Receiver {receiver_id} not found. Dropping packet")
