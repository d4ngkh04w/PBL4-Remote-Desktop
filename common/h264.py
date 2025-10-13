from fractions import Fraction
from PIL import Image
import av
from av.video.frame import PictureType


class H264Encoder:
    """Raw H.264 encoder sử dụng codec context."""

    def __init__(self, width, height, fps=30, gop_size=60, bitrate=2_000_000):
        self.gop_size = gop_size
        self.frame_count = 0

        self.codec = av.CodecContext.create("libx264", "w")
        self.codec.width = width
        self.codec.height = height
        self.codec.pix_fmt = "yuv420p"  # Pixel format (Định dạng đầu ra của video)
        self.codec.time_base = Fraction(1, fps)  # Khoảng thời gian giữa 2 frame
        self.codec.framerate = Fraction(fps, 1)  # Khai báo tốc độ khung hình cho FFmpeg
        self.codec.bit_rate = bitrate  # Tốc độ bit cho video
        self.codec.gop_size = gop_size  # Khoảng cách giữa các I-frame

        self.codec.options = {
            "preset": "ultrafast",  # Tốc độ mã hóa
            "tune": "zerolatency",  # Giảm độ trễ
            "crf": "23",  # Chất lượng video (0-51, thấp hơn là tốt hơn)
            "profile": "baseline",
            "level": "3.1",  # Đảm bảo tương thích với nhiều thiết bị
            "rc-lookahead": "0",  # Số frame encoder nhìn trước để tối ưu bitrate (0: tắt để giảm độ trễ)
            "intra-refresh": "1",  # Sử dụng intra refresh thay vì I-frames cứng toàn bộ
        }

        self.codec.open()

    def encode(self, image: Image.Image) -> bytes | None:
        """Encode PIL Image → raw H.264 bytes."""
        frame = av.VideoFrame.from_image(image)
        frame.pts = self.frame_count

        if self.frame_count % self.gop_size == 0:
            frame.pict_type = PictureType.I

        self.frame_count += 1
        packets = self.codec.encode(frame)

        return b"".join(bytes(p) for p in packets) if packets else None

    def get_extradata(self) -> bytes | None:
        """Lấy SPS/PPS headers."""
        if hasattr(self.codec, "extradata") and self.codec.extradata:
            return bytes(self.codec.extradata)
        return None

    def flush(self) -> bytes | None:
        """Flush buffer cuối stream."""
        packets = self.codec.encode(None)
        return b"".join(bytes(p) for p in packets) if packets else None

    def close(self):
        """Đóng codec."""
        if self.codec:
            self.flush()


class H264Decoder:
    """Raw H.264 decoder."""

    def __init__(self, extradata: bytes | None = None):
        """
        Args:
            extradata: SPS/PPS headers từ encoder
        """

        self.codec = av.CodecContext.create("h264", "r")

        if extradata:
            self.codec.extradata = extradata

        self.codec.open()
        self.frame_count = 0

    def decode(self, data: bytes) -> Image.Image | None:
        """
        Decode raw H.264 bytes → PIL Image
        """
        try:
            # Tạo packet từ raw data
            packet = av.Packet(data)

            # Decode packet
            frames = self.codec.decode(packet)

            if not frames:
                return None

            # Lấy frame đầu tiên (thường chỉ có 1)
            frame = frames[0]
            self.frame_count += 1

            # Convert VideoFrame → PIL Image
            return frame.to_image()

        except Exception as e:
            print(f"Decode error: {e}")
            return None

    def flush(self):
        """Flush buffer cuối stream."""
        try:
            frames = self.codec.decode(None)
            if frames:
                return frames[0].to_image()
        except:
            pass
        return None

    def close(self):
        if self.codec:
            self.flush()
