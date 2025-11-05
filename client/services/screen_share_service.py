import threading
import time
import logging
from typing import Set

from pynput.mouse import Controller
import mss

from common.h264 import H264Encoder
from common.utils import capture_frame, get_cursor_info_for_monitor
from client.handlers.send_handler import SendHandler
from common.config import Config

logger = logging.getLogger(__name__)


class ScreenShareService:
    """
    Screen sharing service - capture 1 lần, gửi cho nhiều sessions.
    """

    def __init__(self, fps: int = 30, gop_size: int = 60, bitrate: int = 2_000_000):
        self.__monitor_number = 1
        self.__fps = fps
        self.__gop_size = gop_size
        self.__bitrate = bitrate

        # Quản lý sessions
        self.__active_sessions: Set[str] = set()
        self.__sessions_lock = threading.RLock()

        # Streaming state
        self.__is_running = threading.Event()
        self.__streaming_thread = None
        self.__mouse_controller = Controller()

        # Encoder (sẽ được tạo khi có session đầu tiên)
        self.__encoder = None
        self.__screen_config = None  # Dict chứa monitor info

        logger.info("CentralizedScreenShareService initialized")

    def add_session(self, session_id: str):
        """Thêm session cần stream tới và gửi config ngay lập tức."""
        with self.__sessions_lock:
            self.__active_sessions.add(session_id)

            if not self.__encoder:
                self.__initialize_encoder()

            self.__send_config_to_session(session_id)

            if not self.__is_running.is_set():
                self.__start_streaming()

    def __initialize_encoder(self):
        """Khởi tạo encoder với dummy frame để có extradata."""
        try:
            with mss.mss(with_cursor=True) as sct:
                monitor = sct.monitors[self.__monitor_number]
                width, height = monitor["width"], monitor["height"]

                self.__encoder = H264Encoder(
                    width=width,
                    height=height,
                    fps=self.__fps,
                    gop_size=self.__gop_size,
                    bitrate=self.__bitrate,
                )

                self.__screen_config = {
                    "monitor": monitor,
                    "width": width,
                    "height": height,
                }

                img = capture_frame(
                    sct_instance=sct,
                    monitor=monitor,
                )
                if img:
                    self.__encoder.encode(img)
                    logger.debug(
                        f"Encoder initialized with dummy frame: {width}x{height}@{self.__fps}fps"
                    )
                else:
                    logger.warning(
                        "Failed to capture dummy frame for encoder initialization"
                    )

        except Exception as e:
            logger.error(f"Error initializing encoder: {e}", exc_info=True)

    def __send_config_to_session(self, session_id: str):
        """Gửi video config cho session cụ thể."""
        if self.__encoder and self.__screen_config:
            extradata = self.__encoder.get_extradata()
            if extradata:
                try:
                    SendHandler.send_video_config_packet(
                        session_id=session_id,
                        width=self.__screen_config["width"],
                        height=self.__screen_config["height"],
                        fps=self.__fps,
                        codec="h264",
                        extradata=extradata,
                    )

                except Exception as e:
                    logger.error(f"Error sending config to {session_id}: {e}")
            else:
                logger.warning(
                    f"Cannot send config to {session_id}: encoder not ready or no extradata"
                )

    def remove_session(self, session_id: str):
        """Xóa session khỏi danh sách stream."""
        with self.__sessions_lock:
            if session_id in self.__active_sessions:
                self.__active_sessions.remove(session_id)
                logger.debug(
                    f"Removed session from centralized streaming: {session_id}"
                )

            if not self.__active_sessions and self.__is_running.is_set():
                self.__stop_streaming()

    def __start_streaming(self):
        """Bắt đầu streaming (private method)."""
        if self.__is_running.is_set():
            logger.warning("Centralized streaming already running")
            return

        self.__is_running.set()
        self.__streaming_thread = threading.Thread(
            target=self.__stream_worker, daemon=True, name="CentralizedScreenStreamer"
        )
        self.__streaming_thread.start()
        logger.info("Centralized screen streaming started")

    def __stop_streaming(self):
        """Dừng streaming (private method)."""
        if not self.__is_running.is_set():
            return

        self.__is_running.clear()
        if self.__streaming_thread:
            self.__streaming_thread.join(timeout=5.0)

        # Cleanup encoder
        if self.__encoder:
            self.__encoder.close()
            self.__encoder = None
            self.__screen_config = None

        logger.info("Centralized screen streaming stopped")

    def __stream_worker(self):
        """Thread worker: capture 1 lần → encode 1 lần → gửi cho tất cả sessions."""
        frame_delay = 1.0 / self.__fps

        with mss.mss(with_cursor=True) as sct:
            try:
                while self.__is_running.is_set():
                    loop_start = time.perf_counter()

                    # Kiểm tra có sessions không
                    with self.__sessions_lock:
                        if not self.__active_sessions:
                            break

                    # Encoder sẽ được khởi tạo trong add_session(), nhưng double-check
                    if not self.__encoder or not self.__screen_config:
                        logger.warning(
                            "Encoder not initialized, initializing in stream worker..."
                        )
                        with self.__sessions_lock:
                            self.__initialize_encoder()

                    # Kiểm tra lại sau khi khởi tạo
                    if not self.__encoder or not self.__screen_config:
                        logger.error("Failed to initialize encoder, skipping frame")
                        time.sleep(frame_delay)
                        continue

                    # CAPTURE 1 LẦN
                    img = capture_frame(
                        sct_instance=sct,
                        monitor=self.__screen_config["monitor"],
                    )

                    if not img:
                        time.sleep(frame_delay)
                        continue

                    # LẤY THÔNG TIN CURSOR
                    cursor_info = get_cursor_info_for_monitor(
                        self.__screen_config["monitor"], self.__mouse_controller
                    )

                    video_data = self.__encoder.encode(img)

                    # Gửi video packet và cursor info
                    if video_data:
                        try:
                            SendHandler.send_video_stream_packet(
                                video_data=video_data,
                            )

                            if cursor_info:
                                SendHandler.send_cursor_info_packet(
                                    cursor_type=cursor_info["cursor_type"],
                                    position=cursor_info["position"],
                                    visible=cursor_info["visible"],
                                )

                        except Exception as e:
                            logger.error(f"Error sending broadcast video packet: {e}")

                    # Frame rate control
                    loop_time = time.perf_counter() - loop_start
                    sleep_time = frame_delay - loop_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Centralized stream error: {e}", exc_info=True)


bitrate = int(2_000_000 * (Config.fps / 25.0) * 1.2)
screen_share_service = ScreenShareService(
    fps=Config.fps, gop_size=Config.fps, bitrate=bitrate
)
