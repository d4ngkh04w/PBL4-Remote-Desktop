import threading
import time
import logging

from pynput.mouse import Controller
import mss

from common.packets import VideoStreamPacket, VideoConfigPacket
from common.h264 import H264Encoder
from common.utils import capture_frame
from client.services.sender_service import SenderService
from client.handlers.send_handler import SendHandler

logger = logging.getLogger(__name__)

# DEPRECATED: Use CentralizedScreenShareService instead
# This class is kept for backwards compatibility only


class ScreenShareService:
    """
    ⚠️  DEPRECATED: Individual screen streaming service với H.264 encoding.

    🚀 USE INSTEAD: CentralizedScreenShareService for better performance!

    This service creates individual capture/encode/send pipeline per session.
    Not recommended for multiple sessions due to:
    - High CPU usage (N times capture + encode)
    - High memory usage (N encoder instances)
    - Inefficient resource utilization
    """

    def __init__(
        self, session_id: str, monitor_number=1, fps=30, gop_size=60, bitrate=2_000_000
    ):
        logger.warning(
            f"⚠️  ScreenShareService is DEPRECATED for session {session_id}. "
            f"Consider using CentralizedScreenShareService for better performance!"
        )

        self._session_id = session_id
        self._monitor_number = monitor_number
        self._fps = fps
        self._gop_size = gop_size
        self._bitrate = bitrate

        self._is_running = threading.Event()
        self._streaming_thread = None
        self._mouse_controller = Controller()

    def start(self):
        """Bắt đầu streaming."""
        if self._is_running.is_set():
            logger.warning("Already streaming")
            return

        self._is_running.set()
        self._streaming_thread = threading.Thread(
            target=self._stream_worker, daemon=True, name="ScreenStreamer"
        )
        self._streaming_thread.start()
        logger.info("Streaming started")

    def stop(self):
        """Dừng streaming."""
        if not self._is_running.is_set():
            return

        self._is_running.clear()
        if self._streaming_thread:
            self._streaming_thread.join(timeout=5.0)
        logger.info("Streaming stopped")

    def _stream_worker(self):
        """Thread worker: capture → encode → send."""
        encoder = None
        frame_delay = 1.0 / self._fps
        config_sent = False
        frame_count = 0  # Đếm frame để debug

        with mss.mss(with_cursor=True) as sct:
            try:
                # Lấy monitor info
                monitor = sct.monitors[self._monitor_number]
                width, height = monitor["width"], monitor["height"]

                # Khởi tạo encoder
                encoder = H264Encoder(
                    width=width,
                    height=height,
                    fps=self._fps,
                    gop_size=self._gop_size,
                    bitrate=self._bitrate,
                )

                while self._is_running.is_set():
                    loop_start = time.perf_counter()

                    # Encode frame đầu để lấy extradata
                    img = capture_frame(
                        sct_instance=sct,
                        monitor=monitor,
                        mouse_controller=self._mouse_controller,
                        draw_cursor=True,
                    )

                    if not img:
                        time.sleep(frame_delay)
                        continue

                    video_data = encoder.encode(img)

                    if not config_sent:
                        extradata = encoder.get_extradata()
                        if extradata:
                            SendHandler.send_video_config_packet(
                                session_id=self._session_id,
                                width=width,
                                height=height,
                                fps=self._fps,
                                codec="h264",
                                extradata=extradata,
                            )

                            config_sent = True
                            logger.info("VideoConfigPacket sent successfully")
                        else:
                            logger.debug("Extradata not available yet, continuing...")
                            # Vẫn gửi video data nếu có

                    if video_data:
                        SendHandler.send_video_stream_packet(
                            session_id=self._session_id,
                            frame_data=video_data,
                        )
                        frame_count += 1

                    loop_time = time.perf_counter() - loop_start
                    sleep_time = frame_delay - loop_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)

            finally:
                if encoder:
                    final_data = encoder.flush()
                    if final_data:
                        SenderService.send_packet(
                            VideoStreamPacket(
                                session_id=self._session_id, video_data=final_data
                            )
                        )
                    encoder.close()
