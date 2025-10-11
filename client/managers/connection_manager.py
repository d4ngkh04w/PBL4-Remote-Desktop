import logging
import socket
import ssl
import threading
from queue import Queue, Empty
from typing import Any

from client.controllers.main_window_controller import MainWindowController
from common.protocol import Protocol
from client.handlers.client_handle import ClientHandler

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Quản lý kết nối socket duy nhất đến server.
    Thực hiện kết nối, tự động kết nối lại, gửi và nhận packet.
    Lớp này được thiết kế theo mẫu Singleton, chỉ có một instance duy nhất trong suốt vòng đời ứng dụng.
    """

    _instance = None
    _lock = threading.RLock()

    def __init__(self, server_host, server_port, use_ssl, cert_file):
        if ConnectionManager._instance is not None:
            logger.warning(
                "ConnectionManager is a singleton and has already been instantiated."
            )

        self.host = server_host
        self.port = server_port
        self.use_ssl = use_ssl
        self.cert_file = cert_file

        self.socket = None
        self.listener_thread = None
        self.sender_thread = None

        self._send_queue = Queue()
        self._shutdown_event = threading.Event()
        self._running = False
        self._is_connecting = False
        self._manually_disconnected = False

        self.auto_reconnect = True
        self.max_retries = 5
        self.retry_delay = 2
        self.reconnect_backoff = 1.5
        self._reconnect_attempts = 0

        # Đặt instance hiện tại cho các phương thức classmethod
        ConnectionManager._instance = self

    def connect(self):
        """
        Bắt đầu quá trình kết nối đến server.
        Nếu kết nối ban đầu thất bại, sẽ tự động bắt đầu quá trình kết nối lại.
        Phương thức này không blocking.
        """
        with self._lock:
            if self._is_connecting or self._running:
                logger.warning("Connection process is already active.")
                return
            self._is_connecting = True
            self._manually_disconnected = False

        # Bắt đầu kết nối trong một luồng riêng để không block luồng gọi nó
        connect_thread = threading.Thread(
            target=self._initial_connect_sequence, daemon=True
        )
        connect_thread.start()

    def _initial_connect_sequence(self):
        """Thực hiện kết nối ban đầu và bắt đầu reconnect nếu cần."""
        if self._attempt_connect():
            return  # Kết nối thành công

        if self.auto_reconnect:
            logger.info("Initial connection failed, starting reconnect process.")
            self._start_reconnect_process()
        else:
            with self._lock:
                self._is_connecting = False
            MainWindowController.on_connection_failed()

    def disconnect(self):
        """
        Ngắt kết nối chủ động từ người dùng hoặc khi ứng dụng đóng.
        """
        logger.info(f"Manually disconnecting from {self.host}:{self.port}")
        with self._lock:
            self._manually_disconnected = True
            self.auto_reconnect = False
            self._running = False
            self._shutdown_event.set()

        self._cleanup_connection()

    @classmethod
    def send_packet(cls, packet: Any) -> bool:
        """
        Hàm duy nhất để gửi packet ra ngoài. Packet sẽ được đưa vào hàng đợi
        và gửi đi bởi sender thread. An toàn để gọi từ bất kỳ luồng nào.
        """
        if not cls._instance or not cls._instance._running:
            logger.warning("Cannot send packet: Not connected to server.")
            return False
        try:
            cls._instance._send_queue.put(packet, timeout=1)
            return True
        except Exception as e:
            logger.error(f"Failed to queue packet for sending: {e}")
            return False

    def _attempt_connect(self) -> bool:
        """Thực hiện một lần cố gắng kết nối socket."""
        try:
            plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.use_ssl:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_verify_locations(self.cert_file)
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = False
                self.socket = context.wrap_socket(
                    plain_socket, server_hostname=self.host
                )
            else:
                self.socket = plain_socket

            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            logger.info(f"Successfully connected to server at {self.host}:{self.port}")

            with self._lock:
                self._running = True
                self._is_connecting = False
                self._reconnect_attempts = 0
                self._shutdown_event.clear()

            self._start_threads()
            MainWindowController.on_connection_established()
            return True

        except Exception as e:
            logger.error(f"Connection attempt failed: {e}")
            self._cleanup_connection()
            return False

    def _start_reconnect_process(self):
        """Bắt đầu quá trình kết nối lại trong một luồng riêng."""
        reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        reconnect_thread.start()

    def _reconnect_loop(self):
        """Vòng lặp thực hiện kết nối lại với độ trễ tăng dần."""
        while (
            not self._manually_disconnected
            and self._reconnect_attempts < self.max_retries
        ):
            self._reconnect_attempts += 1
            delay = self.retry_delay * (
                self.reconnect_backoff ** (self._reconnect_attempts - 1)
            )

            logger.info(
                f"Reconnecting in {delay:.1f}s... (Attempt {self._reconnect_attempts}/{self.max_retries})"
            )
            MainWindowController.on_connection_reconnecting(
                {"attempt": self._reconnect_attempts}
            )

            # Chờ hết thời gian delay hoặc nhận tín hiệu shutdown
            if self._shutdown_event.wait(timeout=delay):
                break  # Bị ngắt bởi disconnect()

            if self._attempt_connect():
                logger.info("Reconnected successfully!")
                return

        if not self._manually_disconnected:
            logger.error(
                "Max reconnection attempts reached. Could not connect to server."
            )
            with self._lock:
                self._is_connecting = False
            MainWindowController.on_connection_failed()

    def _handle_connection_lost(self, error: Exception):
        """Xử lý khi kết nối bị mất đột ngột."""
        logger.error(f"Connection lost: {error}")
        with self._lock:
            if not self._running or self._is_connecting:
                return  # Đã được xử lý hoặc đang trong quá trình kết nối lại
            self._running = False
            self._is_connecting = True

        self._cleanup_connection()

        if self.auto_reconnect and not self._manually_disconnected:
            logger.info("Connection lost. Starting reconnect process.")
            self._start_reconnect_process()
        else:
            MainWindowController.on_connection_failed()

    def _start_threads(self):
        """Bắt đầu luồng lắng nghe và luồng gửi packet."""
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.listener_thread.start()
        self.sender_thread.start()

    def _listener_loop(self):
        """[THREAD] Vòng lặp liên tục lắng nghe packet từ server."""
        logger.debug("Listener thread started.")
        while self._running and not self._shutdown_event.is_set():
            try:
                if not self.socket:
                    break
                packet = Protocol.receive_packet(self.socket)
                if packet:
                    ClientHandler.handle_received_packet(packet)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self._handle_connection_lost(e)
                break
        logger.debug("Listener thread stopped.")

    def _sender_loop(self):
        """[THREAD] Vòng lặp liên tục lấy packet từ queue và gửi đi."""
        logger.debug("Sender thread started.")
        while self._running and not self._shutdown_event.is_set():
            try:
                if not self.socket:
                    break
                packet = self._send_queue.get(timeout=1)
                Protocol.send_packet(self.socket, packet)
            except Empty:
                continue
            except Exception as e:
                if self._running:
                    self._handle_connection_lost(e)
                break
        logger.debug("Sender thread stopped.")

    def _cleanup_connection(self):
        """Dọn dẹp tài nguyên socket và dừng các luồng một cách an toàn."""
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        # Xóa hàng đợi để giải phóng bộ nhớ
        with self._send_queue.mutex:
            self._send_queue.queue.clear()
