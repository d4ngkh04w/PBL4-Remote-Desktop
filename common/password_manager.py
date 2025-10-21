import secrets
import string

import keyring


class PasswordManager:
    """
    Quản lý việc tạo, hash và xác thực mật khẩu một cách an toàn bằng bcrypt.
    """

    @staticmethod
    def generate_password(
        length: int = 8, ascii: bool = True, digits: bool = True
    ) -> str:
        """
        Tạo một mật khẩu ngẫu nhiên với độ dài cho trước.
        """
        characters = ""
        if ascii:
            characters += string.ascii_lowercase
        if digits:
            characters += string.digits
        password = "".join(secrets.choice(characters) for _ in range(length))
        return password

    @staticmethod
    def store_password(device_id: str, password: str):
        """
        Lưu trữ mật khẩu
        """
        keyring.set_password("RemoteDesktopApp", device_id, password)

    @staticmethod
    def get_stored_password(device_id: str) -> str | None:
        """
        Lấy mật khẩu đã lưu
        """
        return keyring.get_password("RemoteDesktopApp", device_id)

    @staticmethod
    def delete_stored_password(device_id: str):
        """
        Xóa mật khẩu đã lưu
        """
        keyring.delete_password("RemoteDesktopApp", device_id)
