import secrets
import sys
import socket
import subprocess
import os
from pathlib import Path

import mss
from mss.base import MSSBase
from pynput.mouse import Controller
import psutil
from PIL import Image

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    # Windows API constants
    CURSOR_SHOWING = 0x00000001

    # Cursor types
    IDC_ARROW = 32512
    IDC_IBEAM = 32513
    IDC_WAIT = 32514
    IDC_CROSS = 32515
    IDC_UPARROW = 32516
    IDC_SIZE = 32640
    IDC_ICON = 32641
    IDC_SIZENWSE = 32642
    IDC_SIZENESW = 32643
    IDC_SIZEWE = 32644
    IDC_SIZENS = 32645
    IDC_SIZEALL = 32646
    IDC_NO = 32648
    IDC_HAND = 32649
    IDC_APPSTARTING = 32650
    IDC_HELP = 32651

    # Structure definitions
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]

    class CURSORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.DWORD),
            ("flags", ctypes.wintypes.DWORD),
            ("hCursor", ctypes.wintypes.HANDLE),
            ("ptScreenPos", POINT),
        ]

    # Cache cho cursor images
    _cursor_cache = {}

    def get_cursor_info():
        """Lấy thông tin cursor hiện tại trên Windows"""
        cursor_info = CURSORINFO()
        cursor_info.cbSize = ctypes.sizeof(CURSORINFO)

        if ctypes.windll.user32.GetCursorInfo(ctypes.byref(cursor_info)):
            return cursor_info
        return None

    def get_cursor_type_from_handle(hCursor) -> str:
        """Xác định loại cursor từ handle"""
        try:
            # Load các standard cursor handles
            standard_cursors = {
                ctypes.windll.user32.LoadCursorW(None, IDC_ARROW): "normal",
                ctypes.windll.user32.LoadCursorW(None, IDC_IBEAM): "text",
                ctypes.windll.user32.LoadCursorW(None, IDC_WAIT): "wait",
                ctypes.windll.user32.LoadCursorW(None, IDC_CROSS): "cross",
                ctypes.windll.user32.LoadCursorW(None, IDC_HAND): "hand",
                ctypes.windll.user32.LoadCursorW(None, IDC_SIZEALL): "move",
                ctypes.windll.user32.LoadCursorW(None, IDC_SIZENWSE): "resize_nwse",
                ctypes.windll.user32.LoadCursorW(None, IDC_SIZENESW): "resize_nesw",
                ctypes.windll.user32.LoadCursorW(None, IDC_SIZEWE): "resize_we",
                ctypes.windll.user32.LoadCursorW(None, IDC_SIZENS): "resize_ns",
                ctypes.windll.user32.LoadCursorW(None, IDC_NO): "no",
                ctypes.windll.user32.LoadCursorW(None, IDC_HELP): "help",
                ctypes.windll.user32.LoadCursorW(None, IDC_APPSTARTING): "working",
            }

            # So sánh handle
            if hCursor in standard_cursors:
                return standard_cursors[hCursor]

            # Default
            return "normal"

        except Exception as e:
            print(f"Error detecting cursor type: {e}")
            return "normal"

    def load_cursor_image(cursor_path: str) -> Image.Image | None:
        """Load cursor image từ file .cur hoặc .ani"""
        try:
            # Kiểm tra cache trước
            if cursor_path in _cursor_cache:
                return _cursor_cache[cursor_path]

            # File .ani không thể load trực tiếp bằng PIL, dùng normal select thay thế
            if cursor_path.endswith(".ani"):
                base_dir = os.path.dirname(cursor_path)
                fallback_path = os.path.join(base_dir, "Normal Select.cur")
                if os.path.exists(fallback_path):
                    cursor_path = fallback_path
                else:
                    return None

            # Load cursor image
            cursor_img = Image.open(cursor_path)

            # Convert sang RGBA nếu chưa phải
            if cursor_img.mode != "RGBA":
                cursor_img = cursor_img.convert("RGBA")

            # Cache lại
            _cursor_cache[cursor_path] = cursor_img
            return cursor_img

        except Exception as e:
            print(f"Error loading cursor image {cursor_path}: {e}")
            return None

    def get_cursor_image_path(cursor_type: str = "normal") -> str | None:
        """Lấy đường dẫn đến file cursor dựa trên loại cursor"""
        # Tìm thư mục assets/cursors
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        cursors_dir = project_root / "assets" / "cursors"

        if not cursors_dir.exists():
            return None

        # Map cursor type to filename
        cursor_map = {
            "normal": "Normal Select.cur",
            "text": "Text Select.cur",
            "hand": "Link Select.cur",
            "wait": "Busy.ani",
            "working": "working in background.cur",
            "cross": "Precision Select.cur",
            "move": "Move.cur",
            "resize_nwse": "Diagonal Resize 1.cur",
            "resize_nesw": "Diagonal Resize 2.cur",
            "resize_we": "Horizontal Resize.cur",
            "resize_ns": "Vertical Resize.cur",
            "help": "Help Select.cur",
            "no": "Unavailable.ani",
            "alternate": "Alternate Select.cur",
            "person": "Person Select.cur",
            "handwriting": "Handwriting.cur",
            "location": "Location Select.cur",
        }

        filename = cursor_map.get(cursor_type, "Normal Select.cur")
        cursor_path = cursors_dir / filename

        if cursor_path.exists():
            return str(cursor_path)

        # Fallback to normal cursor
        fallback_path = cursors_dir / "Normal Select.cur"
        if fallback_path.exists():
            return str(fallback_path)

        return None


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
) -> Image.Image | None:
    """
    Chụp màn hình.
    """
    try:
        # Chụp màn hình
        img_bgra = sct_instance.grab(monitor)

        if not img_bgra:
            return None

        img_pil = Image.frombytes("RGB", img_bgra.size, img_bgra.bgra, "raw", "BGRX")
        return img_pil

    except mss.ScreenShotError as e:
        print(f"MSS ScreenShotError: {e}")
        return None
    except Exception as e:
        print(f"Capture frame error: {e}")
        return None


def get_cursor_info_for_monitor(
    monitor: dict, mouse_controller: Controller
) -> dict | None:
    """
    Lấy thông tin cursor hiện tại cho một monitor cụ thể (chỉ trên Windows).
    """
    if sys.platform != "win32":
        return None

    try:
        # Lấy vị trí chuột toàn cục
        mouse_x, mouse_y = mouse_controller.position

        # Tính toán vị trí tương đối của chuột trên màn hình đang được chụp
        monitor_x, monitor_y = monitor["left"], monitor["top"]
        relative_x = mouse_x - monitor_x
        relative_y = mouse_y - monitor_y

        # Chỉ trả về nếu con trỏ nằm trong phạm vi của màn hình này
        if not (
            0 <= relative_x < monitor["width"] and 0 <= relative_y < monitor["height"]
        ):
            return None

        # Lấy thông tin cursor hiện tại
        cursor_info = get_cursor_info()
        cursor_type = "normal"
        visible = True

        if cursor_info:
            visible = bool(cursor_info.flags & CURSOR_SHOWING)
            if visible:
                cursor_type = get_cursor_type_from_handle(cursor_info.hCursor)

        return {
            "cursor_type": cursor_type,
            "position": (relative_x, relative_y),
            "visible": visible,
        }

    except Exception as e:
        print(f"Error getting cursor info: {e}")
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
            return get_hostname()

    elif sys.platform == "linux":
        try:
            with open("/etc/machine-id", "r") as f:
                return f.read().strip()
        except IOError:
            return get_hostname()

    return get_hostname()


def get_resource_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    return cpu_usage, ram_usage
