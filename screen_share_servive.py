import threading
import time
import logging

from pynput.mouse import Controller
import mss

from common.packets import VideoStreamPacket, VideoConfigPacket
from common.h264 import H264Encoder
from common.utils import capture_frame

logger = logging.getLogger(__name__)


class ScreenShareService:
    """Screen streaming service với H.264 encoding."""

    def __init__(
        self, session_id: str, monitor_number=1, fps=30, gop_size=60, bitrate=2_000_000
    ):
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

        with mss.mss() as sct:
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

                # Encode frame đầu để lấy extradata
                init_img = capture_frame(
                    sct_instance=sct,
                    monitor=monitor,
                    mouse_controller=self._mouse_controller,
                    draw_cursor=True,
                )

                if init_img:
                    encoder.encode(init_img)
                    extradata = encoder.get_extradata()

                    # Gửi config packet trước
                    if extradata:
                        config = VideoConfigPacket(
                            session_id=self._session_id,
                            width=width,
                            height=height,
                            fps=self._fps,
                            codec="h264",
                            extradata=extradata,
                        )
                        SocketClient.send_packet(config)

                # Main loop
                while self._is_running.is_set():
                    loop_start = time.perf_counter()

                    img = capture_frame(sct, monitor)
                    if not img:
                        time.sleep(frame_delay)
                        continue

                    # Encode
                    video_data = encoder.encode(img)
                    if video_data:
                        packet = VideoStreamPacket(
                            session_id=self._session_id, video_data=video_data
                        )
                        SocketClient.send_packet(packet)

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
                        SocketClient.send_packet(VideoStreamPacket(final_data))
                    encoder.close()
