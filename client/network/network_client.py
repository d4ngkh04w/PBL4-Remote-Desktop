from common.config import ServerConfig
from common.logger import logger
import common.protocol as protocol
import socket
import threading
from typing import Union
import time

class NetworkClient:
    def __init__(self, server_host=ServerConfig.SERVER_HOST, server_port=ServerConfig.SERVER_PORT):
        self.host = server_host
        self.port = server_port
        self.sock = None
        self.running = False
        self.listener_thread = None  # Thread để lắng nghe dữ liệu từ server
        
        # Khóa để đảm bảo thread-safe vì nhiều thread có thể truy cập vào socket cùng lúc
        self._lock = threading.Lock()
        self.on_message_received = None  # Callback xử lý khi nhận message

    def connect(self):
        """Kết nối đến server"""        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Timeout 10 giây cho kết nối, tức là nếu không kết nối được trong 10 giây sẽ báo lỗi
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            self.running = True
            logger.info(f"Connected to server at {self.host}:{self.port}")

            # Tạo thread để nghe dữ liệu từ server
            self.listener_thread = threading.Thread(
                target=self.listener_loop, daemon=True)
            self.listener_thread.start()            

        except Exception as e:
            logger.error(
                f"Failed to connect to server {self.host}:{self.port} - {e}")
            raise
        # except socket.gaierror as e:
        #     logger.error(f"DNS resolution failed for {self.host} - {e}")
        #     raise
        # except socket.timeout:
        #     logger.error(f"Connection timeout to {self.host}:{self.port}")
        #     raise
        # except Exception as e:
        #     logger.error(
        #         f"Failed to connect to server {self.host}:{self.port} - {e}")
        #     raise

    def send(self, packet: Union[protocol.ImagePacket, protocol.KeyBoardPacket, protocol.MousePacket]):
        """Gửi packet đến server"""
        if self.sock is None or not self.running:
            logger.warning("Not connected to server")
            return
        try:
            with self._lock:
                protocol.Protocol.send_packet(self.sock, packet)
        except Exception as e:
            logger.error(f"Failed to send data to server - {e}")
            self.disconnect()

    def listener_loop(self):
        """Vòng lặp lắng nghe dữ liệu từ server"""
        while self.running:
            try:
                packet = protocol.Protocol.receive_packet(self.sock)
                if self.on_message_received:
                    self.on_message_received(packet)
            except Exception as e:
                logger.error(f"Error receiving data from server - {e}")
                self.disconnect()

    def disconnect(self):
        """Ngắt kết nối đến server"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error closing socket - {e}")
            self.sock = None
            logger.info(f"Disconnected from server {self.host}:{self.port}")
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1) # Đợi thread kết thúc
            self.listener_thread = None

    # Giới hạn số lần thử kết nối lại
    def reconnect(self):
        """
        Thử kết nối lại đến server
        """
        max_attempts = 5
        self.disconnect()

        for attempt in range(max_attempts):
            logger.info(f"Attempting to reconnect to server {self.host}:{self.port} (Attempt {attempt + 1}/{max_attempts})")
            try:
                if self.connect():
                    logger.info("Reconnected successfully")
                    return True
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed - {e}")

            if attempt < max_attempts - 1:
                time.sleep(2)  # Wait before retrying
        logger.error(f"Failed to reconnect to server {self.host}:{self.port} after {max_attempts} attempts")
        return False
    