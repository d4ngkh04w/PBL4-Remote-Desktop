import queue
import socket
import ssl
import threading
import logging

from common.packets import (
    AssignIdPacket,
    ClientInformationPacket,
    ConnectionResponsePacket,
)
from common.enums import Status
from common.protocol import Protocol
from common.utils import generate_numeric_id
from server.client_manager import ClientManager
from server.session_manager import SessionManager
from server.relay_handler import RelayHandler

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, host, port, use_ssl, cert_file, key_file, max_clients):
        self.host = host
        self.port = port
        self.socket = None
        self.is_listening = False
        self.shutdown_event = threading.Event()
        self.use_ssl = use_ssl
        self.cert_file = cert_file
        self.key_file = key_file
        self.client_semaphore = threading.Semaphore(max_clients)

    def start(self):
        plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        plain_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            plain_socket.bind((self.host, self.port))
            plain_socket.listen(5)
            self.is_listening = True

            if self.use_ssl:
                if not self.cert_file or not self.key_file:
                    raise ValueError("SSL enabled but cert_file/key_file not provided")

                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)

                self.socket = context.wrap_socket(plain_socket, server_side=True)
                logger.info(f"Listening with SSL on {self.host}:{self.port}")
            else:
                self.socket = plain_socket
                logger.info(f"Listening on {self.host}:{self.port}")

            SessionManager.start_cleanup()

            while not self.shutdown_event.is_set():
                self.socket.settimeout(1.0)
                try:
                    client_socket, addr = self.socket.accept()

                    if not self.client_semaphore.acquire(blocking=False):
                        logger.warning(
                            f"Max clients reached. Rejecting connection from {addr}"
                        )
                        try:
                            rejection_packet = ConnectionResponsePacket(
                                connection_status=Status.SERVER_FULL,
                                message="Server is full, please try again later",
                            )
                            Protocol.send_packet(client_socket, rejection_packet)
                        except Exception as e:
                            logger.error(f"Failed to send rejection packet: {e}")
                        finally:
                            client_socket.close()
                        continue

                    try:
                        client_socket.settimeout(1.0)
                        client_info_packet = Protocol.receive_packet(client_socket)

                        if not isinstance(client_info_packet, ClientInformationPacket):
                            logger.warning(
                                f"Expected ClientInformationPacket but got {type(client_info_packet)}"
                            )
                            client_socket.close()
                            self.client_semaphore.release()
                            continue

                    except Exception as e:
                        logger.error(f"Failed to receive client information: {e}")
                        client_socket.close()
                        self.client_semaphore.release()
                        continue

                    client_id = generate_numeric_id(9)

                    packet = AssignIdPacket(client_id=client_id)
                    Protocol.send_packet(client_socket, packet)
                    logger.debug(f"Sent packet: {packet}")

                    client_handler = threading.Thread(
                        target=self.handle_client,
                        args=(
                            client_socket,
                            client_id,
                            addr,
                            self.client_semaphore,
                            client_info_packet.os,
                            client_info_packet.host_name,
                            client_info_packet.device_id,
                        ),
                        daemon=True,
                    )
                    client_handler.start()

                except socket.timeout:
                    continue
                except ssl.SSLError as e:
                    if self.is_listening:
                        logger.error(f"SSL error accepting client connection: {e}")
                    continue
                except Exception as e:
                    if isinstance(e, OSError) and (e.errno == 9 or e.errno == 10038):
                        break
                    logger.error(f"Error accepting client connection: {e}")
                    continue

        except OSError as e:
            logger.error(f"Failed to bind to {self.host}:{self.port} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in server: {e}")
            raise

    def stop(self):
        if self.shutdown_event.is_set():
            return

        self.shutdown_event.set()

        if self.socket:
            try:
                self.socket.close()
                self.socket = None
            except Exception:
                logger.error("Error closing server socket")
        try:
            RelayHandler.shutdown()
            SessionManager.shutdown()
            ClientManager.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down RelayHandler: {e}")

        logger.info("Server shutdown complete")

    def receive(self):
        if not self.socket:
            logger.error("Server is not running")
            return

        try:
            packet = Protocol.receive_packet(self.socket)
            if packet:
                logger.info(f"Received packet: {packet}")
                return packet
            else:
                logger.warning("No packet received")
        except Exception as e:
            logger.error(f"Error receiving packet: {e}")

    def sender_worker(
        self, client_socket: ssl.SSLSocket | socket.socket, client_id: str
    ):
        """Thread chuyên gửi packet từ queue của một client."""
        send_queue = ClientManager.get_client_queue(client_id)
        if not send_queue:
            logger.warning(f"No queue found for client {client_id}")
            return

        while (
            ClientManager.is_client_exist(client_id)
            and not self.shutdown_event.is_set()
        ):
            try:
                packet = send_queue.get(timeout=0.1)
                Protocol.send_packet(client_socket, packet)
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"Error sending packet to {client_id}: {e}")
                break

        logger.debug(f"Sender worker for client {client_id} stopped")

    def handle_client(
        self,
        client_socket: ssl.SSLSocket | socket.socket,
        client_id: str,
        client_addr: str,
        client_semaphore: threading.Semaphore,
        os: str = "",
        host_name: str = "",
        device_id: str = "",
    ):
        """Main handler loop cho client"""
        sender_thread = None
        try:
            ClientManager.add_client(
                client_socket, client_id, client_addr, os, host_name, device_id
            )
            logger.info(
                f"Client {client_id} ({host_name}) connected from {client_addr}"
            )

            client_socket.settimeout(1.0)

            sender_thread = threading.Thread(
                target=self.sender_worker, args=(client_socket, client_id), daemon=True
            )
            sender_thread.start()

            while (
                ClientManager.is_client_exist(client_id)
                and not self.shutdown_event.is_set()
            ):
                try:
                    packet = Protocol.receive_packet(client_socket)
                except socket.timeout:
                    continue
                if not packet:
                    break

                RelayHandler.relay_packet(packet, client_socket)

        except ValueError as ve:
            logger.error(f"ValueError in handle_client for {client_id}: {ve}")
        except ConnectionError:
            logger.info("Connection closed by client")
        except Exception:
            logger.error(f"Exception in handle_client for {client_id}", exc_info=True)
        finally:
            sessions = SessionManager.get_all_sessions(client_id)
            if sessions:
                for sess_id in list(sessions.keys()):
                    SessionManager.end_session(sess_id)

            ClientManager.remove_client(client_id)
            client_socket.close()

            client_semaphore.release()
            logger.info(f"Client {client_id} disconnected from {client_addr}")
