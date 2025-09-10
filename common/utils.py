import secrets
import mss
from PIL import Image
import io


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


def capture_screen() -> tuple[bytes, int, int]:
    """Capture screen và trả về"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        img_pil = Image.frombytes("RGB", img.size, img.rgb)

        # Lưu kích thước gốc
        original_width, original_height = img_pil.size

        new_size = (int(img_pil.width * 0.7), int(img_pil.height * 0.7))
        img_pil = img_pil.resize(new_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()

        img_pil.save(buffer, format="JPEG", quality=75, optimize=True)
        return buffer.getvalue(), original_width, original_height
