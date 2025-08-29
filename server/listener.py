import socket
import threading
from common.logger import logger


class Listener:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.is_listening = False

    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(10)
            self.is_listening = True
            logger.info(f"Listening for connections on {self.host}:{self.port}")

            while self.is_listening:
                self.socket.settimeout(0.5)
                try:
                    client_socket, addr = self.socket.accept()
                    logger.info(f"Accepted connection from {addr}")
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

    def handle_client(self, client_socket):
        logger.info(f"Handling client {client_socket}")
        client_socket.close()
