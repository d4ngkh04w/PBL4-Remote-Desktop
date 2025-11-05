import logging
from concurrent.futures import ThreadPoolExecutor
import queue
from typing import Callable
import socket
import ssl
import os
import threading


from common.packets import (
    Packet,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    MousePacket,
    KeyboardPacket,
    AuthenticationPasswordPacket,
    SessionPacket,
    VideoStreamPacket,
    VideoConfigPacket,
)
from common.enums import Status
from server.client_manager import ClientManager
from server.session_manager import SessionManager

from common.config import Config

logger = logging.getLogger(__name__)


class RelayHandler:
    __stream_pool = ThreadPoolExecutor(
        max_workers=min((os.cpu_count() or 4) * 30, 250),
        thread_name_prefix="StreamRelay",
    )
    __control_pool = ThreadPoolExecutor(
        max_workers=min((os.cpu_count() or 4) * 4, 30),
        thread_name_prefix="ControlRelay",
    )
    __packet_handlers: dict[type, Callable] = {}
    __shutdown_event = threading.Event()

    @staticmethod
    def relay_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        """Xử lý và chuyển tiếp gói tin sử dụng thread pool"""
        try:
            if RelayHandler.__shutdown_event.is_set():
                logger.warning("Server is shutting down. Dropping packet")
                return
            if isinstance(
                packet,
                (
                    VideoStreamPacket,
                    VideoConfigPacket,
                    MousePacket,
                    KeyboardPacket,
                ),
            ):
                RelayHandler.__stream_pool.submit(
                    RelayHandler.__process_packet, packet, sender_socket
                )
            else:
                RelayHandler.__control_pool.submit(
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
            cls.__stream_pool.shutdown(wait=True)
            cls.__control_pool.shutdown(wait=True)
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
                SessionPacket: cls.__handle_session_packet,
                VideoStreamPacket: cls.__relay_stream_packet,
                VideoConfigPacket: cls.__relay_stream_packet,
                # CursorInfoPacket removed - cursor info now embedded in VideoStreamPacket
                MousePacket: cls.__relay_stream_packet,
                KeyboardPacket: cls.__relay_stream_packet,
            }

    @staticmethod
    def __process_packet(packet: Packet, sender_socket: socket.socket | ssl.SSLSocket):
        sender_info = ClientManager.get_client_info(sender_socket)
        if not sender_info:
            logger.warning("Could not find sender info for the socket. Dropping packet")
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

        if SessionManager.is_client_connected(sender_id, receiver_id):
            logger.warning(
                f"Sender {sender_id} is already connected to receiver {receiver_id}"
            )
            response = ConnectionResponsePacket(
                connection_status=Status.ALREADY_CONNECTED,
                message="You are already connected to this host",
            )
            sender_queue.put(response)
            return

        if receiver_queue:
            receiver_queue.put(packet)
        else:
            logger.warning(f"Receiver {receiver_id} not found")
            response = ConnectionResponsePacket(
                connection_status=Status.RECEIVER_NOT_FOUND,
                message="Receiver not found",
            )
            sender_queue.put(response)

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
            host_session_packet = SessionPacket(
                status=Status.SESSION_STARTED, session_id=session_id, role="host"
            )
            controller_session_packet = SessionPacket(
                status=Status.SESSION_STARTED, session_id=session_id, role="controller"
            )
            sender_queue.put(host_session_packet)
            receiver_queue.put(controller_session_packet)
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
            logger.warning(f"Session {session_id} not found. Dropping packet")
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
        packet: MousePacket | KeyboardPacket | VideoStreamPacket | VideoConfigPacket,
        sender_id: str,
    ):
        """Chuyển tiếp các gói tin stream"""

        def __send_to_receiver(receiver_id: str, pkt):
            receiver_queue = ClientManager.get_client_queue(str(receiver_id))
            if not receiver_queue:
                logger.warning(f"Receiver {receiver_id} not found. Dropping packet")
                return False

            try:
                if isinstance(pkt, VideoStreamPacket):
                    receiver_queue.put(pkt, block=False)
                else:
                    receiver_queue.put_nowait(pkt)
            except queue.Full:
                logger.warning(
                    f"Receiver {receiver_id}'s send queue is full. Dropping packet"
                )

        if packet.session_id is not None:
            session_info = SessionManager.get_session(packet.session_id)
            if not session_info:
                logger.warning(
                    f"Session {packet.session_id} not found. Dropping packet"
                )
                return

            receiver_id = (
                session_info["controller_id"]
                if session_info["host_id"] == sender_id
                else session_info["host_id"]
            )
            __send_to_receiver(receiver_id, packet)
            return

        sessions = SessionManager.get_all_sessions(sender_id)
        if not sessions:
            logger.warning(f"Session not found for sender {sender_id}. Dropping packet")
            return

        need_clone = len(sessions) > 1

        for session_id, session in sessions.items():
            receiver_id = (
                session["controller_id"]
                if session["host_id"] == sender_id
                else session["host_id"]
            )

            if need_clone:
                pkt = type(packet)(**packet.__dict__)
                pkt.session_id = session_id
            else:
                pkt = packet
                pkt.session_id = session_id

            __send_to_receiver(receiver_id, pkt)
