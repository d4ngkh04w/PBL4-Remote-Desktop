import threading
import time
import logging
from typing import Dict
from dataclasses import dataclass

from pynput.mouse import Controller
import mss

from common.h264 import H264Encoder
from common.utils import capture_frame
from client.handlers.send_handler import SendHandler
from client.services.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Thông tin session cần stream tới."""
    session_id: str
    config_sent: bool = False


class ScreenShareService:
    """
    Screen sharing service - capture 1 lần, gửi cho nhiều sessions.    
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._monitor_number = 1
        self._fps = 30
        self._gop_size = 60
        self._bitrate = 2_000_000

        # Quản lý sessions
        self._active_sessions: Dict[str, SessionInfo] = {}
        self._sessions_lock = threading.RLock()

        # Streaming state
        self._is_running = threading.Event()
        self._streaming_thread = None
        self._mouse_controller = Controller()

        # Encoder (sẽ được tạo khi có session đầu tiên)
        self._encoder = None
        self._screen_config = None  # Dict chứa monitor info

        logger.info("CentralizedScreenShareService initialized")

    def add_session(self, session_id: str):
        """Thêm session cần stream tới và gửi config ngay lập tức."""
        with self._sessions_lock:
            session_info = SessionInfo(session_id=session_id)
            self._active_sessions[session_id] = session_info
            logger.info(f"Added session to centralized streaming: {session_id}")

            # Khởi tạo encoder nếu chưa có
            if not self._encoder:
                self._initialize_encoder()

            # Gửi config cho session mới nếu encoder đã sẵn sàng
            self._send_config_to_session(session_id)

            if not self._is_running.is_set():
                self._start_streaming()

    def _initialize_encoder(self):
        """Khởi tạo encoder với dummy frame để có extradata."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[self._monitor_number]
                width, height = monitor["width"], monitor["height"]

                self._encoder = H264Encoder(
                    width=width,
                    height=height,
                    fps=self._fps,
                    gop_size=self._gop_size,
                    bitrate=self._bitrate,
                )

                self._screen_config = {
                    "monitor": monitor,
                    "width": width,
                    "height": height,
                }

                # 📸 Capture 1 dummy frame để lấy extradata
                img = capture_frame(
                    sct_instance=sct,
                    monitor=monitor,
                    mouse_controller=self._mouse_controller,
                    draw_cursor=False,  # Không cần cursor cho dummy frame
                )
                if img:
                    self._encoder.encode(img)
                    logger.info(
                        f"Encoder initialized with dummy frame: {width}x{height}@{self._fps}fps"
                    )
                else:
                    logger.warning("Failed to capture dummy frame for encoder initialization")

        except Exception as e:
            logger.error(f"Error initializing encoder: {e}", exc_info=True)

    def _send_config_to_session(self, session_id: str):
        """Gửi video config cho session cụ thể."""
        if self._encoder and self._screen_config:
            extradata = self._encoder.get_extradata()
            if extradata:
                try:
                    SendHandler.send_video_config_packet(
                        session_id=session_id,
                        width=self._screen_config["width"],
                        height=self._screen_config["height"],
                        fps=self._fps,
                        codec="h264",
                        extradata=extradata,
                    )

                    # Mark config as sent
                    if session_id in self._active_sessions:
                        self._active_sessions[session_id].config_sent = True
                except Exception as e:
                    logger.error(f"Error sending config to {session_id}: {e}")
            else:
                logger.warning(f"Cannot send config to {session_id}: encoder not ready or no extradata")

    def remove_session(self, session_id: str):
        """Xóa session khỏi danh sách stream."""
        with self._sessions_lock:
            # Tìm và xóa session
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
                logger.info(f"Removed session from centralized streaming: {session_id}")

            # Dừng streaming nếu không còn session nào
            if not self._active_sessions and self._is_running.is_set():
                self._stop_streaming()

    def _start_streaming(self):
        """Bắt đầu streaming (private method)."""
        if self._is_running.is_set():
            logger.warning("Centralized streaming already running")
            return

        self._is_running.set()
        self._streaming_thread = threading.Thread(
            target=self._stream_worker, daemon=True, name="CentralizedScreenStreamer"
        )
        self._streaming_thread.start()
        logger.info("Centralized screen streaming started")

    def _stop_streaming(self):
        """Dừng streaming (private method)."""
        if not self._is_running.is_set():
            return

        self._is_running.clear()
        if self._streaming_thread:
            self._streaming_thread.join(timeout=5.0)

        # Cleanup encoder
        if self._encoder:
            self._encoder.close()
            self._encoder = None
            self._screen_config = None

        logger.info("Centralized screen streaming stopped")

    def _stream_worker(self):
        """Thread worker: capture 1 lần → encode 1 lần → gửi cho tất cả sessions."""
        frame_delay = 1.0 / self._fps
        frame_count = 0

        with mss.mss(with_cursor=True) as sct:
            try:
                while self._is_running.is_set():
                    loop_start = time.perf_counter()

                    # Kiểm tra có sessions không
                    with self._sessions_lock:
                        if not self._active_sessions:
                            break
                        active_sessions = list(
                            self._active_sessions.values()
                        )  # Copy SessionInfo objects

                    # Encoder sẽ được khởi tạo trong add_session(), nhưng double-check
                    if not self._encoder or not self._screen_config:
                        logger.warning(
                            "Encoder not initialized, initializing in stream worker..."
                        )
                        with self._sessions_lock:
                            self._initialize_encoder()

                    # Kiểm tra lại sau khi khởi tạo
                    if not self._encoder or not self._screen_config:
                        logger.error("Failed to initialize encoder, skipping frame")
                        time.sleep(frame_delay)
                        continue

                    # CAPTURE 1 LẦN
                    img = capture_frame(
                        sct_instance=sct,
                        monitor=self._screen_config["monitor"],
                        mouse_controller=self._mouse_controller,
                        draw_cursor=True,
                    )

                    if not img:
                        time.sleep(frame_delay)
                        continue

                    # ENCODE 1 LẦN
                    video_data = self._encoder.encode(img)     

                    # 📡 GỬI 1 VIDEO PACKET LÊN SERVER (không có session_id cụ thể)
                    if video_data:
                        try:                            
                            SendHandler.send_video_stream_packet(
                                video_data=video_data,
                            )
                            frame_count += 1

                            # 📊 Record performance metrics
                            video_data_size = len(video_data)
                            performance_monitor.record_frame_sent(
                                frame_size_bytes=video_data_size,
                                sessions_count=len(active_sessions),
                            )
                        except Exception as e:
                            logger.error(f"Error sending broadcast video packet: {e}")

                    if frame_count % 300 == 0:  # Log mỗi 300 frames (10s @ 30fps)
                        stats = performance_monitor.get_current_stats()
                        logger.info(
                            f"📺 Centralized streaming: {frame_count} frames → {stats['sessions_count']} sessions"
                        )

                    # Frame rate control
                    loop_time = time.perf_counter() - loop_start
                    sleep_time = frame_delay - loop_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Centralized stream error: {e}", exc_info=True)
            finally:
                # Cleanup
                if self._encoder:
                    try:
                        final_data = self._encoder.flush()
                        if final_data:
                            # Gửi final data (chỉ 1 lần cho tất cả sessions)
                            SendHandler.send_video_stream_packet(                                    
                                video_data=final_data,
                            )
                    except Exception as e:
                        logger.error(f"Error sending final data: {e}")

                    self._encoder.close()
                    self._encoder = None

# Global instance
screen_share_service = ScreenShareService()
