from common.protocol import Protocol
import logging
import threading
import socket
from queue import Queue, Empty
from common.packets import Packet

logger = logging.getLogger(__name__)


class SenderService:
    _queue = Queue()
    _sending_thread = None
    _shutdown_event = threading.Event()
    _socket = None

    @classmethod
    def initialize(cls, sock: socket.socket):
        """Khởi tạo dịch vụ gửi dữ liệu với socket đã kết nối."""
        cls._socket = sock
        cls._shutdown_event.clear()
        cls._sending_thread = threading.Thread(target=cls._send_worker, daemon=True)
        cls._sending_thread.start()
        logger.info("SenderService initialized and sending thread started")

    @classmethod
    def _send_worker(cls):
        """Worker thread để gửi dữ liệu từ hàng đợi."""
        while not cls._shutdown_event.is_set():
            try:
                packet = cls._queue.get(timeout=1)
                if cls._socket:
                    Protocol.send_packet(cls._socket, packet)
                else:
                    logger.error("Socket is None, cannot send packet")
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in sender worker - {e}")

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên khi đóng dịch vụ."""
        cls._shutdown_event.set()
        if cls._sending_thread:
            cls._sending_thread.join()
        cls._socket = None

    @classmethod
    def send_packet(cls, packet: Packet):
        """Đưa dữ liệu vào hàng đợi để gửi."""
        if cls._shutdown_event.is_set():
            return
        if cls._socket:
            cls._queue.put(packet)
        else:
            logger.warning("Socket is not initialized, cannot send data")
