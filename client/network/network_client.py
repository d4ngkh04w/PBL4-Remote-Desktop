from common.config import ServerConfig
from common.logger import logger
import common.protocol as protocol
import socket
import threading


class NetworkClient:
    def __init__(self, server_host = ServerConfig.SERVER_HOST, server_port = ServerConfig.SERVER_PORT):
        self.host = server_host
        self.port = server_port
        self.sock = None
        self.running = False
        self.listener_thread = None

        # Callback xử lý khi nhận message
        self.on_message_received = None

    def connect(self):
        # Kết nối đến server
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.running = True
            logger.info(f"Connected to server at {self.host}:{self.port}")

            # Tạo thread để nghe dữ liệu từ server
            self.listener_thread = threading.Thread(target=self.listener_loop, daemon = True)
            self.listener_thread.start()
            return True
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
            logger.error(
                f"Failed to connect to server {self.host}:{self.port} - {e}")
            raise

    def send(self, packet):
        # Gửi object packet
        if self.sock:
            try:
                protocol.Protocol.send_packet(self.sock, packet)
            except Exception as e:
                logger.error(f"Failed to send data to server - {e}")
                self.disconnect()

       

               