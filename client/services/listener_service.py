import logging
import threading
import socket
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from common.packets import Packet, VideoStreamPacket
from common.protocol import Protocol

logger = logging.getLogger(__name__)


class ListenerService:
    __receiving_thread = None
    __shutdown_event = threading.Event()
    __socket = None
    __thread_pool = None
    __video_queues = {}
    __max_workers = 50

    @classmethod
    def initialize(cls, sock: socket.socket):
        """Khởi tạo dịch vụ nhận dữ liệu với socket đã kết nối."""
        cls.__socket = sock
        cls.__shutdown_event.clear()
        cls.__thread_pool = ThreadPoolExecutor(
            max_workers=cls.__max_workers, thread_name_prefix="PacketHandler"
        )
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
                        cls.__submit_packet_for_processing(packet)
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

        if cls.__thread_pool:
            logger.info("Shutting down thread pool...")
            cls.__thread_pool.shutdown(wait=True, cancel_futures=False)
            cls.__thread_pool = None

        cls.__video_queues.clear()
        cls.__socket = None
        logger.info("ListenerService shutdown completed")

    @classmethod
    def __submit_packet_for_processing(cls, packet: Packet):
        """Submit packet vào thread pool để xử lý."""
        if cls.__thread_pool is None:
            logger.warning("Thread pool is not initialized, processing packet directly")
            cls.__process_packet(packet)
            return

        if isinstance(packet, VideoStreamPacket):
            session_id = packet.session_id
            if session_id not in cls.__video_queues:
                cls.__video_queues[session_id] = Queue()
                # Submit worker để xử lý video packets theo thứ tự cho session này
                cls.__thread_pool.submit(cls.__process_video_queue, session_id)

            cls.__video_queues[session_id].put(packet)
        else:
            # Các packet khác có thể xử lý song song
            cls.__thread_pool.submit(cls.__process_packet, packet)

    @classmethod
    def __process_video_queue(cls, session_id: str):
        """Xử lý video packets theo thứ tự cho một session."""
        queue = cls.__video_queues.get(session_id)
        if not queue:
            return

        while not cls.__shutdown_event.is_set():
            try:
                packet = queue.get(timeout=0.1)
                if packet is None:
                    break
                cls.__process_packet(packet)
                queue.task_done()
            except:
                continue

    @classmethod
    def __process_packet(cls, packet: Packet):
        """Wrapper an toàn để xử lý packet trong thread pool."""
        from client.handlers.receive_handler import ReceiveHandler

        try:
            ReceiveHandler.handle_packet(packet)
        except Exception as e:
            logger.error(
                f"Error processing packet {type(packet).__name__}: {e}", exc_info=True
            )
