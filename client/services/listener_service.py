import logging
import threading
import socket

from common.packets import Packet
from common.protocol import Protocol

logger = logging.getLogger(__name__)


class ListenerService:
    __receiving_thread = None
    __shutdown_event = threading.Event()
    __socket = None

    @classmethod
    def initialize(cls, sock: socket.socket):
        """Khởi tạo dịch vụ nhận dữ liệu với socket đã kết nối."""
        cls.__socket = sock
        cls.__shutdown_event.clear()
        cls.__receiving_thread = threading.Thread(
            target=cls.__receive_worker, daemon=True
        )
        cls.__receiving_thread.start()
        logger.info("ListenerService initialized and receiving thread started")

    @classmethod
    def __receive_worker(cls):
        """Worker thread để nhận dữ liệu từ socket."""
        while not cls.__shutdown_event.is_set():
            if cls.__socket:
                try:
                    packet = Protocol.receive_packet(cls.__socket)
                    if packet:
                        cls.__process_packet(packet)
                except socket.timeout:
                    continue
                except (ConnectionError, OSError) as e:
                    # Socket đã đóng hoặc kết nối bị ngắt - thoát gracefully
                    logger.debug(f"Connection closed in listener: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error in listener worker - {e}", exc_info=True)
                    break

    @classmethod
    def shutdown(cls):
        """Dọn dẹp tài nguyên khi đóng dịch vụ."""
        cls.__shutdown_event.set()
        if cls.__receiving_thread:
            cls.__receiving_thread.join()
        cls.__socket = None

    @classmethod
    def __process_packet(cls, packet: Packet):
        """Xử lý gói tin nhận được."""
        from client.handlers.receive_handler import ReceiveHandler

        ReceiveHandler.handle_packet(packet)
