from queue import Queue, Empty
import socket
import ssl
import logging
import threading
from typing import Any
from common.enums import Status
from common.packets import (
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    SessionPacket,
)
from common.protocol import Protocol
from client.controllers.main_window_controller import MainWindowController
from client.service.session_service import SessionService
logger = logging.getLogger(__name__)


class SocketClient:
    # Class variable để lưu instance hiện tại
    _current_instance = None
    _lock = threading.RLock()

    def __init__(self, server_host, server_port, use_ssl, cert_file):
        self.host = server_host
        self.port = server_port
        self.use_ssl = use_ssl
        self.cert_file = cert_file

        # Socket và thread state
        self.socket = None
        self.running = False
        self.listener_thread = None
        self.sender_thread = None

        # Thread control
        self._send_queue = Queue()
        self._shutdown_event = threading.Event()

        # Reconnection settings
        self.auto_reconnect = True
        self.max_retries = 5
        self.retry_delay = 2
        self.reconnect_backoff = 1.5

        # Reconnection state
        self._reconnect_attempts = 0
        self._is_connecting = False  # Đang trong quá trình connect/reconnect
        self._manually_disconnected = False  # User chủ động disconnect

        # Set as current instance
        with SocketClient._lock:
            SocketClient._current_instance = self

    def connect(self) -> bool:
        """
        Kết nối đến server. Nếu thất bại sẽ tự động thử reconnect.
        """
        with SocketClient._lock:
            if self._is_connecting:
                logger.warning("Already connecting/reconnecting")
                return False
            self._is_connecting = True
            self._manually_disconnected = False

        if self._attempt_connect():
            return True

        if self.auto_reconnect:
            logger.info("Initial connection failed, starting reconnect process")
            self._start_reconnect_process()
            return False
        else:

            with SocketClient._lock:
                self._is_connecting = False
            MainWindowController.on_connection_failed()
            return False

    def disconnect(self):
        """
        Ngắt kết nối do user yêu cầu
        """
        with SocketClient._lock:
            self._manually_disconnected = True
            self.auto_reconnect = False
            self.running = False
            self._shutdown_event.set()

        logger.info(f"Manually disconnecting from {self.host}:{self.port}")
        self._cleanup_connection()

    def _attempt_connect(self) -> bool:
        """
        Thực hiện kết nối socket
        """
        try:

            plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
                logger.debug("SSL enabled: using secure connection")
            else:
                self.socket = plain_socket
                logger.debug("SSL disabled: using plain TCP connection")

            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to server at {self.host}:{self.port}")

            with SocketClient._lock:
                self.running = True
                self._is_connecting = False
                self._reconnect_attempts = 0
                self._shutdown_event.clear()

            self._start_threads()

            MainWindowController.on_connection_established()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.host}:{self.port} - {e}")
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False

    def _start_reconnect_process(self):
        """
        Bắt đầu quá trình reconnect trong thread riêng
        """
        reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        reconnect_thread.start()

    def _reconnect_loop(self):
        """
        Vòng lặp thử kết nối lại
        """
        while self._reconnect_attempts < self.max_retries:
            # Kiểm tra có bị cancel không
            if self._manually_disconnected:
                logger.info("Reconnect cancelled - manual disconnect")
                break

            self._reconnect_attempts += 1
            delay = self.retry_delay * (
                self.reconnect_backoff ** (self._reconnect_attempts - 1)
            )

            logger.debug(
                f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts}/{self.max_retries})"
            )

            # Thông báo đang reconnect
            data = {
                "attempt": self._reconnect_attempts,
            }
            MainWindowController.on_connection_reconnecting(data)

            # Chờ delay hoặc cancel signal
            if self._shutdown_event.wait(timeout=delay):
                if self._manually_disconnected:
                    logger.info("Reconnect cancelled during delay")
                    break

            if self._attempt_connect():
                logger.info("Reconnected successfully!")
                return

        # Hết số lần thử
        logger.error("Max reconnection attempts reached")
        with SocketClient._lock:
            self._is_connecting = False
            self.auto_reconnect = False

        MainWindowController.on_connection_failed()

    def _handle_connection_lost(self, error: Exception):
        """
        Xử lý khi mất kết nối trong quá trình hoạt động
        """
        logger.error(f"Connection lost - {error}")

        with SocketClient._lock:
            if not self.running or self._manually_disconnected or self._is_connecting:
                return  # Đã xử lý rồi hoặc đang reconnect

            self.running = False
            self._is_connecting = True  # Bắt đầu reconnect

        self._cleanup_connection()

        if self.auto_reconnect:
            logger.info("Starting reconnect after connection lost")
            self._start_reconnect_process()
        else:
            with SocketClient._lock:
                self._is_connecting = False
            MainWindowController.on_connection_failed()

    @classmethod
    def send_packet(cls, packet) -> bool:
        """Gửi packet qua queue"""
        with cls._lock:
            if not cls._current_instance or not cls._current_instance.running:
                logger.warning("Not connected to server")
                return False

        try:
            cls._current_instance._send_queue.put(packet, timeout=1)
            return True
        except Exception as e:
            logger.error(f"Failed to queue packet - {e}")
            return False

    def send_packet_sync(self, packet) -> bool:
        """Gửi packet trực tiếp"""
        if not self.running or self.socket is None:
            logger.warning("Not connected to server")
            return False

        try:
            with SocketClient._lock:
                Protocol.send_packet(self.socket, packet)
            return True
        except Exception as e:
            logger.error(f"Failed to send packet - {e}")
            self._handle_connection_lost(e)
            return False

    def _start_threads(self):
        """Bắt đầu listener và sender threads"""
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()

        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()

    def _listener_loop(self):
        """Thread lắng nghe dữ liệu từ server"""
        logger.debug("Listener thread started")

        while self.running and not self._shutdown_event.is_set():
            try:
                if self.socket is None:
                    break

                self.socket.settimeout(0.5)
                packet = Protocol.receive_packet(self.socket)

                if packet:
                    self._handle_received_packet(packet)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:  # Chỉ xử lý nếu đang chạy
                    self._handle_connection_lost(e)
                break

        logger.debug("Listener thread stopped")

    def _sender_loop(self):
        """Thread gửi dữ liệu đến server"""
        logger.debug("Sender thread started")

        while self.running and not self._shutdown_event.is_set():
            try:
                packet = self._send_queue.get(timeout=0.5)
                if packet is None:  # Shutdown signal
                    break

                if self.socket is not None:
                    with SocketClient._lock:
                        Protocol.send_packet(self.socket, packet)

            except Empty:
                continue
            except Exception as e:
                if self.running:  # Chỉ xử lý nếu đang chạy
                    self._handle_connection_lost(e)
                break

        logger.debug("Sender thread stopped")

    def _handle_received_packet(self, packet: Any):
        """Xử lý packet nhận được"""
        try:
            if not packet or not hasattr(packet, "packet_type"):
                logger.error("Invalid packet received")
                return
            if isinstance(packet, AssignIdPacket):
                from client.service.client_service import ClientService
                ClientService._handle_assign_id_packet(packet)
            elif isinstance(packet, ConnectionRequestPacket):
                from client.service.host_service import HostService
                HostService._handle_connection_request_packet(packet)
            elif isinstance(packet, ConnectionResponsePacket):
                if (packet.connection_status == Status.SERVER_FULL or 
                    packet.connection_status == Status.RECEIVER_NOT_FOUND):
                    from client.service.client_service import ClientService
                    ClientService._handle_connection_response_packet(packet)
                else:
                    from client.service.controller_service import ControllerService
                    ControllerService._handle_connection_response_packet(packet)
            elif isinstance(packet, SessionPacket):
                if packet.status == Status.SESSION_STARTED:
                    if packet.role:
                        SessionService.add_session(packet.session_id, packet.role)
                        if packet.role == "controller":
                            from client.service.controller_service import ControllerService
                            ControllerService._handle_session_packet(packet)
                        elif packet.role == "host":
                            from client.service.host_service import HostService
                            HostService._handle_session_packet(packet)
                        else:
                            logger.error(f"Unknown role in SessionPacket: {packet.role}")
                    else:
                        logger.error("SessionPacket missing role for SESSION_STARTED")
            else:
                logger.warning(f"Unhandled packet type: {type(packet)}")

        except Exception as e:
            logger.error(f"Error handling packet - {e}")

    def _cleanup_connection(self):
        """Dọn dẹp kết nối và threads"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket - {e}")
            self.socket = None
        try:
            self._send_queue.put(None, timeout=0.1)  
        except:
            pass

        if self.listener_thread and self.listener_thread.is_alive():
            if self.listener_thread != threading.current_thread():
                self.listener_thread.join(timeout=1)

        if self.sender_thread and self.sender_thread.is_alive():
            if self.sender_thread != threading.current_thread():
                self.sender_thread.join(timeout=1)

        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except Empty:
                break
