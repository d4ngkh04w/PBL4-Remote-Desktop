from common.protocol import Protocol
import logging
import threading
import socket
from queue import Queue, Empty
from common.packets import Packet

logger = logging.getLogger(__name__)


class SenderService:
    __queue = Queue()
    __sending_thread = None
    __shutdown_event = threading.Event()
    __socket = None

    @classmethod
    def initialize(cls, sock: socket.socket):
        """Khởi tạo dịch vụ gửi dữ liệu với socket đã kết nối."""
        cls.__socket = sock
        cls.__shutdown_event.clear()
        cls.__sending_thread = threading.Thread(target=cls.__send_worker, daemon=True)
        cls.__sending_thread.start()
        logger.info("SenderService initialized and sending thread started")

    @classmethod
    def __send_worker(cls):
        """Worker thread để gửi dữ liệu từ hàng đợi."""
        while not cls.__shutdown_event.is_set():
            try:
                packet = cls.__queue.get(timeout=1)
                if cls.__socket:
                    Protocol.send_packet(cls.__socket, packet)
                else:
                    logger.error("Socket is None, cannot send packet")
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in sender worker - {e}")

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên khi đóng dịch vụ."""
        cls.__shutdown_event.set()
        if cls.__sending_thread:
            cls.__sending_thread.join()
        cls.__socket = None

    @classmethod
    def send_packet(cls, packet: Packet):
        """Đưa dữ liệu vào hàng đợi để gửi."""
        if cls.__shutdown_event.is_set():
            return
        if cls.__socket:
            cls.__queue.put(packet)
        else:
            logger.warning("Socket is not initialized, cannot send data")
