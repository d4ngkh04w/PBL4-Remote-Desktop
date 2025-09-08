import socket
import ssl
import threading
import logging

from common.packet import AssignIdPacket
from common.protocol import Protocol
from common.utils import generate_numeric_id
from server.client_handler import ClientHandler

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, host, port, use_ssl, cert_file, key_file):
        self.host = host
        self.port = port
        self.socket = None
        self.is_listening = False
        self.use_ssl = use_ssl
        self.cert_file = cert_file
        self.key_file = key_file

    def start(self):
        plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        plain_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            plain_socket.bind((self.host, self.port))
            plain_socket.listen(10)
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

            while self.is_listening:
                self.socket.settimeout(0.5)
                try:
                    client_socket, addr = self.socket.accept()
                    client_id = generate_numeric_id(9)

                    packet = AssignIdPacket(client_id=client_id)
                    Protocol.send_packet(client_socket, packet)
                    logger.debug(f"Sent packet: {packet}")

                    client_handler = threading.Thread(
                        target=ClientHandler.handle,
                        args=(client_socket, client_id, addr),
                        daemon=True,
                    )
                    client_handler.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error accepting client connection: {e}")
                    continue

        except OSError as e:
            logger.error(f"Failed to bind to {self.host}:{self.port} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in server: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        self.is_listening = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

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
