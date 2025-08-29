import socket
from common.logger import logger


class Connection:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to server {self.host}:{self.port}")
        except ConnectionRefusedError:
            logger.error(
                f"Connection refused - Server {self.host}:{self.port} is not available"
            )
            raise
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed for {self.host} - {e}")
            raise
        except socket.timeout:
            logger.error(f"Connection timeout to {self.host}:{self.port}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to server {self.host}:{self.port} - {e}")
            raise

    def disconnect(self):
        if self.socket:
            self.socket.close()
            logger.info(f"Disconnected from server {self.host}:{self.port}")
