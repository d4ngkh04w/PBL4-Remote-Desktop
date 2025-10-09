import secrets
from PIL import Image
import psutil
import sys
import socket

import mss
from pynput.mouse import Controller

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


def get_cursor_pos():
    """Lấy vị trí chuột hiện tại (x, y)"""
    mouse = Controller()
    return int(mouse.position[0]), int(mouse.position[1])


def capture_screen() -> Image.Image:
    """Capture screen và trả về đối tượng PIL Image"""
    img_pil = Image.new("RGB", (1, 1), (0, 0, 0))
    if sys.platform == "linux":
        sct = mss.mss(with_cursor=True)
    elif sys.platform == "win32":
        sct = mss.mss()

    monitor = sct.monitors[1]
    img = sct.grab(monitor)
    img_pil = Image.frombytes("RGB", img.size, img.rgb)

    if sys.platform == "linux":
        sct.close()
        return img_pil
    elif sys.platform == "win32":
        cursor_x, cursor_y = get_cursor_pos()
        draw = ImageDraw.Draw(img_pil)
        draw.ellipse(
            (cursor_x - 5, cursor_y - 5, cursor_x + 5, cursor_y + 5),
            fill=(255, 0, 0),
            outline=(0, 0, 0),
        )
        sct.close()
        return img_pil


def get_hostname() -> str:
    """Lấy tên máy tính"""
    return socket.gethostname()


def get_resource_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    return cpu_usage, ram_usage
