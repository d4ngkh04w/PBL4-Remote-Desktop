import secrets
import sys
import socket
import subprocess
import uuid

import mss
from mss.base import MSSBase
from pynput.mouse import Controller
import psutil
from PIL import Image

if sys.platform == "win32":
    from PIL import ImageDraw


def generate_numeric_id(num_digits: int = 9) -> str:
    """
    Tạo ID dạng số
    Ví dụ: 123456789
    """
    if num_digits < 1:
        return ""
    range_start = 10 ** (num_digits - 1)
    range_end = (10**num_digits) - 1
    # secrets.randbelow(N) tạo ra số từ 0 đến N-1
    # nên cần cộng thêm range_start
    return str(secrets.randbelow(range_end - range_start + 1) + range_start)


def format_numeric_id(numeric_id: str) -> str:
    """
    Định dạng ID số cho dễ đọc.
    Ví dụ: "123456789" -> "123 456 789"
    """
    if not numeric_id.isdigit():
        return numeric_id

    parts = []
    temp_id = numeric_id
    while temp_id:
        parts.insert(0, temp_id[-3:])
        temp_id = temp_id[:-3]

    return " ".join(parts)


def unformat_numeric_id(formatted_id: str) -> str:
    """
    Bỏ định dạng ID số.
    Ví dụ: "123 456 789" -> "123456789"
    """
    return formatted_id.replace(" ", "")


def capture_frame(
    sct_instance: MSSBase,
    monitor: dict,
    mouse_controller: Controller | None = None,
    draw_cursor: bool = False,
) -> Image.Image | None:
    try:
        # Chụp màn hình
        img_bgra = sct_instance.grab(monitor)

        if not img_bgra:
            return None

        # BGRX loại bỏ kênh Alpha không cần thiết
        img_pil = Image.frombytes("RGB", img_bgra.size, img_bgra.bgra, "raw", "BGRX")

        if draw_cursor and mouse_controller and sys.platform == "win32":
            try:
                # Lấy vị trí chuột toàn cục
                mouse_x, mouse_y = mouse_controller.position

                # Tính toán vị trí tương đối của chuột trên màn hình đang được chụp
                monitor_x, monitor_y = monitor["left"], monitor["top"]
                relative_x = mouse_x - monitor_x
                relative_y = mouse_y - monitor_y

                # Chỉ vẽ nếu con trỏ nằm trong phạm vi của màn hình này
                if (
                    0 <= relative_x < monitor["width"]
                    and 0 <= relative_y < monitor["height"]
                ):
                    draw = ImageDraw.Draw(img_pil)
                    radius = 8
                    # Tọa độ để vẽ hình tròn con trỏ
                    ellipse_bbox = (
                        relative_x - radius,
                        relative_y - radius,
                        relative_x + radius,
                        relative_y + radius,
                    )
                    draw.ellipse(ellipse_bbox, fill=(255, 0, 0), outline=(0, 0, 0))
            except Exception as e:
                # Nếu có lỗi khi vẽ cursor, vẫn trả về ảnh không có cursor
                pass

        return img_pil
    except mss.ScreenShotError as e:
        print(f"MSS ScreenShotError: {e}")
        return None
    except Exception as e:
        print(f"Capture frame error: {e}")
        return None


def get_hostname() -> str:
    """Lấy tên máy tính"""
    return socket.gethostname()


def get_hardware_id() -> str:
    """Lấy hardware ID"""
    if sys.platform == "win32":
        cmd = ["wmic", "csproduct", "get", "uuid"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            ).stdout.strip()
            lines = result.splitlines()
            for line in lines:
                line = line.strip()
                if line and line.lower() != "uuid":
                    return line
        except subprocess.CalledProcessError:
            return str(uuid.getnode())

    elif sys.platform == "linux":
        try:
            with open("/etc/machine-id", "r") as f:
                return f.read().strip()
        except IOError:
            return str(uuid.getnode())

    return str(uuid.getnode())


def get_resource_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    return cpu_usage, ram_usage
