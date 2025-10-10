import io
from PIL import Image

import av


class H264Encoder:
    """Mã hóa một chuỗi ảnh PIL thành luồng video H.264."""

    def __init__(self, width: int, height: int, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps

        self.buffer = io.BytesIO()
        self.container = av.open(self.buffer, mode="w", format="mpegts")

        self.stream = self.container.add_stream("libx264", rate=self.fps)
        self.stream.width = self.width
        self.stream.height = self.height
        self.stream.pix_fmt = "yuv420p"
        self.stream.options = {"preset": "ultrafast", "tune": "zerolatency"}

    def encode(self, image: Image.Image) -> bytes:
        """Mã hóa một ảnh PIL và trả về dữ liệu video đã nén."""
        try:
            frame = av.VideoFrame.from_image(image)
            encoded_packets = self.stream.encode(frame)

            for packet in encoded_packets:
                self.container.mux(packet)

            # Lấy tất cả dữ liệu đã được ghi vào buffer
            compressed_data = self.buffer.getvalue()

            # Xóa buffer để chuẩn bị cho khung hình tiếp theo
            self.buffer.seek(0)
            self.buffer.truncate()

            return compressed_data
        except Exception:
            return b""

    def flush(self) -> bytes:
        """Lấy ra bất kỳ dữ liệu nào còn lại trong buffer của encoder."""
        encoded_packets = self.stream.encode(None)
        for packet in encoded_packets:
            self.container.mux(packet)

        # Lấy dữ liệu cuối cùng còn lại trong buffer
        final_data = self.buffer.getvalue()
        self.buffer.seek(0)
        self.buffer.truncate()
        return final_data

    def close(self):
        """Đóng container một cách an toàn."""
        if self.container:
            self.container.close()
        self.buffer.close()
