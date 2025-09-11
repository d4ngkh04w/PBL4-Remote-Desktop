import socket
import ssl
import threading
import time
import traceback
from typing import Union, Optional, Any, Callable
import logging

from common.packet import (
    ImagePacket,
    KeyBoardPacket,
    MousePacket,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    AuthenticationResultPacket,
)
from common.protocol import Protocol
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


class NetworkClient:
    def __init__(self, server_host, server_port, use_ssl, cert_file):
        self.host = server_host
        self.port = server_port
        self.socket = None
        self.use_ssl = use_ssl
        self.cert_file = cert_file
        self.session_id: Optional[str] = None
        self.running = False
        self.listener_thread = None  # Thread để lắng nghe dữ liệu từ server
        self._disconnected = False  # Flag to track if already disconnected

        # Khóa để đảm bảo thread-safe vì nhiều thread có thể truy cập vào socket cùng lúc
        self._lock = threading.Lock()
        self.on_message_received: Optional[Callable[[Any], None]] = None

    def connect(self):
        plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            if self.use_ssl:
                if not self.cert_file:
                    raise ValueError("SSL enabled but cert_file not provided")

                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_verify_locations(self.cert_file)
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = False

                self.socket = context.wrap_socket(
                    plain_socket, server_hostname=self.host
                )
                logger.info("SSL enabled: using secure connection")
            else:
                self.socket = plain_socket
                logger.info("SSL disabled: using plain TCP connection")

            self.socket.settimeout(30)
            self.socket.connect((self.host, self.port))
            self.running = True
            self._disconnected = False  # Reset disconnected flag on successful connect
            logger.info(f"Connected to server at {self.host}:{self.port}")

            self.listener_thread = threading.Thread(
                target=self.listener_loop, daemon=True
            )
            self.listener_thread.start()

        except Exception as e:
            logger.error(f"Failed to connect to server {self.host}:{self.port} - {e}")
            self.disconnect()

    def send(
        self,
        packet: Union[
            ImagePacket,
            KeyBoardPacket,
            MousePacket,
            RequestConnectionPacket,
            RequestPasswordPacket,
            AuthenticationResultPacket,
            SendPasswordPacket,
        ],
    ):
        """Gửi packet đến server"""
        if self.socket is None or not self.running:
            logger.warning("Not connected to server")
            return
        try:
            with self._lock:
                Protocol.send_packet(self.socket, packet)
        except Exception as e:
            logger.error(f"Failed to send data to server - {e}")
            self.disconnect()

    def listener_loop(self):
        """Vòng lặp lắng nghe dữ liệu từ server"""
        while self.running:
            try:
                if self.socket is None:
                    logger.warning("Not connected to server")
                    return
                self.socket.settimeout(0.5)
                packet = Protocol.receive_packet(self.socket)
                if packet:
                    if self.on_message_received:
                        self.on_message_received(packet)

            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"Error receiving data from server - {e}")
                self.disconnect()

    def disconnect(self):
        """Ngắt kết nối đến server"""
        with self._lock:
            if self._disconnected:
                return

            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
                self._disconnected = True
                logger.info(f"Disconnected from server {self.host}:{self.port}")
            else:
                self._disconnected = True

        if (
            self.listener_thread
            and self.listener_thread.is_alive()
            and self.listener_thread != threading.current_thread()
        ):
            self.listener_thread.join(timeout=1)  # Đợi thread kết thúc
            self.listener_thread = None

    # Giới hạn số lần thử kết nối lại
    def reconnect(self):
        """
        Thử kết nối lại đến server
        """
        max_attempts = 5
        self.disconnect()

        for attempt in range(max_attempts):
            logger.info(
                f"Attempting to reconnect to server {self.host}:{self.port} (Attempt {attempt + 1}/{max_attempts})"
            )
            try:
                if self.connect():
                    logger.info("Reconnected successfully")
                    return True
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed - {e}")

            if attempt < max_attempts - 1:
                time.sleep(2)  # Wait before retrying
        logger.error(
            f"Failed to reconnect to server {self.host}:{self.port} after {max_attempts} attempts"
        )
        return False
