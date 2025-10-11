import threading
import time
import logging

from pynput.mouse import Controller
import mss

from common.packets import VideoStreamPacket
from common.utils import capture_frame
from common.h264encoder import H264Encoder

logger = logging.getLogger(__name__)


class ScreenShareService:

    def __init__(self, monitor_number: int = 1, fps: int = 25):
        self._monitor_number = monitor_number
        self._target_fps = fps

        self._streaming_thread = None
        self._is_running = threading.Event()
        self._mouse_controller = Controller()

    def start(self):
        """Bắt đầu luồng streaming trong một thread riêng."""
        if self._is_running.is_set():
            logger.warning("Streamer is already running")
            return

        self._is_running.set()
        self._streaming_thread = threading.Thread(
            target=self._stream_worker, daemon=True, name="ScreenStreamer"
        )
        self._streaming_thread.start()
        logger.info("Screen streamer thread started")

    def stop(self):
        """Dừng luồng streaming."""
        if not self._is_running.is_set():
            return

        self._is_running.clear()
        if self._streaming_thread:
            self._streaming_thread.join()
        logger.info("Screen streamer stopped")

    def _stream_worker(self):
        """Vòng lặp chính chạy trong thread: chụp -> mã hóa -> gửi."""
        encoder = None
        frame_delay = 1.0 / self._target_fps

        with mss.mss() as sct:
            try:
                monitor = sct.monitors[self._monitor_number]
                width, height = monitor["width"], monitor["height"]

                encoder = H264Encoder(width, height, self._target_fps)

                while self._is_running.is_set():
                    frame_start = time.time()

                    frame_pil = capture_frame(
                        sct_instance=sct,
                        monitor=monitor,
                        mouse_controller=self._mouse_controller,
                        draw_cursor=True,
                    )

                    if frame_pil is None:
                        continue

                    video_data = encoder.encode(frame_pil)

                    if video_data:
                        packet = VideoStreamPacket(video_data=video_data)
                        SocketClient.send_packet(packet)

                    elapsed = time.time() - frame_start
                    sleep_time = frame_delay - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in streaming worker: {e}")
            finally:
                if encoder:
                    final_data = encoder.flush()
                    if final_data:
                        packet = VideoStreamPacket(video_data=final_data)
                        SocketClient.send_packet(packet)
                    encoder.close()
