from queue import Queue, Empty
import socket
import ssl
import logging
import threading
from typing import Any, Optional, Union
from common.enum import EventType 
from client.core.event_bus import EventBus
from common.packet import (
    AssignIdPacket,
    ImagePacket,
    KeyBoardPacket,
    MousePacket,
    RequestConnectionPacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    AuthenticationResultPacket,
    FrameUpdatePacket,
    ResponseConnectionPacket
)
from common.protocol import Protocol




logger = logging.getLogger(__name__)


class SocketClient:
    def __init__(self, server_host, server_port, use_ssl, cert_file):
        self.host = server_host
        self.port = server_port
        self.use_ssl = use_ssl
        self.cert_file = cert_file
        
        # Threading
        self.running = False
        self.listener_thread = None
        self.sender_thread = None
        self._disconnected = False

        # Thread-safe operations
        self._lock = threading.RLock()
        self._send_queue = Queue()
        self._shutdown_event = threading.Event()

        # Reconnection settings
        self.auto_reconnect = True
        self.max_retries = 5
        self.retry_delay = 2
        self.reconnect_backoff = 1.5
        self._reconnect_attempts = 0

        # Client ID - sẽ được gán khi kết nối thành công
        self.client_id: Optional[str] = None

    def connect(self) -> bool:
        """
        Kết nối đến server
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
                logger.info("SSL enabled: using secure connection")
            else:
                self.socket = plain_socket
                logger.info("SSL disabled: using plain TCP connection")

            self.socket.settimeout(10)  # Thiết lập timeout 10 giây cho kết nối
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to server at {self.host}:{self.port}")

            with self._lock:
                self.running = True
                self._disconnected = False
                self._shutdown_event.clear()

            # Start worker threads
            self._start_threads()

            EventBus.publish(EventType.NETWORK_CONNECTED,{
                'host': self.host,
                'port': self.port,
                'ssl': self.use_ssl
            }, source = "SocketClient")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to server {self.host}:{self.port} - {e}")
            self._cleanup_connection()

            EventBus.publish(EventType.NETWORK_CONNECTION_FAILED,{
                'host': self.host,
                'port': self.port,
                'error': str(e)
            }, source = "SocketClient")
            return False
        
    def disconnect(self):
        """Ngắt kết nối khỏi server"""
        with self._lock:
            if not self.running:
                return
            logger.info(f"Disconnecting from server {self.host}:{self.port}")            
            self.running = False
            self._disconnected = True
            self.auto_reconnect = False
            self._shutdown_event.set()

        self._cleanup_connection()

        EventBus.publish(EventType.NETWORK_DISCONNECTED,{
            'host': self.host,
            'port': self.port
        }, source = "SocketClient")

    def send_packet(self, packet: Union[
        ImagePacket,
        KeyBoardPacket,
        MousePacket,
        RequestConnectionPacket,
        RequestPasswordPacket,
        AuthenticationResultPacket,
        SendPasswordPacket,
        FrameUpdatePacket,
    ]) -> bool:
        """Gửi packet đến server"""
        if self.socket is None or not self.running:
            logger.warning("Not connected to server")           
            return False
        try:
            self._send_queue.put(packet, timeout=1)
            return True
        except Exception as e:
            logger.error(f"Failed to queue data to send to server - {e}")           
            return False
        
    def send_packet_sync(self, packet: Union[
        ImagePacket,
        KeyBoardPacket,
        MousePacket,
        RequestConnectionPacket,
        RequestPasswordPacket,
        AuthenticationResultPacket,
        SendPasswordPacket,
        FrameUpdatePacket,
    ]) -> bool:
        """Gửi packet đến server ngay lập tức (không qua hàng đợi)"""
        if self.socket is None or not self.running:
            logger.warning("Not connected to server")
            self.disconnect()
            return False
        try:
            with self._lock:
                Protocol.send_packet(self.socket, packet)
            return True
        except Exception as e:
            logger.error(f"Failed to send data to server - {e}")
            self._handle_connection_error(e)
            return False
     
    def _start_threads(self):
        """Bắt đầu các luồng xử lý"""
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()

        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()

    def _listener_loop(self):
        """Vòng lặp lắng nghe dữ liệu từ server"""
        logger.debug("Listener thread started")

        while self.running and not self._shutdown_event.is_set():
            try:
                if self.socket is None:
                    logger.warning("Not connected to server")
                    self.disconnect()
                    return
                
                # Set a short timeout to allow checking the shutdown event
                self.socket.settimeout(0.5)
                packet = Protocol.receive_packet(self.socket)

                if packet:
                    self._handle_received_packet(packet)

            except socket.timeout:
                continue
            except Exception as e:
                self._handle_connection_error(e)
                break

        logger.debug("Listener thread stopped")

    def _sender_loop(self):
        """Vòng lặp gửi dữ liệu đến server"""
        logger.debug("Sender thread started")

        while self.running and not self._shutdown_event.is_set():
            try:
                packet = self._send_queue.get(timeout=0.5)
                if packet:
                    with self._lock:
                        Protocol.send_packet(self.socket, packet)
            except Empty:
                continue
            except Exception as e:
                self._handle_connection_error(e)
                break

        logger.debug("Sender thread stopped")

    def _handle_received_packet(self, packet: Any):
        """Chỉ publish packet qua EventBus, không xử lý logic nghiệp vụ"""
        try:
            if not packet or not hasattr(packet, "packet_type"):
                logger.error("Invalid packet received: %s", packet)
                return

            # Lưu client_id nếu đây là AssignIdPacket
            if isinstance(packet, AssignIdPacket) and hasattr(packet, "client_id"):
                self.client_id = packet.client_id
                logger.debug("Client ID assigned: %s", self.client_id)

            # Publish packet với event type dựa trên packet type
            event_type = f"PACKET_{packet.packet_type.name}"
            EventBus.publish(event_type, packet, source="SocketClient")
            
        except Exception as e:
            logger.error(f"Error handling received packet - {e}")

    def _handle_connection_error(self, error: Exception):
        """Xử lý lỗi kết nối"""
        logger.error(f"Connection error - {error}")

        with self._lock:
            if self._disconnected:
                return
        
        if self.auto_reconnect and self._reconnect_attempts < self.max_retries:
            self._attempt_reconnect()
        else:
            self._cleanup_connection()
            EventBus.publish(EventType.NETWORK_DISCONNECTED,{
                'host': self.host,
                'port': self.port,
                'error': str(error)
            }, source = "SocketClient")

    def _attempt_reconnect(self):
        """Thử kết nối lại với server"""
        self._reconnect_attempts += 1
        delay = self.retry_delay * (self.reconnect_backoff ** (self._reconnect_attempts - 1))
        logger.info(f"Attempting to reconnect in {delay:.1f} seconds (Attempt {self._reconnect_attempts}/{self.max_retries})")

        EventBus.publish(EventType.NETWORK_RECONNECTING,{
            'host': self.host,
            'port': self.port,
            'attempt': self._reconnect_attempts,
            'max_retries': self.max_retries,
            'delay': delay
        }, source = "SocketClient")
        
        threading.Timer(delay, self._do_reconnect).start()

    def _do_reconnect(self):
        """Thực hiện kết nối lại"""
        self._cleanup_connection()

        if self.connect():
            logger.info("Reconnected successfully")
            self._reconnect_attempts = 0
        else:
            logger.error("Reconnection attempt failed")

            if self._reconnect_attempts < self.max_retries:
                self._attempt_reconnect()
            else:
                logger.error("Max reconnection attempts reached, giving up")
                self.auto_reconnect = False
                EventBus.publish(EventType.NETWORK_DISCONNECTED,{
                    'host': self.host,
                    'port': self.port,
                    'error': 'Max reconnection attempts reached'
                }, source = "SocketClient")

    def _cleanup_connection(self):
        """Dọn dẹp kết nối và các tài nguyên liên quan"""
        with self._lock:
            self.running = False
            self._disconnected = True
            self._shutdown_event.set()

            if self.socket:
                try:
                    self.socket.close()
                except Exception as e:
                    logger.error(f"Error closing socket - {e}")
                self.socket = None

        try:
            self._send_queue.put(None, timeout=0.1)  # Giúp thread sender thoát
        except Exception as e:
            logger.error(f"Error signaling sender thread to stop - {e}")

        if self.listener_thread and self.listener_thread.is_alive():
            if self.listener_thread != threading.current_thread():
                self.listener_thread.join(timeout=1)
        
        if self.sender_thread and self.sender_thread.is_alive():
            if self.sender_thread != threading.current_thread():
                self.sender_thread.join(timeout=1)

        #  Clear queue
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except Empty:
                break    

    def __del__(self):
        """Hủy đối tượng và dọn dẹp tài nguyên"""
        try:
            self.disconnect()
        except Exception:
            pass
            
            