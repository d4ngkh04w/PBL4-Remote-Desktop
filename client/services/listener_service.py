import logging
import threading
import socket

from common.packets import Packet
from common.protocol import Protocol

logger = logging.getLogger(__name__)


class ListenerService:
    _receiving_thread = None
    _shutdown_event = threading.Event()
    _socket = None

    @classmethod
    def initialize(cls, sock: socket.socket):
        """Khởi tạo dịch vụ nhận dữ liệu với socket đã kết nối."""
        cls._socket = sock
        cls._shutdown_event.clear()
        cls._receiving_thread = threading.Thread(
            target=cls.__receive_worker, daemon=True
        )
        cls._receiving_thread.start()
        logger.info("ListenerService initialized and receiving thread started")

    @classmethod
    def __receive_worker(cls):
        """Worker thread để nhận dữ liệu từ socket."""
        while not cls._shutdown_event.is_set():
            if cls._socket:
                try:
                    packet = Protocol.receive_packet(cls._socket)
                    if packet:
                        cls.__process_packet(packet)
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error in listener worker - {e}")

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên khi đóng dịch vụ."""
        cls._shutdown_event.set()
        if cls._receiving_thread:
            cls._receiving_thread.join()
        cls._socket = None

    @classmethod
    def __process_packet(cls, packet: Packet):
        """Xử lý gói tin nhận được."""
        from client.handlers.receive_handler import ReceiveHandler
        ReceiveHandler.handle_packet(packet)
