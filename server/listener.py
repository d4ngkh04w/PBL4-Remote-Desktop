import socket
import ssl
import threading

from common.config import SecurityConfig, ServerConfig
from common.logger import logger
from common.packet import AssignIdPacket
from common.protocol import Protocol
from common.utils import generate_numeric_id, format_numeric_id


class Listener:
    def __init__(self, host=ServerConfig.SERVER_HOST, port=ServerConfig.SERVER_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.is_listening = False

    def start(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=SecurityConfig.CERT_FILE, keyfile=SecurityConfig.KEY_FILE
        )

        plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        plain_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            plain_socket.bind((self.host, self.port))
            plain_socket.listen(10)
            self.is_listening = True

            self.socket = context.wrap_socket(plain_socket, server_side=True)
            logger.info(f"Listening for connections on {self.host}:{self.port}")

            while self.is_listening:
                self.socket.settimeout(0.5)
                try:
                    client_socket, addr = self.socket.accept()
                    logger.info(f"Accepted connection from {addr}")

                    id = format_numeric_id(generate_numeric_id(9))
                    packet = AssignIdPacket(client_id=id)
                    Protocol.send_packet(client_socket, packet)
                    logger.debug(f"Sent packet: {packet}")

                    client_handler = threading.Thread(
                        target=self.handle_client, args=(client_socket,)
                    )
                    client_handler.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error accepting client connection: {e}")
                    continue
        except OSError as e:
            logger.error(
                f"Failed to bind to {self.host}:{self.port} - {e}", log_to_file=False
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error in server: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        self.is_listening = False
        if self.socket:
            self.socket.close()

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

    def handle_client(self, client_socket):
        pass
