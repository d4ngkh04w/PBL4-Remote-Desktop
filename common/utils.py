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
    from PIL import ImageDraw
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
    mouse_controller: Controller | None = None,
    draw_cursor: bool = False,
) -> Image.Image | None:
    try:
        # Chụp màn hình
        img_bgra = sct_instance.grab(monitor)

        if not img_bgra:
            return None

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
                    # Lấy thông tin cursor hiện tại
                    cursor_info = get_cursor_info()
                    cursor_type = "normal"

                    if cursor_info and (cursor_info.flags & CURSOR_SHOWING):
                        # Xác định loại cursor
                        cursor_type = get_cursor_type_from_handle(cursor_info.hCursor)

                    # Lấy cursor image tương ứng
                    cursor_path = get_cursor_image_path(cursor_type)
                    cursor_img = None

                    if cursor_path:
                        cursor_img = load_cursor_image(cursor_path)

                    if cursor_img:
                        # Convert img_pil sang RGBA để hỗ trợ transparency
                        img_pil = img_pil.convert("RGBA")

                        # Tính toán vị trí paste (hotspot thường ở góc trên bên trái)
                        # Với cursor tiêu chuẩn, hotspot ở pixel (0, 0)
                        paste_x = relative_x
                        paste_y = relative_y

                        # Resize cursor nếu cần (giữ kích thước gốc hoặc scale xuống)
                        cursor_width, cursor_height = cursor_img.size
                        if cursor_width > 48 or cursor_height > 48:
                            # Scale xuống nếu cursor quá lớn
                            scale_factor = min(48 / cursor_width, 48 / cursor_height)
                            new_width = int(cursor_width * scale_factor)
                            new_height = int(cursor_height * scale_factor)
                            cursor_img = cursor_img.resize(
                                (new_width, new_height), Image.Resampling.LANCZOS
                            )

                        # Paste cursor lên hình ảnh với alpha blending
                        img_pil.paste(cursor_img, (paste_x, paste_y), cursor_img)

                        # Convert lại sang RGB
                        img_pil = img_pil.convert("RGB")
                    else:
                        # Fallback: vẽ hình tròn đỏ nếu không load được cursor
                        draw = ImageDraw.Draw(img_pil)
                        radius = 8
                        ellipse_bbox = (
                            relative_x - radius,
                            relative_y - radius,
                            relative_x + radius,
                            relative_y + radius,
                        )
                        draw.ellipse(ellipse_bbox, fill=(255, 0, 0), outline=(0, 0, 0))

            except Exception as e:
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
